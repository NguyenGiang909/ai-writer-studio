
import json
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models import Project,Volume,Arc,Chapter,Scene
from app.models.memory import StorySummary,RetconProposal
from app.models.narrative import Thread,ThreadBeat,ThreadDependency
from app.models.truth import StoryEvent,StoryState,KnowledgeState,CanonFact,AuthorDecision
from app.services.memory import HIERARCHY,invalidate_chain,bounded_backlog,impact_preview,ancestor_chain
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
async def _ancestors(db,pid,scope_type,scope_id):
    return await ancestor_chain(db,pid,scope_type,scope_id)

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
