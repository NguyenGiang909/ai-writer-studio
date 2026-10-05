
import json
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models import Project,Volume,Arc,Chapter,Scene
from app.models.memory import StorySummary,RetconProposal,AiTurn
from app.models.narrative import Thread,ThreadBeat,ThreadDependency
from app.models.truth import StoryEvent,StoryState,KnowledgeState,CanonFact,AuthorDecision
from app.services.memory import HIERARCHY,invalidate_chain,bounded_backlog,impact_preview,ancestor_chain
from app.ai.compose import build_story_prompt
from app.ai.router import ModelRouter,ModelRequest
from app.schemas.extras import *
router=APIRouter()

SCOPE_MODEL={"scene":Scene,"chapter":Chapter,"arc":Arc,"volume":Volume,"story":Project}

async def project_ok(db,pid):
    if not await db.get(Project,pid): raise HTTPException(404,"project not found")
async def add(db,obj):
    db.add(obj); await db.commit(); await db.refresh(obj); return obj

async def _ref_graph(db,pid):
    """All things that reference other things — the dependency graph for impact preview."""
    refs=[]
    async def pull(model,kind,ref_fn):
        rows=list((await db.scalars(select(model).where(model.project_id==pid))).all())
        for r in rows:
            refs.append({"kind":kind,"id":r.id,
                         "label":getattr(r,"title",None) or getattr(r,"name",None) or getattr(r,"summary",None) or getattr(r,"predicate",None) or r.id[:8],
                         "references":[x for x in ref_fn(r) if x]})
    await pull(ThreadDependency,"thread_dependency",lambda d:[d.thread_id,d.depends_on_thread_id])
    await pull(Thread,"thread",lambda t:[t.id])
    await pull(ThreadBeat,"thread_beat",lambda b:[b.thread_id,b.scene_id])
    await pull(Scene,"scene",lambda s:[s.id,s.chapter_id,s.pov_character_id,s.location_id])
    await pull(Chapter,"chapter",lambda c:[c.id,c.volume_id,c.arc_id])
    await pull(StoryEvent,"story_event",lambda e:[e.scene_id,e.location_id])
    await pull(StoryState,"story_state",lambda s:[s.entity_id,s.source_event_id])
    await pull(CanonFact,"canon_fact",lambda f:[f.subject_id,f.source_scene_id,f.id])
    await pull(KnowledgeState,"knowledge_state",lambda k:[k.fact_id,k.knower_id])
    await pull(AuthorDecision,"author_decision",lambda d:[d.id])
    return refs

async def _validate_scope(db,pid,scope_type,scope_id):
    if scope_type not in HIERARCHY: raise HTTPException(400,"invalid scope_type")
    cls=SCOPE_MODEL[scope_type]
    obj=await db.get(cls,scope_id)
    if not obj: raise HTTPException(404,f"{scope_type} not found")
    if scope_type!="story" and getattr(obj,"project_id",None)!=pid: raise HTTPException(400,"scope outside project")
    if scope_type=="story" and obj.id!=pid: raise HTTPException(400,"story scope must be the project itself")

@router.post("/projects/{pid}/summaries")
async def create_summary(pid:str,p:SummaryCreate,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid); await _validate_scope(db,pid,p.scope_type,p.scope_id)
    return await add(db,StorySummary(project_id=pid,stale=False,**p.model_dump()))
@router.get("/projects/{pid}/summaries")
async def list_summaries(pid:str,scope_type:str|None=None,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    q=select(StorySummary).where(StorySummary.project_id==pid)
    if scope_type: q=q.where(StorySummary.scope_type==scope_type)
    return list((await db.scalars(q.order_by(StorySummary.scope_type,StorySummary.scope_id))).all())
@router.patch("/projects/{pid}/summaries/{sid}")
async def patch_summary(pid:str,sid:str,p:SummaryPatch,db:AsyncSession=Depends(get_db)):
    obj=await db.get(StorySummary,sid)
    if not obj or obj.project_id!=pid: raise HTTPException(404,"summary not found")
    for k,v in p.model_dump(exclude_unset=True).items(): setattr(obj,k,v)
    await db.commit(); await db.refresh(obj); return obj
# ---- AI summary generation (scene→chapter→arc→volume→story) ----
async def _sum_map(db,pid,scope_type):
    """scope_id → latest StorySummary row for a level."""
    return {s.scope_id:s for s in (await db.scalars(select(StorySummary).where(
        StorySummary.project_id==pid,StorySummary.scope_type==scope_type))).all()}

async def _child_lines(db,pid,children,child_scope):
    """One bullet per child: fresh summary > clipped prose/skeleton > bare title."""
    sums=await _sum_map(db,pid,child_scope); lines=[]
    for c in children:
        label=getattr(c,"title",None) or getattr(c,"name",None) or "…"
        s=sums.get(c.id)
        if s and not s.stale and (s.summary or "").strip():
            lines.append(f"• {label}: {s.summary.strip()}")
        elif getattr(c,"prose",None) and c.prose.strip():
            lines.append(f"• {label}: {c.prose.strip()[:800]}")
        elif getattr(c,"skeleton",None) and c.skeleton.strip():
            lines.append(f"• {label}: {c.skeleton.strip()[:400]}")
        else:
            lines.append(f"• {label}")
    return lines

async def _scope_source_text(db,pid,scope_type,scope_id):
    """(text_for_summarizer, narrative_end). None khi scope không có gì để tóm."""
    if scope_type=="scene":
        sc=await db.get(Scene,scope_id)
        parts=[p for p in [(sc.prose or "").strip()[:9000] or None,
                           f"[Xương cảnh]\n{sc.skeleton}" if sc.skeleton else None] if p]
        return ("\n\n".join(parts) if parts else None), sc.narrative_order
    if scope_type=="chapter":
        ch=await db.get(Chapter,scope_id)
        scenes=list((await db.scalars(select(Scene).where(
            Scene.chapter_id==scope_id).order_by(Scene.order_index))).all())
        lines=await _child_lines(db,pid,scenes,"scene")
        if not lines: return None,None
        head=f"Chương {ch.order_index}: {ch.title or ''}".strip()
        return f"{head}\n"+"\n".join(lines), ch.order_index
    if scope_type=="arc":
        a=await db.get(Arc,scope_id)
        chapters=list((await db.scalars(select(Chapter).where(
            Chapter.arc_id==scope_id).order_by(Chapter.order_index))).all())
        lines=await _child_lines(db,pid,chapters,"chapter")
        if not lines: return None,None
        return f"Hồi: {a.title or ''}\n"+"\n".join(lines), max((c.order_index for c in chapters),default=None)
    if scope_type=="volume":
        v=await db.get(Volume,scope_id)
        arcs=list((await db.scalars(select(Arc).where(
            Arc.volume_id==scope_id).order_by(Arc.order_index))).all())
        orphans=list((await db.scalars(select(Chapter).where(
            Chapter.volume_id==scope_id,Chapter.arc_id.is_(None))
            .order_by(Chapter.order_index))).all())
        lines=(await _child_lines(db,pid,arcs,"arc"))+(await _child_lines(db,pid,orphans,"chapter"))
        if not lines: return None,None
        narr=max([c.order_index for c in (await db.scalars(select(Chapter).where(
            Chapter.volume_id==scope_id))).all()] or [None])
        return f"Quyển: {v.title or ''}\n"+"\n".join(lines), narr
    # story
    vols=list((await db.scalars(select(Volume).where(
        Volume.project_id==pid).order_by(Volume.order_index))).all())
    orphans=list((await db.scalars(select(Chapter).where(
        Chapter.project_id==pid,Chapter.volume_id.is_(None))
        .order_by(Chapter.order_index))).all())
    lines=(await _child_lines(db,pid,vols,"volume"))+(await _child_lines(db,pid,orphans,"chapter"))
    if not lines: return None,None
    proj=await db.get(Project,pid)
    narr=max([c.order_index for c in (await db.scalars(select(Chapter).where(
        Chapter.project_id==pid))).all()] or [None])
    return f"Truyện: {proj.name}\n"+"\n".join(lines), narr

@router.post("/projects/{pid}/summaries/generate")
async def generate_summary(pid:str,p:SummaryGenerateRequest,db:AsyncSession=Depends(get_db)):
    """AI tóm tắt 1 scope → upsert StorySummary (bản nháp phụ trợ, không phải Canon)."""
    await project_ok(db,pid); await _validate_scope(db,pid,p.scope_type,p.scope_id)
    text,narr_end=await _scope_source_text(db,pid,p.scope_type,p.scope_id)
    if not text: raise HTTPException(400,"scope has no content to summarize")
    system,prompt,_=await build_story_prompt(db,pid,"summarization",text)
    try:
        result=await ModelRouter(db).complete(
            ModelRequest(task="summarization",prompt=prompt,project_id=pid,system=system))
    except RuntimeError as e: raise HTTPException(503,str(e))
    summary=(result.text or "").strip()
    db.add(AiTurn(project_id=pid,scope_id=p.scope_id,task="summarization",
                  prompt_excerpt=text[:1500],reply_text=summary[:4000],
                  provider=result.provider or "",model=result.model or ""))
    obj=(await db.scalars(select(StorySummary).where(StorySummary.project_id==pid,
        StorySummary.scope_type==p.scope_type,StorySummary.scope_id==p.scope_id))).first()
    if obj:
        obj.summary=summary; obj.stale=False; obj.narrative_end=narr_end
    else:
        obj=StorySummary(project_id=pid,scope_type=p.scope_type,scope_id=p.scope_id,
                         summary=summary,stale=False,narrative_end=narr_end)
        db.add(obj)
    await db.commit(); await db.refresh(obj)
    return obj

async def _ancestors(db,pid,scope_type,scope_id):
    return await ancestor_chain(db,pid,scope_type,scope_id)

@router.get("/projects/{pid}/summaries/coverage")
async def summaries_coverage(pid:str,db:AsyncSession=Depends(get_db)):
    """Đếm summary còn thiếu/stale theo tầng + danh sách pending để UI chạy queue."""
    await project_ok(db,pid)
    sums={(s.scope_type,s.scope_id):s for s in (await db.scalars(
        select(StorySummary).where(StorySummary.project_id==pid))).all()}
    chapters=list((await db.scalars(select(Chapter).where(
        Chapter.project_id==pid).order_by(Chapter.order_index))).all())
    scenes=list((await db.scalars(select(Scene).where(
        Scene.project_id==pid).order_by(Scene.order_index))).all())
    arcs=list((await db.scalars(select(Arc).where(
        Arc.project_id==pid).order_by(Arc.order_index))).all())
    vols=list((await db.scalars(select(Volume).where(
        Volume.project_id==pid).order_by(Volume.order_index))).all())
    ch_by_id={c.id:c for c in chapters}
    ch_in_arc={a.id:[c for c in chapters if c.arc_id==a.id] for a in arcs}
    ch_in_vol={v.id:[c for c in chapters if c.volume_id==v.id] for v in vols}
    arcs_in_vol={v.id:[a for a in arcs if a.volume_id==v.id] for v in vols}

    levels={st:{"total":0,"fresh":0,"stale":0,"missing":0,"skipped":0} for st in HIERARCHY}
    pending=[]
    def emit(scope_type,scope_id,label,has_content):
        lv=levels[scope_type]; lv["total"]+=1
        s=sums.get((scope_type,scope_id))
        if not has_content:
            lv["skipped"]+=1; return
        if s is None:
            lv["missing"]+=1; pending.append({"scope_type":scope_type,"scope_id":scope_id,"label":label,"reason":"missing"})
        elif s.stale:
            lv["stale"]+=1; pending.append({"scope_type":scope_type,"scope_id":scope_id,"label":label,"reason":"stale"})
        else:
            lv["fresh"]+=1
    for sc in scenes:
        ch=ch_by_id.get(sc.chapter_id)
        label=f"Ch.{ch.order_index if ch else '?'} · {sc.title or 'Cảnh'}"
        emit("scene",sc.id,label,bool((sc.prose or "").strip() or (sc.skeleton or "").strip()))
    for c in chapters:
        kids=[s for s in scenes if s.chapter_id==c.id]
        emit("chapter",c.id,f"Chương {c.order_index}. {c.title or ''}".strip(),bool(kids))
    for a in arcs:
        emit("arc",a.id,f"Hồi: {a.title or ''}".strip(),bool(ch_in_arc.get(a.id)))
    for v in vols:
        has=bool(arcs_in_vol.get(v.id) or [c for c in ch_in_vol.get(v.id,[]) if not c.arc_id])
        emit("volume",v.id,f"Quyển: {v.title or ''}".strip(),has)
    proj=await db.get(Project,pid)
    has_any=bool(vols or [c for c in chapters if not c.volume_id])
    emit("story",pid,f"Truyện: {proj.name}",has_any)
    return {"levels":levels,"pending":pending,
            "pending_count":len(pending)}

@router.post("/projects/{pid}/summaries/{sid}/invalidate")
async def invalidate_summary(pid:str,sid:str,db:AsyncSession=Depends(get_db)):
    obj=await db.get(StorySummary,sid)
    if not obj or obj.project_id!=pid: raise HTTPException(404,"summary not found")
    chain=await _ancestors(db,pid,obj.scope_type,obj.scope_id)
    touched=[]
    for st,sid_ in chain:
        q=select(StorySummary).where(StorySummary.project_id==pid,StorySummary.scope_type==st,StorySummary.scope_id==sid_)
        for s in (await db.scalars(q)).all():
            s.stale=True; touched.append(s.id)
    await db.commit()
    return {"invalidated_chain":[t for t,_ in chain],"marked_stale":touched}
@router.get("/projects/{pid}/summaries/stale-backlog")
async def stale_backlog(pid:str,limit:int=20,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    rows=(await db.scalars(select(StorySummary).where(StorySummary.project_id==pid))).all()
    items=[{"id":s.id,"scope_type":s.scope_type,"scope_id":s.scope_id,"stale":s.stale} for s in rows]
    return bounded_backlog(items,limit)

@router.post("/projects/{pid}/retcon-proposals")
async def create_retcon(pid:str,p:RetconCreate,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    snap=impact_preview(p.target_type,p.target_id,await _ref_graph(db,pid))
    return await add(db,RetconProposal(project_id=pid,impact_snapshot_json=json.dumps(snap),**p.model_dump()))
@router.get("/projects/{pid}/retcon-proposals")
async def list_retcons(pid:str,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    rows=(await db.scalars(select(RetconProposal).where(RetconProposal.project_id==pid))).all()
    return [{"id":r.id,"project_id":r.project_id,"target_type":r.target_type,"target_id":r.target_id,
             "proposal":r.proposal,"impact":json.loads(r.impact_snapshot_json)} for r in rows]

@router.get("/projects/{pid}/impact-preview")
async def preview(pid:str,target_type:str,target_id:str,depth:int=2,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    return impact_preview(target_type,target_id,await _ref_graph(db,pid),depth=max(1,min(depth,4)))
