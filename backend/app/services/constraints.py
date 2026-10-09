"""Constraint Manifest — deterministic rules injected before generation.

Turns DB truth into explicit must_respect / may_use / must_not_invent lines
so the model is told (not asked) what it cannot contradict.
"""

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Scene, Chapter
from app.models.story import Character
from app.models.narrative import Thread
from app.models.truth import KnowledgeState, CanonFact
from app.services.state import states_at

# extractor hay ghi key tự do tiếng Việt — gom về key canonical mà
# build_constraints hiểu, để PHẢI TUÂN THỦ thực sự phát
CANONICAL_STATE_KEYS = {
    "location": {"location", "nơi ở", "địa điểm", "vị trí", "hiện diện",
                 "nơi ở hiện tại", "vị trí hiện tại"},
    "lifecycle": {"lifecycle", "sinh tử", "sống/chết", "hiện trạng sống",
                  "trạng thái sống"},
    "ownership": {"ownership", "sở hữu", "thuộc về", "chủ sở hữu"},
    "status": {"status", "tình trạng", "tâm trạng"},
    # tuổi + bậc học — lỗi thật đã gặp: model dàn "tập đọc" (tiểu học)
    # cho nhân vật cấp 2 vì không có tuổi/lớp trong prompt
    "age": {"age", "tuổi", "độ tuổi", "tuổi hiện tại", "lứa tuổi",
            "năm sinh", "tuổi/nghề"},
    "education": {"education", "lớp", "lớp học", "lớp_học", "khối",
                  "học lớp", "trường học", "trường_học", "trường",
                  "năm học", "cấp học", "năm nay lên lớp"},
}


def canonical_state_key(key: str | None) -> str:
    k = (key or "").strip().lower()
    for canon, aliases in CANONICAL_STATE_KEYS.items():
        if k == canon or k in aliases:
            return canon
    return (key or "state").strip()


# lifecycle values that restrict physical presence
_RESTRICTED = {
    "DEAD": "đã chết — chỉ được xuất hiện trong flashback/mơ/ảo giác/hồi ức",
    "MISSING": "đang mất tích — không xuất hiện trừ khi có sự kiện tìm thấy",
    "IMPRISONED": "đang bị giam — không tự do xuất hiện trừ khi được thả/trốn",
    "COMA": "đang hôn mê — không hành động hay hội thoại",
    "EXITED": "đã rời khỏi mạch truyện — không tái xuất trừ khi có sự kiện quay lại",
}


async def build_constraints(
    db: AsyncSession, pid: str, scene: Scene | None
) -> dict[str, list[str]]:
    """Return {must_respect, may_use, must_not_invent} for writing `scene`."""
    # hai axis thời gian độc lập: story_time (đồng hồ trong truyện) và
    # narrative_order (= chapter.order_index) — không trộn scale
    t = scene.story_time if (scene and scene.story_time is not None) else None
    # narrative position cho filter — scene.narrative_order (convention codebase:
    # = chapter.order_index), fallback chapter.order_index cho scene cũ chưa gán
    t_narr = None
    if scene:
        t_narr = scene.narrative_order
        if t_narr is None and scene.chapter_id:
            ch = await db.get(Chapter, scene.chapter_id)
            if ch and ch.order_index is not None:
                t_narr = ch.order_index
    must: list[str] = []
    may: list[str] = []
    never: list[str] = []

    names = {c.id: c.name for c in (await db.scalars(
        select(Character).where(Character.project_id == pid))).all()}

    # --- character lifecycle / location / ability / ownership states
    # group lại theo canonical key — states_at group theo raw key nên state cũ
    # "nơi ở" + "location" mới của cùng entity sẽ lọt cả hai → mâu thuẫn hiển thị
    dedup: dict[tuple, object] = {}
    for s in await states_at(db, pid, story_time=t, narrative_order=t_narr):
        k = (s.entity_type, s.entity_id, canonical_state_key(s.key))
        cur = dedup.get(k)
        if cur is None or ((s.narrative_order or -1), (s.story_time or -1)) \
                >= ((cur.narrative_order or -1), (cur.story_time or -1)):
            dedup[k] = s
    for s in dedup.values():
        who = names.get(s.entity_id)
        key = canonical_state_key(s.key)
        if key == "lifecycle":
            if not who: continue  # entity orphan (extractor ghi tên không khớp DB)
            v = (s.value_text or "").strip().upper()
            if v in _RESTRICTED:
                must.append(f"{who} {_RESTRICTED[v]}")
                never.append(f"hồi sinh/tái xuất {who} nếu không có sự kiện được duyệt")
            elif v == "ALIVE":
                pass  # default
        elif key == "location":
            if not who: continue
            must.append(f"{who} đang ở {s.value_text} — cần sự kiện di chuyển để ở nơi khác")
        elif key == "age":
            if not who: continue
            must.append(f"{who} hiện {s.value_text} — tuổi đã chốt, không viết "
                        f"hành vi/hoạt động lệch lứa tuổi này")
        elif key == "education":
            if not who: continue
            must.append(f"{who} — {s.value_text} — bậc học/lớp đã chốt, "
                        f"không xếp sai hoạt động học")
        elif key == "ownership":
            must.append(f"{s.value_text} (ownership đã ghi — không đổi chủ tự do)")
        elif key.startswith("ability."):
            if not who: continue
            ability = key.split(".", 1)[1]
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

    # --- open threads relevant now; dàn chương (cast_json) ghim thread tác giả
    # đã chọn cho chương — lên đầu danh sách và được bảo chủ động đụng tới
    pinned_tids: set[str] = set()
    if scene:
        ch = await db.get(Chapter, scene.chapter_id)
        if ch and ch.cast_json:
            try:
                pinned_tids = set(json.loads(ch.cast_json).get("threads") or [])
            except Exception:
                pinned_tids = set()
    open_threads = list((await db.scalars(
        select(Thread).where(Thread.project_id == pid, Thread.status == "OPEN"))).all())
    open_threads.sort(key=lambda t: 0 if t.id in pinned_tids else 1)
    for th in open_threads[:8]:
        if th.id in pinned_tids:
            must.append(f"Hố '{th.title}' — tác giả chọn cho chương này: để nó "
                        f"bề mặt/nhích tiến nếu xương cảnh cho phép")
        else:
            may.append(f"Hố '{th.title}' đang mở — chỉ đụng tới nếu xương cảnh yêu cầu")

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
