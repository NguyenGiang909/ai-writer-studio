import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models import Project, Volume, Arc, Chapter, Scene
from app.models.manuscript import SceneVersion
from app.schemas.manuscript import *

router = APIRouter()

async def project_or_404(db: AsyncSession, project_id: str):
    obj = await db.get(Project, project_id)
    if not obj: raise HTTPException(404, "project not found")
    return obj

# Autosave bắn PATCH liên tục — chỉ chốt 1 checkpoint mỗi 90s để lịch sử
# gồm các "mốc phiên sửa" thay vì hàng trăm bản gần giống nhau.
SNAPSHOT_WINDOW = timedelta(seconds=90)

async def _snapshot_version(db: AsyncSession, scene: Scene, prose: str, force: bool = False):
    """Lưu prose CŨ thành version. Bỏ qua nếu version mới nhất còn trong cửa sổ
    90s (trừ force=True dùng cho restore — không bao giờ mất trạng thái hiện tại)."""
    latest = (await db.scalars(select(SceneVersion).where(
        SceneVersion.scene_id == scene.id).order_by(SceneVersion.created_at.desc()))).first()
    now = datetime.utcnow()
    if not force and latest and (now - latest.created_at) < SNAPSHOT_WINDOW:
        return
    db.add(SceneVersion(project_id=scene.project_id, scene_id=scene.id,
                        title=scene.title, prose=prose or ""))

async def _stale_ancestor_summaries(db: AsyncSession, project_id: str, scene_id: str):
    # prose đổi → các tóm tắt phủ cảnh này (scene→chapter→arc/volume→story) hết hạn
    from app.models.memory import StorySummary
    from app.services.memory import ancestor_chain
    chain = set(await ancestor_chain(db, project_id, "scene", scene_id))
    for s in (await db.scalars(select(StorySummary).where(
        StorySummary.project_id == project_id))).all():
        if (s.scope_type, s.scope_id) in chain and not s.stale:
            s.stale = True

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
async def delete_chapter(project_id:str,chapter_id:str,compact:bool=True,db:AsyncSession=Depends(get_db)):
    """Xoá chương: dọn facts trích của chương + scenes(+versions); compact →
    khép trục narrative (chương sau tụt 1). Facts tác giả nhập tay giữ nguyên."""
    from app.services.repair import delete_chapter_full
    obj=await db.get(Chapter,chapter_id)
    if not obj or obj.project_id!=project_id: raise HTTPException(404,"chapter not found")
    removed=await delete_chapter_full(db,project_id,obj,compact=compact)
    await db.commit(); return {"deleted":chapter_id,"removed_facts":removed}

@router.post("/projects/{project_id}/chapters/insert")
async def insert_chapter(project_id:str,p:ChapterInsert,db:AsyncSession=Depends(get_db)):
    """Chèn chương vào giữa mạch — dời trục narrative đồng bộ mọi bảng rồi tạo."""
    await project_or_404(db,project_id)
    from app.services.repair import shift_narrative
    max_o=(await db.scalar(select(func.max(Chapter.order_index))
                           .where(Chapter.project_id==project_id))) or 0
    if not 1<=p.order_index<=max_o+1: raise HTTPException(400,"order_index out of range")
    if p.arc_id:
        a=await db.get(Arc,p.arc_id)
        if not a or a.project_id!=project_id: raise HTTPException(400,"arc outside project")
    await shift_narrative(db,project_id,p.order_index,+1)
    obj=Chapter(project_id=project_id,title=p.title,order_index=p.order_index,
                volume_id=p.volume_id,arc_id=p.arc_id)
    db.add(obj); await db.commit(); await db.refresh(obj)
    return {"id":obj.id,"order_index":obj.order_index,"shifted":True}

@router.post("/projects/{project_id}/chapters/{chapter_id}/reextract")
async def reextract_chapter(project_id:str,chapter_id:str,db:AsyncSession=Depends(get_db)):
    """Sửa prose xong → trích lại dữ kiện chương: wipe facts cũ (có provenance,
    giữ facts tác giả/locked) rồi extract lại từ prose hiện tại."""
    from app.services.repair import wipe_chapter_extractions
    from app.services.authoring import extract_chapter_facts
    ch=await db.get(Chapter,chapter_id)
    if not ch or ch.project_id!=project_id: raise HTTPException(404,"chapter not found")
    removed=await wipe_chapter_extractions(db,project_id,ch)
    try:
        added=await extract_chapter_facts(db,project_id,ch,run=None)
    except ValueError as e:
        raise HTTPException(400,str(e))
    await db.commit(); return {"removed":removed,"added":added}

@router.post("/projects/{project_id}/chapters/{chapter_id}/scenes", response_model=SceneOut)
async def create_scene(project_id: str, chapter_id: str, payload: SceneCreate, db: AsyncSession=Depends(get_db)):
    await project_or_404(db, project_id)
    ch=await db.get(Chapter,chapter_id)
    if not ch or ch.project_id != project_id: raise HTTPException(404,"chapter not found in project")
    data=payload.model_dump()
    siblings=list((await db.scalars(select(Scene).where(
        Scene.chapter_id==chapter_id).order_by(Scene.order_index))).all())
    # chèn giữa: order_index đụng/nhỏ hơn max → đẩy sibling >= vị trí lên 1
    want=data.get("order_index") or 0
    if siblings and 0<want<=siblings[-1].order_index:
        for s in reversed([s for s in siblings if s.order_index>=want]):
            s.order_index+=1
        await db.flush()
    if data.get("story_time") is None:
        prev=[s for s in siblings if s.order_index<(want or 10**9)]
        if prev and prev[-1].story_time is not None:
            data["story_time"]=prev[-1].story_time
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
    old_prose=obj.prose or ""
    for k,v in data.items(): setattr(obj,k,v)
    if "prose" in data:
        if data["prose"] != old_prose:
            await _snapshot_version(db, obj, old_prose)
        await _stale_ancestor_summaries(db, project_id, scene_id)
    await db.commit(); await db.refresh(obj); return obj

def _vout(v: SceneVersion, full: bool = False):
    d = {"id": v.id, "scene_id": v.scene_id, "title": v.title,
         "created_at": v.created_at, "chars": len(v.prose or ""),
         "excerpt": (v.prose or "")[:160]}
    if full: d["prose"] = v.prose or ""
    return d

@router.get("/projects/{project_id}/scenes/{scene_id}/versions", response_model=list[SceneVersionOut])
async def list_scene_versions(project_id: str, scene_id: str, db: AsyncSession=Depends(get_db)):
    obj=await db.get(Scene,scene_id)
    if not obj or obj.project_id!=project_id: raise HTTPException(404,"scene not found in project")
    rows=(await db.scalars(select(SceneVersion).where(SceneVersion.scene_id==scene_id)
        .order_by(SceneVersion.created_at.desc()).limit(50))).all()
    return [_vout(v) for v in rows]

@router.get("/projects/{project_id}/scenes/{scene_id}/versions/{version_id}", response_model=SceneVersionFullOut)
async def get_scene_version(project_id: str, scene_id: str, version_id: str, db: AsyncSession=Depends(get_db)):
    v=await db.get(SceneVersion,version_id)
    if not v or v.project_id!=project_id or v.scene_id!=scene_id: raise HTTPException(404,"version not found")
    return _vout(v, full=True)

@router.post("/projects/{project_id}/scenes/{scene_id}/versions/{version_id}/restore", response_model=SceneOut)
async def restore_scene_version(project_id: str, scene_id: str, version_id: str, db: AsyncSession=Depends(get_db)):
    """Khôi phục prose từ version — force-snapshot trạng thái hiện tại trước
    (không mất dữ liệu), rồi đánh stale summaries như sửa prose thường."""
    obj=await db.get(Scene,scene_id)
    if not obj or obj.project_id!=project_id: raise HTTPException(404,"scene not found in project")
    v=await db.get(SceneVersion,version_id)
    if not v or v.scene_id!=scene_id: raise HTTPException(404,"version not found")
    await _snapshot_version(db, obj, obj.prose, force=True)
    obj.prose=v.prose or ""
    await _stale_ancestor_summaries(db, project_id, scene_id)
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
