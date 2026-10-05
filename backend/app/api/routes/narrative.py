
from fastapi import APIRouter,Depends,HTTPException,Body
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models import Project,Scene
from app.models.narrative import Thread,ThreadBeat,ThreadDependency
from app.schemas.extras import *
router=APIRouter()

async def project_ok(db,pid):
    if not await db.get(Project,pid): raise HTTPException(404,"project not found")
async def scoped(db,cls,obj_id,pid,label):
    obj=await db.get(cls,obj_id)
    if not obj or getattr(obj,"project_id",None)!=pid: raise HTTPException(400,f"{label} outside project")
    return obj
async def add(db,obj):
    db.add(obj); await db.commit(); await db.refresh(obj); return obj

@router.post("/projects/{pid}/threads")
async def create_thread(pid:str,p:ThreadCreate,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid); return await add(db,Thread(project_id=pid,**p.model_dump()))
@router.get("/projects/{pid}/threads")
async def list_threads(pid:str,status:str|None=None,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    q=select(Thread).where(Thread.project_id==pid)
    if status: q=q.where(Thread.status==status)
    return list((await db.scalars(q.order_by(Thread.title))).all())
@router.patch("/projects/{pid}/threads/{tid}")
async def patch_thread(pid:str,tid:str,p:ThreadPatch,db:AsyncSession=Depends(get_db)):
    obj=await scoped(db,Thread,tid,pid,"thread")
    for k,v in p.model_dump(exclude_unset=True).items(): setattr(obj,k,v)
    await db.commit(); await db.refresh(obj); return obj
@router.delete("/projects/{pid}/threads/{tid}")
async def delete_thread(pid:str,tid:str,db:AsyncSession=Depends(get_db)):
    obj=await scoped(db,Thread,tid,pid,"thread")
    await db.delete(obj); await db.commit(); return {"deleted":True}

@router.patch("/projects/{pid}/thread-beats/{bid}")
async def patch_beat(pid:str,bid:str,data:dict=Body(...),db:AsyncSession=Depends(get_db)):
    obj=await scoped(db,ThreadBeat,bid,pid,"beat")
    for k,v in data.items():
        if k in obj.__table__.columns: setattr(obj,k,v)
    await db.commit(); await db.refresh(obj); return obj
@router.delete("/projects/{pid}/thread-beats/{bid}")
async def delete_beat(pid:str,bid:str,db:AsyncSession=Depends(get_db)):
    obj=await scoped(db,ThreadBeat,bid,pid,"beat")
    await db.delete(obj); await db.commit(); return {"deleted":True}
@router.delete("/projects/{pid}/thread-dependencies/{did}")
async def delete_dependency(pid:str,did:str,db:AsyncSession=Depends(get_db)):
    obj=await scoped(db,ThreadDependency,did,pid,"dependency")
    await db.delete(obj); await db.commit(); return {"deleted":True}

@router.post("/projects/{pid}/threads/{tid}/beats")
async def create_beat(pid:str,tid:str,p:ThreadBeatCreate,db:AsyncSession=Depends(get_db)):
    await scoped(db,Thread,tid,pid,"thread")
    if p.scene_id: await scoped(db,Scene,p.scene_id,pid,"scene")
    return await add(db,ThreadBeat(project_id=pid,thread_id=tid,**p.model_dump()))
@router.get("/projects/{pid}/threads/{tid}/beats")
async def list_beats(pid:str,tid:str,db:AsyncSession=Depends(get_db)):
    await scoped(db,Thread,tid,pid,"thread")
    return list((await db.scalars(select(ThreadBeat).where(ThreadBeat.thread_id==tid).order_by(ThreadBeat.narrative_order))).all())

@router.post("/projects/{pid}/thread-dependencies")
async def create_dependency(pid:str,p:ThreadDependencyCreate,db:AsyncSession=Depends(get_db)):
    if p.thread_id==p.depends_on_thread_id: raise HTTPException(400,"thread cannot depend on itself")
    await scoped(db,Thread,p.thread_id,pid,"thread")
    await scoped(db,Thread,p.depends_on_thread_id,pid,"dependency thread")
    rev=(await db.scalars(select(ThreadDependency).where(
        ThreadDependency.thread_id==p.depends_on_thread_id,
        ThreadDependency.depends_on_thread_id==p.thread_id))).first()
    if rev: raise HTTPException(400,"dependency cycle")
    return await add(db,ThreadDependency(project_id=pid,**p.model_dump()))
@router.get("/projects/{pid}/thread-dependencies")
async def list_dependencies(pid:str,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    return list((await db.scalars(select(ThreadDependency).where(ThreadDependency.project_id==pid))).all())
