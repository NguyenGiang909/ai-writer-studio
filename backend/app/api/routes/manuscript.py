import json
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models import Project, Volume, Arc, Chapter, Scene
from app.schemas.manuscript import *

router = APIRouter()

async def project_or_404(db: AsyncSession, project_id: str):
    obj = await db.get(Project, project_id)
    if not obj: raise HTTPException(404, "project not found")
    return obj

@router.post("/projects", response_model=ProjectOut)
async def create_project(payload: ProjectCreate, db: AsyncSession=Depends(get_db)):
    obj=Project(**payload.model_dump()); db.add(obj); await db.commit(); await db.refresh(obj); return obj

@router.get("/projects", response_model=list[ProjectOut])
async def list_projects(db: AsyncSession=Depends(get_db)):
    return list((await db.scalars(select(Project).order_by(Project.created_at))).all())

@router.patch("/projects/{project_id}", response_model=ProjectOut)
async def patch_project(project_id: str, payload: ProjectPatch, db: AsyncSession=Depends(get_db)):
    obj = await project_or_404(db, project_id)
    for k, v in payload.model_dump(exclude_unset=True).items(): setattr(obj, k, v)
    await db.commit(); await db.refresh(obj); return obj

@router.delete("/projects/{project_id}")
async def delete_project(project_id: str, db: AsyncSession=Depends(get_db)):
    obj = await project_or_404(db, project_id)
    await db.delete(obj); await db.commit()
    return {"deleted": project_id}

@router.post("/projects/{project_id}/volumes", response_model=VolumeOut)
async def create_volume(project_id: str, payload: VolumeCreate, db: AsyncSession=Depends(get_db)):
    await project_or_404(db, project_id)
    obj=Volume(project_id=project_id, **payload.model_dump()); db.add(obj); await db.commit(); await db.refresh(obj); return obj

@router.patch("/projects/{project_id}/volumes/{oid}")
async def patch_volume(project_id:str,oid:str,data:dict=Body(...),db:AsyncSession=Depends(get_db)):
    obj=await db.get(Volume,oid)
    if not obj or obj.project_id!=project_id: raise HTTPException(404,"volume not found")
    for k,v in data.items():
        if k in obj.__table__.columns: setattr(obj,k,v)
    await db.commit(); await db.refresh(obj); return obj
@router.delete("/projects/{project_id}/volumes/{oid}")
async def delete_volume(project_id:str,oid:str,db:AsyncSession=Depends(get_db)):
    obj=await db.get(Volume,oid)
    if not obj or obj.project_id!=project_id: raise HTTPException(404,"volume not found")
    await db.delete(obj); await db.commit(); return {"deleted":oid}

@router.post("/projects/{project_id}/arcs", response_model=ArcOut)
async def create_arc(project_id: str, payload: ArcCreate, db: AsyncSession=Depends(get_db)):
    await project_or_404(db, project_id)
    if payload.volume_id:
        v=await db.get(Volume,payload.volume_id)
        if not v or v.project_id != project_id: raise HTTPException(400,"volume outside project")
    obj=Arc(project_id=project_id, **payload.model_dump()); db.add(obj); await db.commit(); await db.refresh(obj); return obj

@router.patch("/projects/{project_id}/arcs/{oid}")
async def patch_arc(project_id:str,oid:str,data:dict=Body(...),db:AsyncSession=Depends(get_db)):
    obj=await db.get(Arc,oid)
    if not obj or obj.project_id!=project_id: raise HTTPException(404,"arc not found")
    for k,v in data.items():
        if k in obj.__table__.columns: setattr(obj,k,v)
    await db.commit(); await db.refresh(obj); return obj
@router.delete("/projects/{project_id}/arcs/{oid}")
async def delete_arc(project_id:str,oid:str,db:AsyncSession=Depends(get_db)):
    obj=await db.get(Arc,oid)
    if not obj or obj.project_id!=project_id: raise HTTPException(404,"arc not found")
    await db.delete(obj); await db.commit(); return {"deleted":oid}

@router.post("/projects/{project_id}/chapters", response_model=ChapterOut)
async def create_chapter(project_id: str, payload: ChapterCreate, db: AsyncSession=Depends(get_db)):
    await project_or_404(db, project_id)
    if payload.volume_id:
        v=await db.get(Volume,payload.volume_id)
        if not v or v.project_id != project_id: raise HTTPException(400,"volume outside project")
    if payload.arc_id:
        a=await db.get(Arc,payload.arc_id)
        if not a or a.project_id != project_id: raise HTTPException(400,"arc outside project")
    obj=Chapter(project_id=project_id, **payload.model_dump()); db.add(obj); await db.commit(); await db.refresh(obj); return obj

@router.patch("/projects/{project_id}/chapters/{chapter_id}", response_model=ChapterOut)
async def patch_chapter(project_id: str, chapter_id: str, payload: ChapterPatch, db: AsyncSession=Depends(get_db)):
    obj=await db.get(Chapter,chapter_id)
    if not obj or obj.project_id != project_id: raise HTTPException(404,"chapter not found in project")
    data=payload.model_dump(exclude_unset=True)
    if data.get("arc_id"):
        a=await db.get(Arc,data["arc_id"])
        if not a or a.project_id != project_id: raise HTTPException(400,"arc outside project")
    for k,v in data.items(): setattr(obj,k,v)
    await db.commit(); await db.refresh(obj); return obj

@router.delete("/projects/{project_id}/chapters/{chapter_id}")
async def delete_chapter(project_id:str,chapter_id:str,db:AsyncSession=Depends(get_db)):
    obj=await db.get(Chapter,chapter_id)
    if not obj or obj.project_id!=project_id: raise HTTPException(404,"chapter not found")
    await db.delete(obj); await db.commit(); return {"deleted":chapter_id}

@router.post("/projects/{project_id}/chapters/{chapter_id}/scenes", response_model=SceneOut)
async def create_scene(project_id: str, chapter_id: str, payload: SceneCreate, db: AsyncSession=Depends(get_db)):
    await project_or_404(db, project_id)
    ch=await db.get(Chapter,chapter_id)
    if not ch or ch.project_id != project_id: raise HTTPException(404,"chapter not found in project")
    data=payload.model_dump()
    if data.get("story_time") is None:
        prev=list((await db.scalars(select(Scene).where(
            Scene.chapter_id==chapter_id).order_by(Scene.order_index.desc()))).all())
        if prev and prev[0].story_time is not None:
            data["story_time"]=prev[0].story_time
    if data.get("narrative_order") is None:
        data["narrative_order"]=ch.order_index
    obj=Scene(project_id=project_id, chapter_id=chapter_id, **data)
    db.add(obj); await db.commit(); await db.refresh(obj); return obj

@router.post("/projects/{project_id}/chapters/{chapter_id}/scenes/batch", response_model=list[SceneOut])
async def create_scenes_batch(project_id: str, chapter_id: str, payload: SceneBatchCreate, db: AsyncSession=Depends(get_db)):
    """Tạo nhiều cảnh trong 1 transaction — order_index tự nối tiếp từ max hiện có."""
    await project_or_404(db, project_id)
    ch=await db.get(Chapter,chapter_id)
    if not ch or ch.project_id != project_id: raise HTTPException(404,"chapter not found in project")
    prev=list((await db.scalars(select(Scene).where(
        Scene.chapter_id==chapter_id).order_by(Scene.order_index.desc()))).all())
    next_order=(prev[0].order_index+1) if prev else 1
    prev_time=prev[0].story_time if prev else None
    objs=[]
    for i,item in enumerate(payload.scenes):
        data=item.model_dump()
        data["order_index"]=next_order+i
        data["story_time"]=prev_time
        data["narrative_order"]=ch.order_index
        objs.append(Scene(project_id=project_id, chapter_id=chapter_id, **data))
    db.add_all(objs); await db.commit()
    for o in objs: await db.refresh(o)
    return objs

@router.patch("/projects/{project_id}/scenes/{scene_id}", response_model=SceneOut)
async def patch_scene(project_id: str, scene_id: str, payload: ScenePatch, db: AsyncSession=Depends(get_db)):
    obj=await db.get(Scene,scene_id)
    if not obj or obj.project_id != project_id: raise HTTPException(404,"scene not found in project")
    data=payload.model_dump(exclude_unset=True)
    if "brief" in data:
        data["brief_json"]=json.dumps(data.pop("brief"),ensure_ascii=False) if data["brief"] is not None else None
        data.pop("brief",None)
    if data.get("location_id"):
        from app.models.story import Location
        loc=await db.get(Location,data["location_id"])
        if not loc or loc.project_id!=project_id: raise HTTPException(400,"location outside project")
    for k,v in data.items(): setattr(obj,k,v)
    if "prose" in data:
        # prose đổi → các tóm tắt phủ cảnh này (scene→chapter→arc/volume→story) hết hạn
        from app.models.memory import StorySummary
        from app.services.memory import ancestor_chain
        chain=set(await ancestor_chain(db,project_id,"scene",scene_id))
        for s in (await db.scalars(select(StorySummary).where(
            StorySummary.project_id==project_id))).all():
            if (s.scope_type,s.scope_id) in chain and not s.stale:
                s.stale=True
    await db.commit(); await db.refresh(obj); return obj

@router.delete("/projects/{project_id}/scenes/{scene_id}")
async def delete_scene(project_id:str,scene_id:str,db:AsyncSession=Depends(get_db)):
    obj=await db.get(Scene,scene_id)
    if not obj or obj.project_id!=project_id: raise HTTPException(404,"scene not found")
    await db.delete(obj); await db.commit(); return {"deleted":scene_id}

@router.get("/projects/{project_id}/manuscript")
async def manuscript_tree(project_id: str, db: AsyncSession=Depends(get_db)):
    await project_or_404(db, project_id)
    volumes=list((await db.scalars(select(Volume).where(Volume.project_id==project_id).order_by(Volume.order_index))).all())
    arcs=list((await db.scalars(select(Arc).where(Arc.project_id==project_id).order_by(Arc.order_index))).all())
    chapters=list((await db.scalars(select(Chapter).where(Chapter.project_id==project_id).order_by(Chapter.order_index))).all())
    scenes=list((await db.scalars(select(Scene).where(Scene.project_id==project_id).order_by(Scene.chapter_id,Scene.order_index))).all())
    by_ch={}
    for s in scenes: by_ch.setdefault(s.chapter_id,[]).append(SceneOut.model_validate(s).model_dump())
    return {
        "project_id":project_id,
        "volumes":[VolumeOut.model_validate(v).model_dump() for v in volumes],
        "arcs":[ArcOut.model_validate(a).model_dump() for a in arcs],
        "chapters":[{**ChapterOut.model_validate(c).model_dump(),"scenes":by_ch.get(c.id,[])} for c in chapters],
    }
