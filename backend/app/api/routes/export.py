
import json,re,uuid
from datetime import datetime
from fastapi import APIRouter,Depends,HTTPException,UploadFile,File
from fastapi.responses import Response
from sqlalchemy import select,inspect,text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db, engine
from app.models import *
from app.models.truth import CanonFact,AuthorDecision,StoryEvent,StoryState,KnowledgeState,Secret
from app.models.narrative import Thread,ThreadBeat,ThreadDependency
from app.models.discussion import DiscussionThread,DiscussionMessage,StylePreference
from app.models.review import SuggestedChange
from app.models.memory import StorySummary,RetconProposal,AiTurn
from app.models.account import ModelPreference,StoryBranch,BranchChange
router=APIRouter()

# Toàn bộ bảng thuộc project — KHÔNG gồm provider_credentials (secret) và usage_logs.
TABLES=[
    ("volumes",Volume),("arcs",Arc),("chapters",Chapter),("scenes",Scene),
    ("scene_versions",SceneVersion),
    ("characters",Character),("aliases",Alias),("character_arcs",CharacterArc),
    ("world_entities",WorldEntity),("locations",Location),("factions",Faction),
    ("items",Item),("abilities",Ability),("relationships",Relationship),
    ("canon_facts",CanonFact),("author_decisions",AuthorDecision),
    ("story_events",StoryEvent),("story_states",StoryState),
    ("knowledge_states",KnowledgeState),("secrets",Secret),
    ("threads",Thread),("thread_beats",ThreadBeat),("thread_dependencies",ThreadDependency),
    ("discussion_threads",DiscussionThread),("discussion_messages",DiscussionMessage),
    ("style_profiles",StyleProfile),("style_samples",StyleSample),
    ("style_preferences",StylePreference),("suggested_changes",SuggestedChange),
    ("story_summaries",StorySummary),("retcon_proposals",RetconProposal),
    ("ai_turns",AiTurn),("story_branches",StoryBranch),("branch_changes",BranchChange),
    ("model_preferences",ModelPreference),
]

def _dump(obj):
    return {c.key:getattr(obj,c.key) for c in inspect(obj).mapper.column_attrs}

def _slug(name):
    s=(name or "project").lower()
    s=re.sub(r"[àáảãạăắằẳẵặâấầẩẫậ]","a",s); s=re.sub(r"[èéẻẽẹêếềểễệ]","e",s)
    s=re.sub(r"[ìíỉĩị]","i",s); s=re.sub(r"[òóỏõọôốồổỗộơớờởỡợ]","o",s)
    s=re.sub(r"[ùúủũụưứừửữự]","u",s); s=re.sub(r"[ỳýỷỹỵ]","y",s)
    s=s.replace("đ","d")
    s=re.sub(r"[^a-z0-9]+","-",s).strip("-")
    return s or "project"

@router.get("/projects/{pid}/export")
async def export_project(pid:str,format:str="json",db:AsyncSession=Depends(get_db)):
    """Sao lưu toàn bộ project → file .json (đầy đủ) hoặc .md (chỉ bản thảo)."""
    proj=await db.get(Project,pid)
    if not proj: raise HTTPException(404,"project not found")
    stamp=datetime.utcnow().strftime("%Y%m%d-%H%M")
    slug=_slug(proj.name)
    if format=="markdown":
        return Response(content=await _markdown(db,proj),media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition":f'attachment; filename="{slug}-{stamp}.md"'})
    data={"format":"ai-writer-studio-export","version":1,
          "exported_at":datetime.utcnow().isoformat()+"Z",
          "project":_dump(proj)}
    counts={}
    for name,model in TABLES:
        rows=(await db.scalars(select(model).where(model.project_id==pid))).all()
        data[name]=[_dump(r) for r in rows]; counts[name]=len(rows)
    data["counts"]=counts
    return Response(content=json.dumps(data,ensure_ascii=False,default=str,indent=1),
        media_type="application/json",
        headers={"Content-Disposition":f'attachment; filename="{slug}-{stamp}.json"'})

async def _markdown(db,proj):
    """Bản thảo sạch: Quyển → Hồi → Chương → Cảnh, chỉ prose."""
    lines=[f"# {proj.name}",""]
    chapters=list((await db.scalars(select(Chapter).where(
        Chapter.project_id==proj.id).order_by(Chapter.order_index))).all())
    ch_ids=[c.id for c in chapters]
    scenes=list((await db.scalars(select(Scene).where(
        Scene.project_id==proj.id).order_by(Scene.order_index))).all()) if ch_ids else []
    by_ch={}
    for s in scenes: by_ch.setdefault(s.chapter_id,[]).append(s)
    vols={v.id:v for v in (await db.scalars(select(Volume).where(Volume.project_id==proj.id))).all()}
    arcs={a.id:a for a in (await db.scalars(select(Arc).where(Arc.project_id==proj.id))).all()}
    last_vol=last_arc=None
    for c in chapters:
        if c.volume_id!=last_vol:
            last_vol=c.volume_id; last_arc=None
            if c.volume_id and c.volume_id in vols:
                lines += [f"\n## {vols[c.volume_id].title}\n"]
        if c.arc_id!=last_arc:
            last_arc=c.arc_id
            if c.arc_id and c.arc_id in arcs:
                lines += [f"\n### {arcs[c.arc_id].title}\n"]
        # Title đã chứa "Chương N." sẵn thì dùng nguyên, tránh "Chương 1. Chương 1. …"
        title=(c.title or "").strip()
        head=title if re.match(r"(?i)^(chương|chapter|hồi|quyển|phần)\s*\d",title) else f"Chương {c.order_index}. {title}".rstrip(". ")
        lines += [f"\n## {head}\n"]
        for s in by_ch.get(c.id,[]):
            if s.title: lines.append(f"\n#### {s.title}\n")
            prose=(s.prose or "").strip()
            if prose: lines += [prose,""]
    return "\n".join(lines)

@router.post("/projects/import")
async def import_project(file: UploadFile = File(...), db: AsyncSession=Depends(get_db)):
    """Nhập file export .json → project MỚI. Remap toàn bộ id để import lặp
    được và FK tự trỏ sang id mới (mọi cột ref đều đuôi _id hoặc giá trị uuid)."""
    try:
        data=json.loads(await file.read())
    except Exception:
        raise HTTPException(400,"file không phải JSON hợp lệ")
    if data.get("format")!="ai-writer-studio-export":
        raise HTTPException(400,"không phải file export của app (thiếu format)")
    psrc=data.get("project") or {}
    if not psrc.get("name"): raise HTTPException(400,"export thiếu project.name")

    proj=Project(name=psrc["name"],description=psrc.get("description"))
    db.add(proj); await db.flush()
    new_pid=proj.id

    # Pass 1: mọi id cũ → uuid mới (uuid duy nhất toàn cục nên map chung an toàn)
    id_map={}
    for name,_ in TABLES:
        for row in data.get(name) or []:
            if isinstance(row.get("id"),str): id_map[row["id"]]=str(uuid.uuid4())

    # Pass 2: insert; defer FK check tới commit để khỏi sắp thứ tự/self-FK
    if engine.url.get_backend_name().startswith("sqlite"):
        await db.execute(text("PRAGMA defer_foreign_keys=ON"))
    counts={}
    for name,model in TABLES:
        rows=data.get(name) or []
        cols={c.name:c for c in model.__table__.columns}
        n=0
        for row in rows:
            if not isinstance(row,dict): continue
            kw={}
            for k,v in row.items():
                col=cols.get(k)
                if col is None: continue
                if k=="id" and v in id_map: v=id_map[v]
                elif k=="project_id": v=new_pid
                elif isinstance(v,str) and v in id_map: v=id_map[v]
                if isinstance(v,str) and col.type.__class__.__name__=="DateTime":
                    try: v=datetime.fromisoformat(v.replace("Z","+00:00")).replace(tzinfo=None)
                    except ValueError: pass
                kw[k]=v
            if "project_id" in cols: kw["project_id"]=new_pid
            if kw.get("id") is None and "id" in cols: kw["id"]=str(uuid.uuid4())
            db.add(model(**kw)); n+=1
        counts[name]=n
    await db.commit()
    return {"project":{"id":new_pid,"name":proj.name},"counts":counts}
