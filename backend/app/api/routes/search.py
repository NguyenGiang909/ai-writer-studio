
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models import Project, Chapter, Scene, Character, Alias, Location
from app.models.truth import CanonFact, StoryEvent
from app.models.narrative import Thread

router = APIRouter()

PER_TYPE = 20

def _snippet(text: str | None, q: str, span: int = 90) -> str:
    """Trích đoạn ±span ký tự quanh match đầu tiên (casefold)."""
    if not text: return ""
    t = text.casefold(); i = t.find(q.casefold())
    if i < 0: return text[: span * 2].strip()
    a, b = max(0, i - span), min(len(text), i + len(q) + span)
    return ("…" if a else "") + text[a:b].strip() + ("…" if b < len(text) else "")

def _like(col, q):
    # Escape ký tự đặc biệt của LIKE — tìm "%" hay "_" phải ra literal, không phải wildcard
    e = q.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return func.lower(col).like(f"%{e}%", escape="\\")

@router.get("/projects/{pid}/search")
async def search_project(pid: str, q: str = Query(min_length=1, max_length=200),
                         db: AsyncSession = Depends(get_db)):
    """Tìm toàn cục trong project: cảnh/chương (title+prose), nhân vật, bí danh,
    canon fact, thread, sự kiện, địa điểm. Trả label + snippet quanh match."""
    if not await db.get(Project, pid): raise HTTPException(404, "project not found")
    q = q.strip()
    if not q: return {"q": q, "total": 0, "results": []}
    out = []

    scenes = (await db.scalars(select(Scene).where(Scene.project_id == pid).where(
        or_(_like(Scene.title, q), _like(Scene.prose, q), _like(Scene.skeleton, q))
    ).limit(PER_TYPE))).all()
    ch_titles = {c.id: c.title for c in (await db.scalars(
        select(Chapter).where(Chapter.project_id == pid))).all()}
    for s in scenes:
        text = s.prose if q.casefold() in (s.prose or "").casefold() else (s.title or "") + "\n" + (s.skeleton or "")
        out.append({"type": "scene", "id": s.id,
                    "label": s.title or f"Cảnh {s.order_index}",
                    "context": ch_titles.get(s.chapter_id, ""),
                    "snippet": _snippet(text, q)})

    chapters = (await db.scalars(select(Chapter).where(Chapter.project_id == pid).where(
        _like(Chapter.title, q)).limit(PER_TYPE))).all()
    for c in chapters:
        first_scene = (await db.scalars(select(Scene.id).where(
            Scene.chapter_id == c.id).order_by(Scene.order_index).limit(1))).first()
        out.append({"type": "chapter", "id": c.id, "label": c.title or f"Chương {c.order_index}",
                    "context": "", "snippet": "", "scene_id": first_scene})

    chars = (await db.scalars(select(Character).where(Character.project_id == pid).where(
        or_(_like(Character.name, q), _like(Character.summary, q), _like(Character.role, q))
    ).limit(PER_TYPE))).all()
    for c in chars:
        text = c.summary if q.casefold() in (c.summary or "").casefold() else f"{c.name} · {c.role or ''}"
        out.append({"type": "character", "id": c.id, "label": c.name,
                    "context": c.role or "", "snippet": _snippet(text, q)})

    aliases = (await db.scalars(select(Alias).where(Alias.project_id == pid).where(
        _like(Alias.alias, q)).limit(PER_TYPE))).all()
    owner = {c.id: c.name for c in (await db.scalars(
        select(Character).where(Character.project_id == pid))).all()}
    for a in aliases:
        if q.casefold() in (a.alias or "").casefold() and not any(
            r["type"] == "character" and r["id"] == a.character_id for r in out):
            out.append({"type": "character", "id": a.character_id,
                        "label": owner.get(a.character_id, "?"),
                        "context": f"bí danh: {a.alias}", "snippet": ""})

    facts = (await db.scalars(select(CanonFact).where(CanonFact.project_id == pid).where(
        or_(_like(CanonFact.predicate, q), _like(CanonFact.value_text, q))
    ).limit(PER_TYPE))).all()
    for f in facts:
        out.append({"type": "canon", "id": f.id,
                    "label": f"{f.subject_type} · {f.predicate}",
                    "context": f.truth_status, "snippet": _snippet(f.value_text, q)})

    threads = (await db.scalars(select(Thread).where(Thread.project_id == pid).where(
        or_(_like(Thread.title, q), _like(Thread.description, q))).limit(PER_TYPE))).all()
    for th in threads:
        out.append({"type": "thread", "id": th.id, "label": th.title,
                    "context": th.status, "snippet": _snippet(th.description or "", q)})

    events = (await db.scalars(select(StoryEvent).where(StoryEvent.project_id == pid).where(
        _like(StoryEvent.summary, q)).limit(PER_TYPE))).all()
    for e in events:
        out.append({"type": "event", "id": e.id, "label": e.event_type,
                    "context": f"t={e.story_time}" if e.story_time is not None else "",
                    "snippet": _snippet(e.summary, q)})

    locs = (await db.scalars(select(Location).where(Location.project_id == pid).where(
        or_(_like(Location.name, q), _like(Location.description, q))).limit(PER_TYPE))).all()
    for l in locs:
        out.append({"type": "location", "id": l.id, "label": l.name,
                    "context": "", "snippet": _snippet(l.description or "", q)})

    return {"q": q, "total": len(out), "results": out}
