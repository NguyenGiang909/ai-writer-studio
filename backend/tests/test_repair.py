"""Vòng sửa sau khi viết xong — chèn/xoá chương dời trục narrative, re-extract
thay facts trích của chương mà giữ facts tác giả."""
import pytest
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models import Chapter, Scene
from app.models.truth import StoryState
from app.models.memory import StorySummary
from app.models.authoring import EntityProvenance


async def _mk_project(client, n_ch=3, prose="Văn."):
    p = (await client.post("/api/v1/projects", json={"name": "T"})).json()
    chs = []
    for i in range(1, n_ch + 1):
        ch = (await client.post(f"/api/v1/projects/{p['id']}/chapters",
                                json={"title": f"C{i}", "order_index": i})).json()
        (await client.post(f"/api/v1/projects/{p['id']}/chapters/{ch['id']}/scenes",
                           json={"title": f"S{i}", "order_index": 1, "prose": prose})).json()
        chs.append(ch)
    return p, chs


@pytest.mark.asyncio
async def test_shift_narrative_moves_all_axes(client):
    """Chèn chương giữa: chapters + states + summaries dời đồng bộ."""
    from app.models.memory import StorySummary
    from app.models.narrative import ThreadBeat, Thread
    p, chs = await _mk_project(client)
    pid = p["id"]
    async with SessionLocal() as db:
        db.add(StoryState(project_id=pid, entity_type="character", entity_id="e1",
                          key="location", value_text="x", narrative_order=2))
        db.add(StorySummary(project_id=pid, scope_type="chapter", scope_id=chs[2]["id"],
                            summary="s", narrative_end=3))
        th = Thread(project_id=pid, title="t", planned_payoff_order=3, status="OPEN")
        db.add(th); await db.flush()
        db.add(ThreadBeat(project_id=pid, thread_id=th.id, beat_type="setup",
                          narrative_order=2))
        await db.commit()
    r = await client.post(f"/api/v1/projects/{pid}/chapters/insert",
                          json={"title": "Mới", "order_index": 2})
    assert r.status_code == 200
    async with SessionLocal() as db:
        orders = [c.order_index for c in (await db.scalars(select(Chapter).where(
            Chapter.project_id == pid).order_by(Chapter.order_index))).all()]
        assert orders == [1, 2, 3, 4]
        st = (await db.scalars(select(StoryState).where(
            StoryState.project_id == pid))).first()
        assert st.narrative_order == 3          # 2 → 3
        su = (await db.scalars(select(StorySummary).where(
            StorySummary.project_id == pid))).first()
        assert su.narrative_end == 4            # 3 → 4
        beat = (await db.scalars(select(ThreadBeat))).first()
        assert beat.narrative_order == 3
        th = (await db.scalars(select(Thread))).first()
        assert th.planned_payoff_order == 4


@pytest.mark.asyncio
async def test_insert_rejects_out_of_range(client):
    p, _ = await _mk_project(client)
    r = await client.post(f"/api/v1/projects/{p['id']}/chapters/insert",
                          json={"title": "X", "order_index": 99})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_insert_scene_between_shifts_siblings(client):
    """Cảnh bổ sung chèn giữa — sibling order_index đẩy lên, kế thừa story_time."""
    p, chs = await _mk_project(client, n_ch=1)
    ch = chs[0]
    (await client.post(f"/api/v1/projects/{p['id']}/chapters/{ch['id']}/scenes",
                       json={"title": "S2", "order_index": 2})).json()
    r = await client.post(f"/api/v1/projects/{p['id']}/chapters/{ch['id']}/scenes",
                          json={"title": "Giữa", "order_index": 2})
    assert r.status_code == 200
    async with SessionLocal() as db:
        titles = [(s.title, s.order_index) for s in (await db.scalars(select(Scene).where(
            Scene.chapter_id == ch["id"]).order_by(Scene.order_index))).all()]
        assert titles == [("S1", 1), ("Giữa", 2), ("S2", 3)]


@pytest.mark.asyncio
async def test_wipe_keeps_author_facts(client):
    """Re-extract wipe chỉ xoá rows có provenance AI — facts tác giả sống."""
    p, chs = await _mk_project(client, n_ch=1)
    pid, ch = p["id"], chs[0]
    async with SessionLocal() as db:
        scene = (await db.scalars(select(Scene).where(
            Scene.chapter_id == ch["id"]))).first()
        ai_row = StoryState(project_id=pid, entity_type="character", entity_id="e1",
                            key="location", value_text="ai", narrative_order=1)
        author_row = StoryState(project_id=pid, entity_type="character", entity_id="e1",
                                key="mood", value_text="tay", narrative_order=1)
        db.add_all([ai_row, author_row]); await db.flush()
        db.add(EntityProvenance(project_id=pid, entity_type="story_state",
                                entity_id=ai_row.id, origin="ai"))
        await db.commit()
        from app.services.repair import wipe_chapter_extractions
        removed = await wipe_chapter_extractions(db, pid,
                                                 await db.get(Chapter, ch["id"]))
        await db.commit()
        assert removed["states"] == 1
        left = [s.value_text for s in (await db.scalars(select(StoryState).where(
            StoryState.project_id == pid))).all()]
        assert left == ["tay"]


@pytest.mark.asyncio
async def test_delete_chapter_compacts_axis(client):
    """Xoá chương 2: scenes+facts dọn sạch, chương 3 tụt về 2."""
    p, chs = await _mk_project(client)
    pid = p["id"]
    async with SessionLocal() as db:
        db.add(StoryState(project_id=pid, entity_type="character", entity_id="e1",
                          key="location", value_text="x", narrative_order=3))
        await db.commit()
    r = await client.delete(f"/api/v1/projects/{pid}/chapters/{chs[1]['id']}")
    assert r.status_code == 200
    async with SessionLocal() as db:
        orders = [c.order_index for c in (await db.scalars(select(Chapter).where(
            Chapter.project_id == pid).order_by(Chapter.order_index))).all()]
        assert orders == [1, 2]
        sc = (await db.scalars(select(Scene).where(
            Scene.chapter_id == chs[1]["id"]))).first()
        assert sc is None
        st = (await db.scalars(select(StoryState).where(
            StoryState.project_id == pid))).first()
        assert st.narrative_order == 2          # 3 → 2


@pytest.mark.asyncio
async def test_reextract_replaces_chapter_facts(client):
    """Endpoint reextract: wipe AI facts cũ rồi extract lại (fake provider)."""
    p, chs = await _mk_project(client, n_ch=1)
    pid, ch = p["id"], chs[0]
    async with SessionLocal() as db:
        stale = StoryState(project_id=pid, entity_type="character", entity_id="e1",
                           key="location", value_text="cu", narrative_order=1)
        db.add(stale); await db.flush()
        db.add(EntityProvenance(project_id=pid, entity_type="story_state",
                                entity_id=stale.id, origin="ai"))
        await db.commit()
    r = await client.post(f"/api/v1/projects/{pid}/chapters/{ch['id']}/reextract")
    assert r.status_code == 200 and r.json()["added"] > 0
    async with SessionLocal() as db:
        vals = [s.value_text for s in (await db.scalars(select(StoryState).where(
            StoryState.project_id == pid))).all()]
        assert "cu" not in vals                 # fact cũ bị thay
        assert (await db.scalars(select(StorySummary).where(
            StorySummary.scope_id == ch["id"]))).first() is not None
