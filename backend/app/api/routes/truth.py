
import json
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models import Project,Scene,Location
from app.models.truth import CanonFact,AuthorDecision,StoryEvent,StoryState,KnowledgeState,Secret
from app.schemas.extras import *
from app.services import temporal
router=APIRouter()

async def project_ok(db,pid):
    if not await db.get(Project,pid): raise HTTPException(404,"project not found")
async def scoped(db,cls,obj_id,pid,label):
    obj=await db.get(cls,obj_id)
    if not obj or getattr(obj,"project_id",None)!=pid: raise HTTPException(400,f"{label} outside project")
    return obj
async def add(db,obj):
    db.add(obj); await db.commit(); await db.refresh(obj); return obj
async def listing(db,cls,pid,col=None):
    return list((await db.scalars(select(cls).where(cls.project_id==pid).order_by(col or cls.id))).all())
async def patch(db,obj,payload):
    for k,v in payload.model_dump(exclude_unset=True).items(): setattr(obj,k,v)
    await db.commit(); await db.refresh(obj); return obj

# ---- Canon facts ----
@router.post("/projects/{pid}/canon-facts")
async def create_canon_fact(pid:str,p:CanonFactCreate,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    if p.source_scene_id: await scoped(db,Scene,p.source_scene_id,pid,"source scene")
    return await add(db,CanonFact(project_id=pid,**p.model_dump()))
@router.get("/projects/{pid}/canon-facts")
async def list_canon_facts(pid:str,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid); return await listing(db,CanonFact,pid)
@router.patch("/projects/{pid}/canon-facts/{fid}")
async def patch_canon_fact(pid:str,fid:str,p:CanonFactPatch,db:AsyncSession=Depends(get_db)):
    obj=await scoped(db,CanonFact,fid,pid,"canon fact"); return await patch(db,obj,p)
@router.delete("/projects/{pid}/canon-facts/{fid}")
async def delete_canon_fact(pid:str,fid:str,db:AsyncSession=Depends(get_db)):
    obj=await scoped(db,CanonFact,fid,pid,"canon fact")
    await db.delete(obj); await db.commit(); return {"deleted":fid}

# ---- Author decisions ----
@router.post("/projects/{pid}/author-decisions")
async def create_decision(pid:str,p:AuthorDecisionCreate,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    d=p.model_dump()
    if d.pop("rejected",None) is not None: d["rejected_json"]=json.dumps(p.rejected,ensure_ascii=False)
    return await add(db,AuthorDecision(project_id=pid,**d))
@router.get("/projects/{pid}/author-decisions")
async def list_decisions(pid:str,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid); return await listing(db,AuthorDecision,pid)
@router.patch("/projects/{pid}/author-decisions/{did}")
async def patch_decision(pid:str,did:str,p:AuthorDecisionPatch,db:AsyncSession=Depends(get_db)):
    obj=await scoped(db,AuthorDecision,did,pid,"author decision")
    d=p.model_dump(exclude_unset=True)
    if "rejected" in d:
        v=d.pop("rejected"); d["rejected_json"]=json.dumps(v,ensure_ascii=False) if v is not None else None
    for k,v in d.items(): setattr(obj,k,v)
    await db.commit(); await db.refresh(obj); return obj
@router.delete("/projects/{pid}/author-decisions/{did}")
async def delete_decision(pid:str,did:str,db:AsyncSession=Depends(get_db)):
    obj=await scoped(db,AuthorDecision,did,pid,"author decision")
    await db.delete(obj); await db.commit(); return {"deleted":did}

# ---- Story events ----
@router.post("/projects/{pid}/story-events")
async def create_event(pid:str,p:StoryEventCreate,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    if p.scene_id: await scoped(db,Scene,p.scene_id,pid,"scene")
    if p.location_id: await scoped(db,Location,p.location_id,pid,"location")
    return await add(db,StoryEvent(project_id=pid,**p.model_dump()))
@router.get("/projects/{pid}/story-events")
async def list_events(pid:str,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid); return await listing(db,StoryEvent,pid,StoryEvent.narrative_order)

# ---- Story state ----
@router.post("/projects/{pid}/story-states")
async def create_state(pid:str,p:StoryStateCreate,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    if p.source_event_id: await scoped(db,StoryEvent,p.source_event_id,pid,"source event")
    return await add(db,StoryState(project_id=pid,**p.model_dump()))
@router.get("/projects/{pid}/story-states")
async def list_states(pid:str,entity_id:str|None=None,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    q=select(StoryState).where(StoryState.project_id==pid)
    if entity_id: q=q.where(StoryState.entity_id==entity_id)
    return list((await db.scalars(q.order_by(StoryState.entity_id,StoryState.key))).all())
@router.get("/projects/{pid}/story-states/as-of")
async def state_as_of(pid:str,entity_id:str,key:str,story_time:int|None=None,narrative_order:int|None=None,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    row=await temporal.story_state_as_of(db,pid,entity_id,key,story_time,narrative_order)
    if not row: raise HTTPException(404,"no state at that point")
    return row

# ---- Knowledge state ----
@router.post("/projects/{pid}/knowledge-states")
async def create_knowledge(pid:str,p:KnowledgeStateCreate,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid); await scoped(db,CanonFact,p.fact_id,pid,"canon fact")
    d=p.model_dump()
    if d.get("knower_id")=="reader" and d.get("knower_type")=="character": d["knower_type"]="reader"
    return await add(db,KnowledgeState(project_id=pid,**d))
@router.get("/projects/{pid}/knowledge-states")
async def list_knowledge(pid:str,knower_id:str|None=None,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    q=select(KnowledgeState).where(KnowledgeState.project_id==pid)
    if knower_id: q=q.where(KnowledgeState.knower_id==knower_id)
    return list((await db.scalars(q.order_by(KnowledgeState.knower_id))).all())
@router.get("/projects/{pid}/knowledge-states/as-of")
async def knowledge_as_of(pid:str,knower_id:str,narrative_order:int|None=None,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    return await temporal.knowledge_as_of(db,pid,knower_id,narrative_order)

# ---- Secrets ----
@router.post("/projects/{pid}/secrets")
async def create_secret(pid:str,p:SecretCreate,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid); await scoped(db,CanonFact,p.fact_id,pid,"canon fact")
    return await add(db,Secret(project_id=pid,**p.model_dump()))
@router.get("/projects/{pid}/secrets")
async def list_secrets(pid:str,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid); return await listing(db,Secret,pid)

# ---- Generic PATCH/DELETE (dict body → chỉ ghi cột tồn tại) ----
from fastapi import Body

def _patch_del(cls,label,path):
    op=path.replace("-","_")
    @router.patch(f"/projects/{{pid}}/{path}/{{oid}}",operation_id=f"patch_{op}")
    async def _p(pid:str,oid:str,data:dict=Body(...),db:AsyncSession=Depends(get_db)):
        obj=await scoped(db,cls,oid,pid,label)
        for k,v in data.items():
            if k in obj.__table__.columns: setattr(obj,k,v)
        await db.commit(); await db.refresh(obj); return obj
    @router.delete(f"/projects/{{pid}}/{path}/{{oid}}",operation_id=f"delete_{op}")
    async def _d(pid:str,oid:str,db:AsyncSession=Depends(get_db)):
        obj=await scoped(db,cls,oid,pid,label)
        await db.delete(obj); await db.commit(); return {"deleted":oid}

_patch_del(StoryEvent,"story event","story-events")
_patch_del(StoryState,"story state","story-states")
_patch_del(KnowledgeState,"knowledge state","knowledge-states")
_patch_del(Secret,"secret","secrets")
