
import re
import unicodedata
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models import Project, Chapter, Scene, Character, Alias, Location
from app.models.truth import CanonFact, StoryEvent
from app.models.narrative import Thread

router = APIRouter()

PER_TYPE = 20


def _qrx(q: str):
    """Regex ranh TỪ theo Unicode — \\w của Python gồm chữ có dấu, nên 'hôn'
    không còn ăn 'khôn/hồn/chôn' (C5). NFC hoá query để text NFD vẫn bắt.
    Ranh chỉ đặt ở phía query là ký tự word — query toàn ký hiệu ('%',
    '100%') vẫn match literal."""
    nq = unicodedata.normalize("NFC", q)
    pat = re.escape(nq)
    if nq and re.match(r"\w", nq[0]):
        pat = r"(?<!\w)" + pat
    if nq and re.match(r"\w", nq[-1]):
        pat = pat + r"(?!\w)"
    return re.compile(pat, re.IGNORECASE)


def _hit(rx, *texts) -> bool:
    return any(rx.search(unicodedata.normalize("NFC", t or "")) for t in texts)


def _snippet(text: str | None, rx, span: int = 90) -> str:
    """Trích đoạn ±span ký tự quanh match ranh-từ đầu tiên."""
    if not text: return ""
    m = rx.search(unicodedata.normalize("NFC", text))
    if not m: return text[: span * 2].strip()
    a, b = max(0, m.start() - span), min(len(text), m.end() + span)
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
    rx = _qrx(q)
    out = []

    # LIKE lấy ứng viên rộng (limit×3) → lọc ranh-từ ở Python — LIKE substring
    # không hiểu ranh từ tiếng Việt; boundary match ⇒ substring match nên
    # không bỏ sót ứng viên (chỉ rớt false-positive như 'khôn' chứa 'hôn')
    scenes = (await db.scalars(select(Scene).where(Scene.project_id == pid).where(
        or_(_like(Scene.title, q), _like(Scene.prose, q), _like(Scene.skeleton, q))
    ).limit(PER_TYPE * 3))).all()
    ch_titles = {c.id: c.title for c in (await db.scalars(
        select(Chapter).where(Chapter.project_id == pid))).all()}
    n = 0
    for s in scenes:
        if not _hit(rx, s.title, s.prose, s.skeleton):
            continue
        if n >= PER_TYPE: break
        n += 1
        text = s.prose if _hit(rx, s.prose) else (s.title or "") + "\n" + (s.skeleton or "")
        out.append({"type": "scene", "id": s.id,
                    "label": s.title or f"Cảnh {s.order_index}",
                    "context": ch_titles.get(s.chapter_id, ""),
                    "snippet": _snippet(text, rx)})

    chapters = (await db.scalars(select(Chapter).where(Chapter.project_id == pid).where(
        _like(Chapter.title, q)).limit(PER_TYPE * 3))).all()
    n = 0
    for c in chapters:
        if not _hit(rx, c.title):
            continue
        if n >= PER_TYPE: break
        n += 1
        first_scene = (await db.scalars(select(Scene.id).where(
            Scene.chapter_id == c.id).order_by(Scene.order_index).limit(1))).first()
        out.append({"type": "chapter", "id": c.id, "label": c.title or f"Chương {c.order_index}",
                    "context": "", "snippet": "", "scene_id": first_scene})

    chars = (await db.scalars(select(Character).where(Character.project_id == pid).where(
        or_(_like(Character.name, q), _like(Character.summary, q), _like(Character.role, q))
    ).limit(PER_TYPE * 3))).all()
    n = 0
    for c in chars:
        if not _hit(rx, c.name, c.summary, c.role):
            continue
        if n >= PER_TYPE: break
        n += 1
        text = c.summary if _hit(rx, c.summary) else f"{c.name} · {c.role or ''}"
        out.append({"type": "character", "id": c.id, "label": c.name,
                    "context": c.role or "", "snippet": _snippet(text, rx)})

    aliases = (await db.scalars(select(Alias).where(Alias.project_id == pid).where(
        _like(Alias.alias, q)).limit(PER_TYPE * 3))).all()
    owner = {c.id: c.name for c in (await db.scalars(
        select(Character).where(Character.project_id == pid))).all()}
    for a in aliases:
        if _hit(rx, a.alias) and not any(
            r["type"] == "character" and r["id"] == a.character_id for r in out):
            out.append({"type": "character", "id": a.character_id,
                        "label": owner.get(a.character_id, "?"),
                        "context": f"bí danh: {a.alias}", "snippet": ""})

    facts = (await db.scalars(select(CanonFact).where(CanonFact.project_id == pid).where(
        or_(_like(CanonFact.predicate, q), _like(CanonFact.value_text, q))
    ).limit(PER_TYPE * 3))).all()
    n = 0
    for f in facts:
        if not _hit(rx, f.predicate, f.value_text):
            continue
        if n >= PER_TYPE: break
        n += 1
        out.append({"type": "canon", "id": f.id,
                    "label": f"{f.subject_type} · {f.predicate}",
                    "context": f.truth_status, "snippet": _snippet(f.value_text, rx)})

    threads = (await db.scalars(select(Thread).where(Thread.project_id == pid).where(
        or_(_like(Thread.title, q), _like(Thread.description, q))).limit(PER_TYPE * 3))).all()
    n = 0
    for th in threads:
        if not _hit(rx, th.title, th.description):
            continue
        if n >= PER_TYPE: break
        n += 1
        out.append({"type": "thread", "id": th.id, "label": th.title,
                    "context": th.status, "snippet": _snippet(th.description or "", rx)})

    events = (await db.scalars(select(StoryEvent).where(StoryEvent.project_id == pid).where(
        _like(StoryEvent.summary, q)).limit(PER_TYPE * 3))).all()
    n = 0
    for e in events:
        if not _hit(rx, e.summary):
            continue
        if n >= PER_TYPE: break
        n += 1
        out.append({"type": "event", "id": e.id, "label": e.event_type,
                    "context": f"t={e.story_time}" if e.story_time is not None else "",
                    "snippet": _snippet(e.summary, rx)})

    locs = (await db.scalars(select(Location).where(Location.project_id == pid).where(
        or_(_like(Location.name, q), _like(Location.description, q))).limit(PER_TYPE * 3))).all()
    n = 0
    for l in locs:
        if not _hit(rx, l.name, l.description):
            continue
        if n >= PER_TYPE: break
        n += 1
        out.append({"type": "location", "id": l.id, "label": l.name,
                    "context": "", "snippet": _snippet(l.description or "", rx)})

    return {"q": q, "total": len(out), "results": out}
