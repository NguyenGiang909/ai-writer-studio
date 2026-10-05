
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models import *
from app.schemas.story import *
router=APIRouter()

async def project_ok(db,pid):
    if not await db.get(Project,pid): raise HTTPException(404,"project not found")
async def scoped(db,cls,obj_id,pid,label):
    obj=await db.get(cls,obj_id)
    if not obj or obj.project_id!=pid: raise HTTPException(400,f"{label} outside project")
    return obj
async def add(db,obj):
    db.add(obj); await db.commit(); await db.refresh(obj); return obj

async def _patch_obj(db,cls,oid,pid,label,data):
    """Generic PATCH: chỉ áp các field trùng tên cột thật của model."""
    obj=await scoped(db,cls,oid,pid,label)
    for k,v in data.items():
        if k in obj.__table__.columns: setattr(obj,k,v)
    await db.commit(); await db.refresh(obj); return obj

async def _del_obj(db,cls,oid,pid,label):
    obj=await scoped(db,cls,oid,pid,label)
    await db.delete(obj); await db.commit(); return {"deleted":True}

# --- importance buckets: 0 Quan trọng · 1 Khá quan trọng · 2 Trung bình · 3 Thùng rác
import re as _re, unicodedata as _ud
def _role_default_importance(role):
    s=_ud.normalize("NFD",role or "")
    s="".join(c for c in s if not _ud.combining(c)).replace("đ","d").lower()
    if not s.strip(): return 2
    if _re.search(r"thoang qua|minor|nho\b|mot lan|1 lan|xuat hien",s): return 3
    if _re.search(r"protagonist|nhan vat chinh|\bpov\b|trung tam",s): return 0
    if _re.search(r"deuteragonist|phu chinh|antagonist|phan dien|doi dau|doi thu|chinh dien|thu linh|chu su",s): return 1
    return 2

def _eff_importance(row):
    if row.importance is not None: return row.importance
    return _role_default_importance(getattr(row,"role",None))

async def _move(db,cls,pid,obj_id,direction):
    rows=list((await db.scalars(select(cls).where(cls.project_id==pid))).all())
    for r in rows:
        if r.importance is None: r.importance=_eff_importance(r)
    def k(r):
        nm=(getattr(r,"name",None) or getattr(r,"relationship_type",None) or r.id)
        return (r.importance, r.sort_order, str(nm).lower(), r.id)
    rows.sort(key=k)
    ids={r.id:i for i,r in enumerate(rows)}
    i=ids.get(obj_id)
    if i is None: raise HTTPException(404,"not found")
    j=i-1 if direction=="up" else i+1
    if j<0 or j>=len(rows):
        return {"moved":False}
    a,b=rows[i],rows[j]
    if a.importance!=b.importance: a.importance=b.importance  # đẩy qua ranh giới = đổi nhóm
    rows[i],rows[j]=rows[j],rows[i]
    for n,r in enumerate(rows): r.sort_order=n
    await db.commit()
    return {"moved":True}

@router.post("/projects/{pid}/characters")
async def create_character(pid:str,p:CharacterCreate,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid); return await add(db,Character(project_id=pid,**p.model_dump()))

@router.get("/projects/{pid}/characters")
async def list_characters(pid:str,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    return list((await db.scalars(select(Character).where(Character.project_id==pid).order_by(Character.name))).all())

@router.patch("/projects/{pid}/characters/{cid}")
async def patch_character(pid:str,cid:str,p:CharacterPatch,db:AsyncSession=Depends(get_db)):
    obj=await scoped(db,Character,cid,pid,"character")
    for k,v in p.model_dump(exclude_unset=True).items(): setattr(obj,k,v)
    await db.commit(); await db.refresh(obj); return obj

@router.post("/projects/{pid}/characters/{cid}/move")
async def move_character(pid:str,cid:str,p:MoveRequest,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    return await _move(db,Character,pid,cid,p.direction)

async def _reorder(db,cls,pid,ids):
    """Kéo-thả: gán sort_order theo thứ tự id client gửi lên."""
    rows=list((await db.scalars(select(cls).where(cls.project_id==pid))).all())
    pos={i:n for n,i in enumerate(ids)}
    for r in rows:
        if r.id in pos: r.sort_order=pos[r.id]
    await db.commit()
    return {"reordered":len(pos)}

@router.post("/projects/{pid}/characters/reorder")
async def reorder_characters(pid:str,p:ReorderRequest,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    return await _reorder(db,Character,pid,p.ids)

@router.delete("/projects/{pid}/characters/{cid}")
async def delete_character(pid:str,cid:str,db:AsyncSession=Depends(get_db)):
    await scoped(db,Character,cid,pid,"character")
    await db.execute(update(Scene).where(Scene.project_id==pid,Scene.pov_character_id==cid).values(pov_character_id=None))
    return await _del_obj(db,Character,cid,pid,"character")

@router.post("/projects/{pid}/world-entities")
async def create_world(pid:str,p:WorldEntityCreate,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid); return await add(db,WorldEntity(project_id=pid,**p.model_dump()))

@router.post("/projects/{pid}/locations")
async def create_location(pid:str,p:LocationCreate,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    if p.parent_location_id: await scoped(db,Location,p.parent_location_id,pid,"parent location")
    return await add(db,Location(project_id=pid,**p.model_dump()))

@router.post("/projects/{pid}/factions")
async def create_faction(pid:str,p:NamedCreate,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid); return await add(db,Faction(project_id=pid,**p.model_dump()))

@router.post("/projects/{pid}/items")
async def create_item(pid:str,p:ItemCreate,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid); return await add(db,Item(project_id=pid,**p.model_dump()))

@router.post("/projects/{pid}/abilities")
async def create_ability(pid:str,p:AbilityCreate,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid); return await add(db,Ability(project_id=pid,**p.model_dump()))

@router.post("/projects/{pid}/relationships")
async def create_relationship(pid:str,p:RelationshipCreate,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    await scoped(db,Character,p.source_character_id,pid,"source character")
    await scoped(db,Character,p.target_character_id,pid,"target character")
    if p.source_character_id==p.target_character_id: raise HTTPException(400,"relationship endpoints must differ")
    return await add(db,Relationship(project_id=pid,**p.model_dump()))

@router.patch("/projects/{pid}/relationships/{rid}")
async def patch_relationship(pid:str,rid:str,p:RelationshipPatch,db:AsyncSession=Depends(get_db)):
    obj=await scoped(db,Relationship,rid,pid,"relationship")
    for k,v in p.model_dump(exclude_unset=True).items(): setattr(obj,k,v)
    await db.commit(); await db.refresh(obj); return obj

@router.post("/projects/{pid}/relationships/{rid}/move")
async def move_relationship(pid:str,rid:str,p:MoveRequest,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    return await _move(db,Relationship,pid,rid,p.direction)

@router.post("/projects/{pid}/relationships/reorder")
async def reorder_relationships(pid:str,p:ReorderRequest,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    return await _reorder(db,Relationship,pid,p.ids)

@router.post("/projects/{pid}/aliases")
async def create_alias(pid:str,p:AliasCreate,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid); await scoped(db,Character,p.character_id,pid,"character")
    return await add(db,Alias(project_id=pid,**p.model_dump()))

@router.post("/projects/{pid}/character-arcs")
async def create_character_arc(pid:str,p:CharacterArcCreate,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid); await scoped(db,Character,p.character_id,pid,"character")
    return await add(db,CharacterArc(project_id=pid,**p.model_dump()))

@router.post("/projects/{pid}/style-profiles")
async def create_style_profile(pid:str,p:StyleProfileCreate,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    allowed={"global","arc","character","scene_type"}
    if p.scope_type not in allowed: raise HTTPException(400,"invalid style scope")
    if p.scope_type=="global" and p.scope_id is not None: raise HTTPException(400,"global scope_id must be null")
    if p.scope_type=="arc" and p.scope_id: await scoped(db,Arc,p.scope_id,pid,"arc")
    if p.scope_type=="character" and p.scope_id: await scoped(db,Character,p.scope_id,pid,"character")
    return await add(db,StyleProfile(project_id=pid,**p.model_dump()))

@router.post("/projects/{pid}/style-samples")
async def create_style_sample(pid:str,p:StyleSampleCreate,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid); await scoped(db,StyleProfile,p.style_profile_id,pid,"style profile")
    return await add(db,StyleSample(project_id=pid,**p.model_dump()))

async def _list(db,cls,pid,order_col="name"):
    col=getattr(cls,order_col,None) or cls.id
    return list((await db.scalars(select(cls).where(cls.project_id==pid).order_by(col))).all())

@router.get("/projects/{pid}/world-entities")
async def list_world_entities(pid:str,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid); return await _list(db,WorldEntity,pid)
@router.get("/projects/{pid}/locations")
async def list_locations(pid:str,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid); return await _list(db,Location,pid)
@router.get("/projects/{pid}/factions")
async def list_factions(pid:str,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid); return await _list(db,Faction,pid)
@router.get("/projects/{pid}/items")
async def list_items(pid:str,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid); return await _list(db,Item,pid)
@router.get("/projects/{pid}/abilities")
async def list_abilities(pid:str,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid); return await _list(db,Ability,pid)
@router.get("/projects/{pid}/relationships")
async def list_relationships(pid:str,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid); return await _list(db,Relationship,pid,"id")
@router.get("/projects/{pid}/aliases")
async def list_aliases(pid:str,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid); return await _list(db,Alias,pid,"alias")
@router.get("/projects/{pid}/character-arcs")
async def list_character_arcs(pid:str,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid); return await _list(db,CharacterArc,pid,"title")
@router.get("/projects/{pid}/style-profiles")
async def list_style_profiles(pid:str,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid); return await _list(db,StyleProfile,pid)
@router.get("/projects/{pid}/style-samples")
async def list_style_samples(pid:str,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid); return await _list(db,StyleSample,pid,"id")

# ---- Generic PATCH/DELETE cho mọi story entity (dict body → chỉ ghi cột tồn tại) ----
from fastapi import Body

def _patch_del(cls,label,path):
    op=path.replace("-","_")
    @router.patch(f"/projects/{{pid}}/{path}/{{oid}}",operation_id=f"patch_{op}")
    async def _patch(pid:str,oid:str,data:dict=Body(...),db:AsyncSession=Depends(get_db)):
        return await _patch_obj(db,cls,oid,pid,label,data)
    @router.delete(f"/projects/{{pid}}/{path}/{{oid}}",operation_id=f"delete_{op}")
    async def _del(pid:str,oid:str,db:AsyncSession=Depends(get_db)):
        return await _del_obj(db,cls,oid,pid,label)

_patch_del(WorldEntity,"world entity","world-entities")
_patch_del(Location,"location","locations")
_patch_del(Faction,"faction","factions")
_patch_del(Item,"item","items")
_patch_del(Ability,"ability","abilities")
_patch_del(Relationship,"relationship","relationships")
_patch_del(Alias,"alias","aliases")
_patch_del(CharacterArc,"character arc","character-arcs")
_patch_del(StyleProfile,"style profile","style-profiles")
_patch_del(StyleSample,"style sample","style-samples")
