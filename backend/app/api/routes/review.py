
import json
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models import Project,Scene,Chapter
from app.models.review import SuggestedChange
from app.models.story import Character,Location,Item,Ability
from app.models.truth import CanonFact,StoryEvent,StoryState,KnowledgeState
from app.models.narrative import Thread,ThreadBeat
from app.schemas.extras import *
router=APIRouter()

MATERIALIZABLE={"canon_fact","story_event","ai_draft","entity","story_state","knowledge_state","thread_beat"}

_ENTITY_TABLES={"character":Character,"location":Location,"item":Item,"ability":Ability}

async def _resolve_entity(db,pid,kind,name):
    """name → entity id in the right table. Returns (entity_id, created_bool)."""
    cls=_ENTITY_TABLES.get((kind or "character").lower())
    if cls is None or not name: return None,False
    norm=name.strip().lower()
    for row in (await db.scalars(select(cls).where(cls.project_id==pid))).all():
        if (row.name or "").strip().lower()==norm: return row.id,False
    return None,False

async def _find_fact(db,pid,predicate,value_text):
    for f in (await db.scalars(select(CanonFact).where(CanonFact.project_id==pid))).all():
        if f.predicate==predicate and f.value_text==value_text: return f
    return None

async def project_ok(db,pid):
    if not await db.get(Project,pid): raise HTTPException(404,"project not found")
async def scoped(db,cls,obj_id,pid,label):
    obj=await db.get(cls,obj_id)
    if not obj or getattr(obj,"project_id",None)!=pid: raise HTTPException(400,f"{label} outside project")
    return obj
async def add(db,obj):
    db.add(obj); await db.commit(); await db.refresh(obj); return obj

def _view(s:SuggestedChange):
    try: payload=json.loads(s.payload_json)
    except Exception: payload={"raw":s.payload_json}
    return {"id":s.id,"project_id":s.project_id,"scene_id":s.scene_id,"change_type":s.change_type,
            "payload":payload,"status":s.status,"auto_applied":s.auto_applied}

@router.post("/projects/{pid}/suggestions")
async def create_suggestion(pid:str,p:SuggestionCreate,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    if p.scene_id: await scoped(db,Scene,p.scene_id,pid,"scene")
    obj=await add(db,SuggestedChange(project_id=pid,scene_id=p.scene_id,change_type=p.change_type,
                                     payload_json=json.dumps(p.payload),status="pending",auto_applied=False))
    return _view(obj)
@router.get("/projects/{pid}/suggestions")
async def list_suggestions(pid:str,status:str|None=None,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    q=select(SuggestedChange).where(SuggestedChange.project_id==pid)
    if status: q=q.where(SuggestedChange.status==status)
    return [_view(s) for s in (await db.scalars(q.order_by(SuggestedChange.id))).all()]

@router.post("/projects/{pid}/suggestions/{sid}/approve")
async def approve_suggestion(pid:str,sid:str,db:AsyncSession=Depends(get_db)):
    s=await scoped(db,SuggestedChange,sid,pid,"suggestion")
    if s.status!="pending": raise HTTPException(400,"suggestion already resolved")
    payload=json.loads(s.payload_json or "{}")
    applied=None
    if s.change_type=="canon_fact":
        applied=await add(db,CanonFact(project_id=pid,
            subject_type=payload.get("subject_type","story"),subject_id=payload.get("subject_id"),
            predicate=payload.get("predicate","fact"),value_text=payload.get("value_text",""),
            truth_status="INFERRED",locked=False,source_scene_id=s.scene_id))
    elif s.change_type=="story_event":
        applied=await add(db,StoryEvent(project_id=pid,scene_id=s.scene_id,
            event_type=payload.get("event_type","event"),summary=payload.get("summary","")))
    elif s.change_type=="entity":
        kind=(payload.get("kind") or "character").lower()
        if kind=="location":
            applied=await add(db,Location(project_id=pid,
                name=payload.get("name","(không tên)"),
                description=payload.get("summary")))
        else:
            name=payload.get("name","").strip()
            if name:
                dup=await db.scalar(select(Character).where(
                    Character.project_id==pid,Character.name==name))
                if dup is None:
                    applied=await add(db,Character(project_id=pid,name=name,
                        role=payload.get("role") or "phụ",
                        summary=payload.get("summary")))
    elif s.change_type=="ai_draft":
        text=payload.get("text","")
        if s.scene_id and text.strip():
            scene=await db.get(Scene,s.scene_id)
            if scene and scene.project_id==pid:
                scene.prose=(scene.prose.rstrip()+"\n\n"+text).lstrip() if scene.prose else text
                await db.commit()
                applied=scene
    elif s.change_type=="story_state":
        scene=await db.get(Scene,s.scene_id) if s.scene_id else None
        eid=payload.get("entity_id")
        if not eid:
            eid,_=await _resolve_entity(db,pid,payload.get("entity_kind"),payload.get("entity_name",""))
        if eid:
            applied=await add(db,StoryState(project_id=pid,
                entity_type=payload.get("entity_kind","character"),entity_id=eid,
                key=payload.get("key","status"),value_text=payload.get("value","") or payload.get("value_text",""),
                story_time=payload.get("story_time") if payload.get("story_time") is not None else (scene.story_time if scene else None),
                narrative_order=scene.narrative_order if scene else None))
    elif s.change_type=="knowledge_state":
        scene=await db.get(Scene,s.scene_id) if s.scene_id else None
        kid=payload.get("knower_id") or ("reader" if payload.get("knower_name","").strip().lower() in ("reader","độc giả") else None)
        ktype="reader" if kid=="reader" else "character"
        if not kid:
            kid,_=await _resolve_entity(db,pid,"character",payload.get("knower_name",""))
        fid=payload.get("fact_id")
        if not fid:
            pred=payload.get("predicate","fact"); val=payload.get("value_text","")
            f=await _find_fact(db,pid,pred,val)
            if not f:
                f=await add(db,CanonFact(project_id=pid,subject_type="story",predicate=pred,
                    value_text=val or payload.get("fact",""),truth_status="INFERRED",
                    source_scene_id=s.scene_id))
            fid=f.id
        if kid:
            applied=await add(db,KnowledgeState(project_id=pid,knower_type=ktype,knower_id=kid,
                fact_id=fid,state=payload.get("state","KNOWS"),
                acquired_story_time=payload.get("story_time") if payload.get("story_time") is not None else (scene.story_time if scene else None),
                acquired_narrative_order=scene.narrative_order if scene else None))
    elif s.change_type=="thread_beat":
        scene=await db.get(Scene,s.scene_id) if s.scene_id else None
        tid=payload.get("thread_id")
        if not tid:
            want=(payload.get("thread_title") or "").strip().lower()
            for t in (await db.scalars(select(Thread).where(Thread.project_id==pid))).all():
                if t.title.strip().lower()==want: tid=t.id; break
        if tid:
            norder=payload.get("narrative_order")
            if norder is None and scene: norder=scene.narrative_order
            if norder is None and scene:
                ch=await db.get(Chapter,scene.chapter_id); norder=ch.order_index if ch else None
            applied=await add(db,ThreadBeat(project_id=pid,thread_id=tid,scene_id=s.scene_id,
                beat_type=payload.get("beat_type","reinforcement"),
                narrative_order=norder,notes=payload.get("note") or payload.get("notes")))
    s.status="approved"; await db.commit(); await db.refresh(s)
    out=_view(s)
    if applied is not None: out["applied_id"]=applied.id
    out["materialized"]=s.change_type in MATERIALIZABLE
    if applied is None and s.change_type in MATERIALIZABLE:
        out["warning"]="Đã duyệt nhưng không ghi được — thiếu dữ kiện hoặc không tìm thấy thực thể tương ứng."
    return out

@router.post("/projects/{pid}/suggestions/{sid}/reject")
async def reject_suggestion(pid:str,sid:str,db:AsyncSession=Depends(get_db)):
    s=await scoped(db,SuggestedChange,sid,pid,"suggestion")
    if s.status!="pending": raise HTTPException(400,"suggestion already resolved")
    s.status="rejected"; await db.commit(); await db.refresh(s); return _view(s)
