"""Constraint Manifest — deterministic rules injected before generation.

Turns DB truth into explicit must_respect / may_use / must_not_invent lines
so the model is told (not asked) what it cannot contradict.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Scene, Chapter
from app.models.story import Character
from app.models.narrative import Thread
from app.models.truth import KnowledgeState, CanonFact
from app.services.state import states_at

# lifecycle values that restrict physical presence
_RESTRICTED = {
    "DEAD": "đã chết — chỉ được xuất hiện trong flashback/mơ/ảo giác/hồi ức",
    "MISSING": "đang mất tích — không xuất hiện trừ khi có sự kiện tìm thấy",
    "IMPRISONED": "đang bị giam — không tự do xuất hiện trừ khi được thả/trốn",
    "COMA": "đang hôn mê — không hành động hay hội thoại",
    "EXITED": "đã rời khỏi mạch truyện — không tái xuất trừ khi có sự kiện quay lại",
}


def _time_of(scene: Scene | None, chapter: Chapter | None) -> int | None:
    if scene and scene.story_time is not None:
        return scene.story_time
    if scene and scene.narrative_order is not None:
        return scene.narrative_order
    return None


async def build_constraints(
    db: AsyncSession, pid: str, scene: Scene | None
) -> dict[str, list[str]]:
    """Return {must_respect, may_use, must_not_invent} for writing `scene`."""
    t = _time_of(scene, None)
    must: list[str] = []
    may: list[str] = []
    never: list[str] = []

    names = {c.id: c.name for c in (await db.scalars(
        select(Character).where(Character.project_id == pid))).all()}

    # --- character lifecycle / location / ability / ownership states
    for s in await states_at(db, pid, story_time=t):
        who = names.get(s.entity_id, s.entity_id)
        if s.key == "lifecycle":
            v = (s.value_text or "").strip().upper()
            if v in _RESTRICTED:
                must.append(f"{who} {_RESTRICTED[v]}")
                never.append(f"hồi sinh/tái xuất {who} nếu không có sự kiện được duyệt")
            elif v == "ALIVE":
                pass  # default
        elif s.key == "location":
            must.append(f"{who} đang ở {s.value_text} — cần sự kiện di chuyển để ở nơi khác")
        elif s.key == "ownership":
            must.append(f"{s.value_text} (ownership đã ghi — không đổi chủ tự do)")
        elif s.key.startswith("ability."):
            ability = s.key.split(".", 1)[1]
            # value_text may encode "UNLOCKED"/"LOCKED"
            if (s.value_text or "").upper().startswith("LOCKED"):
                never.append(f"{who} dùng {ability} — chưa mở khoá tại thời điểm này")

    # --- POV knowledge boundary (things the POV cannot know yet)
    if scene and scene.pov_character_id:
        leaks = list((await db.scalars(
            select(KnowledgeState).where(
                KnowledgeState.project_id == pid,
                KnowledgeState.knower_id == scene.pov_character_id,
                KnowledgeState.state.in_(["UNAWARE", "FALSE_BELIEF", "SUSPECTS"]),
            ))).all())
        if leaks:
            fact_ids = [k.fact_id for k in leaks]
            facts = {f.id: f for f in (await db.scalars(
                select(CanonFact).where(CanonFact.id.in_(fact_ids)))).all()}
            for k in leaks:
                f = facts.get(k.fact_id)
                if not f:
                    continue
                if k.state == "UNAWARE":
                    never.append(f"POV biết về '{f.predicate}' — nhân vật chưa hề biết")
                elif k.state == "FALSE_BELIEF":
                    must.append(f"POV tin sai: {f.predicate} — {k.known_aspects or f.value_text[:120]}")
                else:
                    must.append(f"POV chỉ NGHI '{f.predicate}' — không được viết như đã biết chắc")

    # --- open threads relevant now
    open_threads = list((await db.scalars(
        select(Thread).where(Thread.project_id == pid, Thread.status == "OPEN"))).all())
    for th in open_threads[:8]:
        may.append(f"Hố '{th.title}' đang mở — có thể reinforce nếu hợp mạch")

    # locked canon = absolute
    locked = list((await db.scalars(
        select(CanonFact).where(CanonFact.project_id == pid, CanonFact.locked == True))).all())  # noqa: E712
    for f in locked[:10]:
        never.append(f"mâu thuẫn canon khoá: {f.predicate} = {f.value_text[:120]}")

    return {"must_respect": must, "may_use": may, "must_not_invent": never}


def render_constraints(m: dict[str, list[str]]) -> str:
    """Human-readable block for prompts — empty string when nothing binds."""
    if not any(m.values()):
        return ""
    out = []
    if m["must_respect"]:
        out.append("PHẢI TUÂN THỦ:\n" + "\n".join(f"- {x}" for x in m["must_respect"]))
    if m["must_not_invent"]:
        out.append("KHÔNG ĐƯỢC TẠO:\n" + "\n".join(f"- {x}" for x in m["must_not_invent"]))
    if m["may_use"]:
        out.append("CÓ THỂ DÙNG:\n" + "\n".join(f"- {x}" for x in m["may_use"]))
    return "=== RÀNG BUỘC TRUYỆN (đã xác minh từ DB, không được phá) ===\n" + "\n\n".join(out)
