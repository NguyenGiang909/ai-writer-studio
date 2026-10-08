"""Sửa chữa truyện đã viết — dời trục narrative, dọn facts trích cũ, re-extract.

Dùng cho vòng sửa sau khi project viết xong: sửa prose (tay/AI) → re-extract
chương thay facts cũ → chèn chương/cảnh bổ sung giữa mạch → quét lại.

Nguyên tắc: chỉ xoá dữ kiện do pipeline trích (có EntityProvenance origin="ai").
Facts tác giả nhập tay / seed / đã duyệt (không provenance, hoặc locked) được giữ.
"""
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chapter, Scene
from app.models.manuscript import SceneVersion
from app.models.truth import StoryEvent, StoryState, CanonFact, KnowledgeState
from app.models.narrative import Thread, ThreadBeat
from app.models.memory import StorySummary
from app.models.authoring import EntityProvenance

# mọi cột mang vị trí narrative (chapter.order_index scale) — chèn/xoá chương
# phải dời đồng bộ hết, thiếu một bảng là timeline lệch
_NARR_AXIS = [
    (Scene, "narrative_order"),
    (StoryState, "narrative_order"),
    (StoryEvent, "narrative_order"),
    (ThreadBeat, "narrative_order"),
    (KnowledgeState, "acquired_narrative_order"),
    (StorySummary, "narrative_end"),
    (Thread, "planned_payoff_order"),
    (CanonFact, "valid_from"),
    (CanonFact, "valid_to"),
]


async def shift_narrative(db: AsyncSession, pid: str, at_order: int, delta: int) -> int:
    """Dời mọi vị trí narrative >= at_order thêm delta (+1 chèn, -1 khép lỗ).

    chapters.order_index có unique (project_id, order_index) → update từng row
    theo thứ tự desc để không đụng constraint giữa chừng."""
    moved = 0
    chs = list((await db.scalars(select(Chapter).where(
        Chapter.project_id == pid, Chapter.order_index >= at_order)
        .order_by(Chapter.order_index.desc()))).all())
    for c in chs:
        c.order_index += delta
        moved += 1
        await db.flush()  # flush từng row: unique (project,order) cấm batch update
    for model, attr in _NARR_AXIS:
        col = getattr(model, attr)
        rows = list((await db.scalars(select(model).where(
            model.project_id == pid, col.isnot(None), col >= at_order))).all())
        for r in rows:
            setattr(r, attr, getattr(r, attr) + delta)
            moved += 1
    await db.flush()
    return moved


async def wipe_chapter_extractions(db: AsyncSession, pid: str, ch: Chapter) -> dict:
    """Xoá facts trích từ prose của một chương (event/beat/canon theo scene_id
    của scenes chương — extractor luôn ghi scenes[0].id; state theo
    narrative_order = ch.order_index). Chỉ xoá row có provenance AI — facts
    tác giả/seed/đã duyệt giữ nguyên; CanonFact locked cũng giữ."""
    sc_ids = list((await db.scalars(
        select(Scene.id).where(Scene.chapter_id == ch.id))).all())
    prov: dict[str, set[str]] = {}
    for et, eid in (await db.execute(select(
            EntityProvenance.entity_type, EntityProvenance.entity_id)
            .where(EntityProvenance.project_id == pid))).all():
        prov.setdefault(et, set()).add(eid)

    removed = {"events": 0, "states": 0, "beats": 0, "facts": 0}
    gone_ids: list[str] = []

    async def _wipe(model, where, et, count_key, skip_locked=False):
        if not sc_ids and et != "story_state":
            return
        rows = list((await db.scalars(select(model).where(*where))).all())
        for r in rows:
            if r.id not in prov.get(et, set()):
                continue
            if skip_locked and getattr(r, "locked", False):
                continue
            await db.delete(r)
            gone_ids.append(r.id)
            removed[count_key] += 1

    if sc_ids:
        await _wipe(StoryEvent, [StoryEvent.scene_id.in_(sc_ids)],
                    "story_event", "events")
        await _wipe(ThreadBeat, [ThreadBeat.scene_id.in_(sc_ids)],
                    "thread_beat", "beats")
        await _wipe(CanonFact, [CanonFact.source_scene_id.in_(sc_ids)],
                    "canon_fact", "facts", skip_locked=True)
    await _wipe(StoryState, [StoryState.project_id == pid,
                             StoryState.narrative_order == ch.order_index],
                "story_state", "states")

    # dọn provenance trỏ row vừa xoá
    if gone_ids:
        await db.execute(delete(EntityProvenance).where(
            EntityProvenance.entity_id.in_(gone_ids)))
    await db.flush()
    return removed


async def delete_chapter_full(db: AsyncSession, pid: str, ch: Chapter,
                              compact: bool = True) -> dict:
    """Xoá chương + scenes(+versions) + facts trích; compact → khép trục narr."""
    removed = await wipe_chapter_extractions(db, pid, ch)
    sc_ids = list((await db.scalars(
        select(Scene.id).where(Scene.chapter_id == ch.id))).all())
    if sc_ids:
        await db.execute(delete(SceneVersion).where(SceneVersion.scene_id.in_(sc_ids)))
        await db.execute(delete(Scene).where(Scene.id.in_(sc_ids)))
    order = ch.order_index
    await db.delete(ch)
    await db.flush()
    if compact:
        await shift_narrative(db, pid, order, -1)
    return removed
