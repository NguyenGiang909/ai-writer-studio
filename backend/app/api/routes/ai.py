
import json,re
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models import Project,Chapter,Scene
from app.models.review import SuggestedChange
from app.models.story import Character,Alias,Location,Ability,Item,Relationship
from app.models.narrative import Thread,ThreadBeat
from app.models.truth import KnowledgeState,StoryState,CanonFact
from app.models.memory import AiTurn
from app.services.state import states_at,effective_at
from app.ai.context import ContextBuilder,ContextItem
from app.ai.router import ModelRouter,ModelRequest
from app.ai.compose import build_story_prompt
from app.ai.writer import parse_author_brief,allocate_word_budget,line_diff
from app.services.continuity import restricted_appearance,location_conflict,ability_locked,item_owner_mismatch,relationship_ended,stale_thread,dedupe,Issue
from app.schemas.extras import *
router=APIRouter()

async def project_ok(db,pid):
    if not await db.get(Project,pid): raise HTTPException(404,"project not found")

@router.post("/projects/{pid}/context/preview")
async def context_preview(pid:str,p:ContextPreviewRequest,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    items=[ContextItem(bucket=i.bucket,text=i.text,priority=i.priority,source=i.source,
                       estimated_tokens=i.estimated_tokens) for i in p.items]
    text,manifest=ContextBuilder().build(items,budget=p.budget)
    return {"text":text,"manifest":{"included":manifest.included,"omitted":manifest.omitted,
            "total_estimated_tokens":manifest.total_estimated_tokens}}

@router.post("/writer/parse-brief")
async def parse_brief(p:ParseBriefRequest):
    plan=parse_author_brief(p.text,p.target_words)
    return {"beats":plan.beats,"constraints":plan.constraints,
            "target_words":plan.target_words,"plan_hash":plan.plan_hash}
@router.post("/writer/word-budget")
async def word_budget(p:WordBudgetRequest):
    try: return {"allocation":allocate_word_budget(p.target,p.scene_count)}
    except ValueError: raise HTTPException(400,"scene_count must be >= 1")
@router.post("/writer/line-diff")
async def diff(p:LineDiffRequest):
    return {"diff":line_diff(p.original,p.replacement)}

@router.post("/projects/{pid}/ai/complete")
async def complete(pid:str,p:CompleteRequest,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    system,prompt,manifest=await build_story_prompt(db,pid,p.task,p.prompt,p.scene_id,getattr(p,"chapter_id",None))
    try:
        result=await ModelRouter(db).complete(
            ModelRequest(task=p.task,prompt=prompt,model=p.model,project_id=pid,system=system))
    except RuntimeError as e: raise HTTPException(503,str(e))
    db.add(AiTurn(project_id=pid,scope_id=p.scene_id or pid,task=p.task,
                  prompt_excerpt=p.prompt[:1500],reply_text=(result.text or "")[:4000],
                  provider=result.provider or "",model=result.model or ""))
    await db.commit()
    issues=[]
    if p.task in {"writing","expand","scene_expand","revision"} and p.scene_id and result.text:
        sc=await db.get(Scene,p.scene_id)
        if sc:
            st_t=sc.story_time if sc.story_time is not None else sc.narrative_order
            chars={c.id:c for c in (await db.scalars(select(Character).where(Character.project_id==pid))).all()}
            aliases=list((await db.scalars(select(Alias).where(Alias.project_id==pid))).all())
            life=await states_at(db,pid,story_time=st_t,entity_type="character",key="lifecycle")
            for st in life:
                c=chars.get(st.entity_id)
                if not c or not c.name: continue
                names=[c.name]+[a.alias for a in aliases if a.character_id==c.id and a.alias]
                names+=[w for w in re.split(r"\s+",c.name) if len(w)>=4]
                hit=any(re.search(r"\b"+re.escape(n)+r"\b",result.text,
                                  re.IGNORECASE if " " in n else 0) for n in dict.fromkeys(names))
                if not hit: continue
                iss=restricted_appearance(c.name,st.value_text,sc.scene_type,st.story_time,st_t,sc.id,c.id)
                if iss: issues.append({"code":iss.code,"severity":iss.severity,"message":iss.message})
    return {"reply":result.text,"provider":result.provider,"model":result.model,
            "usage":result.usage,"context":manifest,"issues":issues}

@router.post("/projects/{pid}/ai/context-manifest")
async def context_manifest(pid:str,p:ContextManifestRequest,db:AsyncSession=Depends(get_db)):
    """Preview what context the AI would receive — no model call, free."""
    await project_ok(db,pid)
    _sys,_prompt,manifest=await build_story_prompt(db,pid,p.task or "writing","",p.scene_id,getattr(p,"chapter_id",None))
    return {"manifest":manifest}

@router.post("/projects/{pid}/scenes/{sid}/extract-suggestions")
async def extract_suggestions(pid:str,sid:str,db:AsyncSession=Depends(get_db)):
    """F2 after-write extraction: read scene prose → suggestions into Review queue."""
    await project_ok(db,pid)
    sc=await db.get(Scene,sid)
    if not sc or sc.project_id!=pid: raise HTTPException(404,"scene not found in project")
    if not (sc.prose or "").strip(): raise HTTPException(400,"scene has no prose to extract")
    system,prompt,_=await build_story_prompt(db,pid,"extraction",sc.prose.strip()[-8000:],sid)
    try:
        result=await ModelRouter(db).complete(
            ModelRequest(task="extraction",prompt=prompt,project_id=pid,system=system))
    except RuntimeError as e: raise HTTPException(503,str(e))
    data=_parse_json(result.text)
    created=[]
    for f in (data.get("canon_facts") or [])[:20]:
        created.append(await _mk(db,pid,sid,"canon_fact",f))
    for e in (data.get("events") or [])[:20]:
        created.append(await _mk(db,pid,sid,"story_event",e))
    for e in (data.get("entities") or [])[:20]:
        created.append(await _mk(db,pid,sid,"entity",e))
    for s_ in (data.get("story_states") or [])[:20]:
        created.append(await _mk(db,pid,sid,"story_state",s_))
    for k in (data.get("knowledge") or [])[:20]:
        created.append(await _mk(db,pid,sid,"knowledge_state",k))
    for t in (data.get("thread_touches") or [])[:20]:
        created.append(await _mk(db,pid,sid,"thread_beat",t))
    return {"created":len(created),"provider":result.provider,
            "items":[{"change_type":s.change_type,"payload":json.loads(s.payload_json)} for s in created]}

def _parse_json(text:str)->dict:
    t=(text or "").strip()
    if "```" in t:
        t=t.split("```",2)[1]
        if t.startswith("json"): t=t[4:]
        t=t.split("```")[0]
    try: return json.loads(t)
    except Exception:
        a,b=t.find("{"),t.rfind("}")
        try: return json.loads(t[a:b+1]) if a>=0 and b>a else {}
        except Exception: return {}

async def _mk(db,pid,sid,change_type,payload:dict):
    obj=SuggestedChange(project_id=pid,scene_id=sid,change_type=change_type,
        payload_json=json.dumps(payload or {},ensure_ascii=False),
        status="pending",auto_applied=False)
    db.add(obj); await db.commit(); await db.refresh(obj); return obj

@router.get("/projects/{pid}/continuity/check")
async def continuity_check(pid:str,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    issues=[]
    chapters={c.id:c for c in (await db.scalars(select(Chapter).where(Chapter.project_id==pid))).all()}
    scenes=list((await db.scalars(select(Scene).where(Scene.project_id==pid))).all())
    knowledge=list((await db.scalars(select(KnowledgeState).where(KnowledgeState.project_id==pid))).all())

    def scene_t(sc):
        return sc.story_time if sc.story_time is not None else sc.narrative_order

    # knowledge check moved below — needs `present` char map + entity maps built first

    # γ1 restricted lifecycle appearance — name match in prose vs StoryState at scene time
    chars={c.id:c for c in (await db.scalars(select(Character).where(Character.project_id==pid))).all()}
    aliases=list((await db.scalars(select(Alias).where(Alias.project_id==pid))).all())
    terms:dict[str,list[str]]={}
    for c in chars.values():
        ts=[c.name]+[a.alias for a in aliases if a.character_id==c.id and a.alias]
        ts+=[w for w in re.split(r"\s+",c.name or "") if len(w)>=4]
        terms[c.id]=[t for t in dict.fromkeys(ts) if t]
    life_states=await states_at(db,pid,entity_type="character",key="lifecycle")
    for sc in scenes:
        if not sc.prose: continue
        prose_l=sc.prose.lower()
        for st in life_states:
            c=chars.get(st.entity_id)
            if not c or not c.name: continue
            hit=False
            for t in terms.get(c.id,[]):
                if " " in t:
                    if re.search(r"\b"+re.escape(t)+r"\b",sc.prose,re.IGNORECASE): hit=True; break
                elif re.search(r"\b"+re.escape(t)+r"\b",sc.prose): hit=True; break
            if not hit: continue
            iss=restricted_appearance(c.name,st.value_text,sc.scene_type,
                                      st.story_time,scene_t(sc),sc.id,c.id)
            if iss: issues.append(iss)

    # γ4 location conflict — character "location" StoryState vs scene.location_id
    locs={l.id:l for l in (await db.scalars(select(Location).where(Location.project_id==pid))).all()}
    loc_states=list((await db.scalars(select(StoryState).where(
        StoryState.project_id==pid,StoryState.entity_type=="character",
        StoryState.key=="location"))).all())
    if loc_states:
        for sc in scenes:
            if not sc.prose or not sc.location_id: continue
            sloc=locs.get(sc.location_id)
            if not sloc: continue
            eff=effective_at(loc_states,scene_t(sc))
            for (et,eid,k),st in eff.items():
                c=chars.get(eid)
                if not c or not c.name: continue
                hit=any(re.search(r"\b"+re.escape(t)+r"\b",sc.prose,
                                  re.IGNORECASE if " " in t else 0)
                        for t in terms.get(c.id,[]))
                if not hit: continue
                iss=location_conflict(c.name,st.value_text,sloc.name,sloc.id,
                                      st.story_time,scene_t(sc),sc.id,c.id)
                if iss: issues.append(iss)

    # γ5 ability not unlocked — ability name in prose vs its status StoryState
    abilities=list((await db.scalars(select(Ability).where(Ability.project_id==pid))).all())
    if abilities:
        ab_states=list((await db.scalars(select(StoryState).where(
            StoryState.project_id==pid,StoryState.entity_type=="ability",
            StoryState.key=="status"))).all())
        ab_latest={}
        for s in ab_states:
            cur=ab_latest.get(s.entity_id)
            if cur is None or (s.story_time or -1)>=(cur.story_time or -1): ab_latest[s.entity_id]=s
        for sc in scenes:
            if not sc.prose: continue
            eff=effective_at(ab_states,scene_t(sc))
            for ab in abilities:
                if not ab.name or not re.search(r"\b"+re.escape(ab.name)+r"\b",sc.prose,re.IGNORECASE): continue
                st=eff.get(("ability",ab.id,"status")) or ab_latest.get(ab.id)
                iss=ability_locked(ab.name,st.value_text if st else None,
                                   st.story_time if st else None,scene_t(sc),sc.id,ab.id)
                if iss: issues.append(iss)

    # presence map: which characters' names actually appear in each scene's prose
    present:dict[str,set[str]]={}
    for sc in scenes:
        if not sc.prose: continue
        hit=set()
        for c in chars.values():
            if not c.name: continue
            if any(re.search(r"\b"+re.escape(t)+r"\b",sc.prose,
                             re.IGNORECASE if " " in t else 0) for t in terms.get(c.id,[])):
                hit.add(c.id)
        present[sc.id]=hit

    # γ7 item ownership — item name in prose but recorded holder absent
    items={i.id:i for i in (await db.scalars(select(Item).where(Item.project_id==pid))).all()}
    own_states=list((await db.scalars(select(StoryState).where(
        StoryState.project_id==pid,StoryState.entity_type=="item",
        StoryState.key=="ownership"))).all())

    # knowledge leaks — nhân vật thể hiện tri thức trước mốc họ được nó.
    # Cảnh có POV: chỉ POV đó mới "lộ". Không POV (tác giả kể): chỉ flag khi
    # knower có mặt trong văn. Và chỉ tính là lộ khi fact thật sự được nhắc tới.
    abilities_map={a.id:a for a in abilities} if abilities else {}
    facts_by_id={f.id:f for f in (await db.scalars(select(CanonFact).where(CanonFact.project_id==pid))).all()}
    _SUBJ={"item":items,"character":chars,"location":locs,"ability":abilities_map}
    def _fact_terms(f):
        if not f: return []
        ts=[]
        ent=_SUBJ.get(f.subject_type,{}).get(f.subject_id)
        nm=getattr(ent,"name",None)
        if nm: ts.append(nm)
        ts += [w for w in re.findall(r"[\wÀ-ỹ]+", f.value_text or "") if len(w)>=5]
        return list(dict.fromkeys(ts))
    def _fact_label(f):
        if not f: return "dữ kiện"
        ent=_SUBJ.get(f.subject_type,{}).get(f.subject_id)
        nm=getattr(ent,"name",None) or "?"
        return f"{f.predicate.replace('_',' ')} của {nm}" if f.predicate else (f.value_text or "?")[:90]
    for sc in scenes:
        ch=chapters.get(sc.chapter_id)
        if not ch or not sc.prose: continue
        for k in knowledge:
            if not k.knower_id or k.knower_type!="character": continue
            can_leak=(k.knower_id==sc.pov_character_id) if sc.pov_character_id \
                     else (k.knower_id in present.get(sc.id,set()))
            if not can_leak: continue
            if (k.acquired_narrative_order is None or k.acquired_narrative_order<=ch.order_index) and \
               (k.acquired_story_time is None or k.acquired_story_time<=scene_t(sc)):
                continue
            f=facts_by_id.get(k.fact_id)
            fterms=_fact_terms(f)
            if fterms and not any(re.search(r"\b"+re.escape(t)+r"\b",sc.prose,re.IGNORECASE) for t in fterms):
                continue
            kn=chars.get(k.knower_id)
            acq=k.acquired_narrative_order if k.acquired_narrative_order is not None else k.acquired_story_time
            issues.append(Issue(
                "KNOWLEDGE_LEAK","knowledge","warning",
                f"{kn.name if kn else 'Nhân vật'} mới biết { _fact_label(f)} từ mốc {acq} — cảnh này ở mốc {ch.order_index}; kiểm tra cảnh có để lộ không.",
                {"scene_id":sc.id,"knower_id":k.knower_id,"fact_id":k.fact_id,
                 "acquired_narrative_order":k.acquired_narrative_order,
                 "acquired_story_time":k.acquired_story_time,
                 "scene_chapter":ch.order_index,"scene_time":scene_t(sc)}))

    if items and own_states:
        for sc in scenes:
            if not sc.prose: continue
            eff=effective_at(own_states,scene_t(sc))
            for it in items.values():
                if not it.name or not re.search(r"\b"+re.escape(it.name)+r"\b",sc.prose,re.IGNORECASE): continue
                st=eff.get(("item",it.id,"ownership"))
                if not st: continue
                owner_id=st.value_text.strip()
                owner=chars.get(owner_id)
                iss=item_owner_mismatch(it.name,it.id,owner.name if owner else owner_id,
                                        owner_id,present.get(sc.id,set()),sc.id)
                if iss: issues.append(iss)

    # γ8 relationship ended/hostile — both members co-appear in prose
    rels=list((await db.scalars(select(Relationship).where(Relationship.project_id==pid))).all())
    rel_states=list((await db.scalars(select(StoryState).where(
        StoryState.project_id==pid,StoryState.entity_type=="relationship",
        StoryState.key=="status"))).all())
    if rels and rel_states:
        for sc in scenes:
            if not sc.prose: continue
            eff=effective_at(rel_states,scene_t(sc))
            for r in rels:
                st=eff.get(("relationship",r.id,"status"))
                if not st: continue
                pa=present.get(sc.id,set())
                if r.source_character_id in pa and r.target_character_id in pa:
                    iss=relationship_ended(
                        chars[r.source_character_id].name if r.source_character_id in chars else "?",
                        chars[r.target_character_id].name if r.target_character_id in chars else "?",
                        st.value_text,r.id,sc.id)
                    if iss: issues.append(iss)

    # γ3 narrative debt — open threads gone quiet or past payoff window
    threads=list((await db.scalars(select(Thread).where(Thread.project_id==pid,Thread.status=="OPEN"))).all())
    if threads:
        beats=list((await db.scalars(select(ThreadBeat).where(ThreadBeat.project_id==pid))).all())
        last_beat={}
        for b in beats:
            if b.narrative_order is None: continue
            last_beat[b.thread_id]=max(last_beat.get(b.thread_id,0),b.narrative_order)
        narr_orders=[sc.narrative_order for sc in scenes if sc.narrative_order is not None]
        current=max(narr_orders) if narr_orders else (max((c.order_index for c in chapters.values()),default=None))
        for th in threads:
            iss=stale_thread(th,last_beat.get(th.id),current)
            if iss: issues.append(iss)

    out=dedupe(issues)
    return {"issues":[{"code":i.code,"category":i.category,"severity":i.severity,
                       "message":i.message,"evidence":i.evidence} for i in out],
            "count":len(out),"auto_mutations":0}
