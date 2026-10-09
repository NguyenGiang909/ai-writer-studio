"""Neo vị trí truyện — vá lỗi lệch bối cảnh khi viết dài (58 chương).

Kiểm chứng: scene_expand nhận neo Chương N/M + hồi + đuôi cảnh liền trước +
recap đã viết; constraints lọc state tương lai theo narrative_order
(= chapter.order_index); key trích tự do ("nơi ở") chuẩn hoá; chapter_facts
ghi StorySummary recap không tốn call thêm; cast không đổ nhân vật pha khác.
"""
import json

import pytest, pytest_asyncio
import app.services.authoring as eng
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models import Arc, Character, Chapter, Scene
from app.models.truth import StoryEvent, StoryState
from app.models.memory import StorySummary
from app.models.authoring import AuthoringStep
from app.models.narrative import Thread
from app.models.story import Ability as AbilityModel
from app.ai.compose import build_story_prompt
from app.services.constraints import (
    canonical_state_key, build_constraints, render_constraints)
from app.services.state import states_at


@pytest.fixture(autouse=True)
def _no_spawn(monkeypatch):
    monkeypatch.setattr(eng, "spawn", lambda rid: None)


def test_canonical_state_key():
    assert canonical_state_key("nơi ở") == "location"
    assert canonical_state_key(" Vị Trí ") == "location"
    assert canonical_state_key("sinh tử") == "lifecycle"
    assert canonical_state_key("sở hữu") == "ownership"
    assert canonical_state_key("tâm trạng") == "status"
    assert canonical_state_key("tuổi") == "age"
    assert canonical_state_key("lớp") == "education"
    assert canonical_state_key("trường học") == "education"
    assert canonical_state_key("bloodline") == "bloodline"  # passthrough
    assert canonical_state_key(None) == "state"


@pytest.mark.asyncio
async def test_states_at_filters_future_narrative(client):
    """State tương lai (narrative_order > vị trí cảnh) không được lộ."""
    pid = (await client.post("/api/v1/projects", json={"name": "T"})).json()["id"]
    async with SessionLocal() as db:
        c = Character(project_id=pid, name="Minh")
        db.add(c); await db.flush()
        db.add(StoryState(project_id=pid, entity_type="character",
                          entity_id=c.id, key="location",
                          value_text="làng", narrative_order=2))
        db.add(StoryState(project_id=pid, entity_type="character",
                          entity_id=c.id, key="location",
                          value_text="phố", narrative_order=12))
        cid = c.id
        await db.commit()
        at2 = await states_at(db, pid, narrative_order=2)
        assert len(at2) == 1 and at2[0].value_text == "làng"
        latest = await states_at(db, pid)
        assert latest[0].value_text == "phố"  # không filter → state mới nhất


@pytest.mark.asyncio
async def test_constraints_hide_future_and_orphans(client):
    """Prompt cảnh chương 2: chỉ thấy 'đang ở làng', không thấy phố/entity rác."""
    pid = (await client.post("/api/v1/projects", json={"name": "T"})).json()["id"]
    async with SessionLocal() as db:
        c = Character(project_id=pid, name="Minh")
        db.add(c); await db.flush()
        ch = Chapter(project_id=pid, title="C2", order_index=2)
        db.add(ch); await db.flush()
        sc = Scene(project_id=pid, chapter_id=ch.id, title="S",
                   order_index=0, narrative_order=2)
        db.add(sc)
        db.add(StoryState(project_id=pid, entity_type="character",
                          entity_id=c.id, key="nơi ở",          # key tự do
                          value_text="làng", narrative_order=1))
        db.add(StoryState(project_id=pid, entity_type="character",
                          entity_id=c.id, key="location",
                          value_text="khu tập thể", narrative_order=9))  # tương lai
        db.add(StoryState(project_id=pid, entity_type="character",
                          entity_id="orphan-uuid-rac", key="location",
                          value_text="quán net", narrative_order=1))
        db.add(Thread(project_id=pid, title="Chuyển nhà", status="OPEN"))
        # tuổi/lớp tại vị trí — bậc học chốt cho dàn ý (lỗi "tập đọc" cấp 2)
        db.add(StoryState(project_id=pid, entity_type="character",
                          entity_id=c.id, key="tuổi", value_text="11 tuổi",
                          narrative_order=1))
        db.add(StoryState(project_id=pid, entity_type="character",
                          entity_id=c.id, key="lớp", value_text="lớp 9 cấp 2",
                          narrative_order=1))
        db.add(StoryState(project_id=pid, entity_type="character",
                          entity_id=c.id, key="age", value_text="40 tuổi",
                          narrative_order=20))  # tương lai — không được lộ
        await db.commit()
        m = await build_constraints(db, pid, sc)
        text = render_constraints(m)
        assert "Minh đang ở làng" in text
        assert "khu tập thể" not in text            # state tương lai bị ẩn
        assert "quán net" not in text                # entity orphan bị bỏ
        assert "chỉ đụng tới nếu xương cảnh yêu cầu" in text  # thread không mời dẫn
        assert "Minh hiện 11 tuổi" in text            # age canonical → MUST
        assert "lớp 9 cấp 2" in text                 # education canonical → MUST
        assert "40 tuổi" not in text                 # tuổi tương lai bị ẩn


@pytest.mark.asyncio
async def test_scene_expand_prompt_has_anchor(client):
    """scene_expand: neo vị trí + đuôi cảnh trước + recap + cast lọc."""
    pid = (await client.post("/api/v1/projects", json={"name": "T"})).json()["id"]
    async with SessionLocal() as db:
        arc = Arc(project_id=pid, title="Hồi Quê", order_index=1)
        db.add(arc); await db.flush()
        ch1 = Chapter(project_id=pid, arc_id=arc.id, title="C1", order_index=1)
        ch2 = Chapter(project_id=pid, arc_id=arc.id, title="C2", order_index=2)
        db.add_all([ch1, ch2]); await db.flush()
        db.add(Scene(project_id=pid, chapter_id=ch1.id, title="S0",
                     order_index=0, prose="văn chương một",
                     narrative_order=1))
        s1 = Scene(project_id=pid, chapter_id=ch2.id, title="S1",
                   order_index=0, narrative_order=2,
                   prose="nội dung … CÂU_NEO_TRƯỚC")
        s2 = Scene(project_id=pid, chapter_id=ch2.id, title="S2",
                   order_index=1, narrative_order=2,
                   skeleton="Minh gặp lại bạn cũ")
        db.add_all([s1, s2])
        db.add(StoryEvent(project_id=pid, event_type="plot",
                          summary="SỰ_KIỆN_CHƯƠNG_1", narrative_order=1))
        db.add(StorySummary(project_id=pid, scope_type="chapter",
                            scope_id=ch1.id, summary="TÓM_TẮT_CH1",
                            narrative_end=1, stale=False))
        db.add(Character(project_id=pid, name="Minh", importance=0))
        db.add(Character(project_id=pid, name="Kẻ Pha Xa", importance=3))
        await db.commit()
        sid = s2.id
    async with SessionLocal() as db:
        _, body, manifest = await build_story_prompt(
            db, pid, "scene_expand", "Viết cảnh.", scene_id=sid)
        assert 'Chương 2/2' in body
        assert 'Hồi "Hồi Quê"' in body
        assert "Cảnh trước trong chương" in body and "CÂU_NEO_TRƯỚC" in body
        assert "SỰ_KIỆN_CHƯƠNG_1" in body          # written-recap: events
        assert "TÓM_TẮT_CH1" in body               # recap chương trước
        assert "Kẻ Pha Xa" not in body             # chưa lộ mặt, kém quan trọng
        inc = "\n".join(manifest)
        assert "prev-scenes" in inc and "written-recap" in inc


@pytest.mark.asyncio
async def test_chapter_outline_has_bedrock(client):
    """Dàn cảnh nhận bedrock: tuổi/lớp/ở của nhân vật tại vị trí chương —
    tránh lỗi dàn 'tập đọc' cho nhân vật cấp 2."""
    pid = (await client.post("/api/v1/projects", json={"name": "T"})).json()["id"]
    async with SessionLocal() as db:
        c = Character(project_id=pid, name="Sơn")
        db.add(c); await db.flush()
        ch = Chapter(project_id=pid, title="Trường làng", order_index=2)
        db.add(ch); await db.flush()
        db.add(StoryState(project_id=pid, entity_type="character",
                          entity_id=c.id, key="age", value_text="11 tuổi",
                          narrative_order=0))
        db.add(StoryState(project_id=pid, entity_type="character",
                          entity_id=c.id, key="education",
                          value_text="lớp 9 cấp 2", narrative_order=0))
        db.add(StoryState(project_id=pid, entity_type="character",
                          entity_id=c.id, key="location", value_text="làng",
                          narrative_order=1))
        cid = ch.id
        await db.commit()
    async with SessionLocal() as db:
        _, body, manifest = await build_story_prompt(
            db, pid, "chapter_outline", "", chapter_id=cid)
        assert "Hiện trạng nhân vật tại điểm này" in body
        assert "Sơn · tuổi: 11 tuổi" in body
        assert "Sơn · lớp/trường: lớp 9 cấp 2" in body
        assert "Sơn · đang ở: làng" in body
        assert "bedrock-states" in "\n".join(manifest)


@pytest.mark.asyncio
async def test_rolling_anchor_pipeline(client):
    """End-to-end rolling: scenes có narrative_order, key chuẩn hoá,
    recap → StorySummary, scene_write step trả issues[]."""
    pid = (await client.post("/api/v1/projects",
                             json={"name": "Anchor"})).json()["id"]
    (await client.post(f"/api/v1/projects/{pid}/authoring/start",
                       json={"prompt": "người mất ký ức"})).raise_for_status()
    run_id = (await client.get(
        f"/api/v1/projects/{pid}/authoring/status")).json()["run"]["id"]
    for _ in range(80):
        await eng.tick(run_id)
        st = (await client.get(
            f"/api/v1/projects/{pid}/authoring/status")).json()["run"]
        if st["status"] == "awaiting_review":
            ap = (await client.post(
                f"/api/v1/projects/{pid}/authoring/approve")).json()
            if ap["status"] == "complete":
                break
        elif st["status"] in {"complete", "failed"}:
            break
    assert st["status"] == "complete"
    async with SessionLocal() as db:
        scenes = (await db.scalars(select(Scene).where(
            Scene.project_id == pid))).all()
        assert scenes and all(s.narrative_order is not None for s in scenes)
        chs = {c.id: c for c in (await db.scalars(
            select(Chapter).where(Chapter.project_id == pid))).all()}
        for s in scenes:
            assert s.narrative_order == chs[s.chapter_id].order_index
        keys = {st_.key for st_ in (await db.scalars(
            select(StoryState).where(StoryState.project_id == pid))).all()}
        assert "location" in keys              # "nơi ở" đã chuẩn hoá
        assert "nơi ở" not in keys
        assert "age" in keys and "education" in keys  # cast seed trạng thái nền
        seeded = [s for s in (await db.scalars(select(StoryState).where(
            StoryState.project_id == pid, StoryState.key == "age"))).all()
                  if s.narrative_order == 0]
        assert seeded and any("tuổi" in (s.value_text or "") for s in seeded)
        sums = (await db.scalars(select(StorySummary).where(
            StorySummary.project_id == pid,
            StorySummary.scope_type == "chapter"))).all()
        assert sums and any("la bàn" in (s.summary or "") for s in sums)
        writes = [s for s in (await db.scalars(select(AuthoringStep).where(
            AuthoringStep.project_id == pid,
            AuthoringStep.step_key.like("scene_write.%")))).all()]
        assert writes
        for w in writes:
            out = json.loads(w.output_json or "{}")
            assert "issues" in out and isinstance(out["issues"], list)


@pytest.mark.asyncio
async def test_fast_mode_writes_whole_chapter(client):
    """call_mode=fast: chương viết bằng 1 call chapter_write, không tách cảnh."""
    pid = (await client.post("/api/v1/projects",
                             json={"name": "Fast"})).json()["id"]
    (await client.post(f"/api/v1/projects/{pid}/authoring/start",
                       json={"prompt": "người mất ký ức",
                             "call_mode": "fast"})).raise_for_status()
    run_id = (await client.get(
        f"/api/v1/projects/{pid}/authoring/status")).json()["run"]["id"]
    for _ in range(80):
        await eng.tick(run_id)
        st = (await client.get(
            f"/api/v1/projects/{pid}/authoring/status")).json()["run"]
        if st["status"] == "awaiting_review":
            ap = (await client.post(
                f"/api/v1/projects/{pid}/authoring/approve")).json()
            if ap["status"] == "complete":
                break
        elif st["status"] in {"complete", "failed"}:
            break
    assert st["status"] == "complete"
    async with SessionLocal() as db:
        steps = (await db.scalars(select(AuthoringStep).where(
            AuthoringStep.project_id == pid))).all()
        keys = [s.step_key for s in steps]
        chw = [k for k in keys if k.startswith("chapter_write.")]
        assert chw, "fast mode phải gom chương thành 1 call"
        assert not any(k.startswith("scene_write.") for k in keys), \
            "fast mode parse đủ cảnh → không cần scene_write bù"
        scenes = (await db.scalars(select(Scene).where(
            Scene.project_id == pid))).all()
        assert scenes and all((s.prose or "").strip() for s in scenes)
        out = json.loads(next(
            s for s in steps if s.step_key.startswith("chapter_write.")
        ).output_json or "{}")
        assert out["scenes_written"] >= 2 and "issues" in out


@pytest.mark.asyncio
async def test_chapter_cast_pins_context(client):
    """Dàn chương: nhân vật/hố/năng lực tác giả ghim vào context trước heuristic —
    ability được inject kèm cơ chế; pinned thread lên đầu trong constraints."""
    pid = (await client.post("/api/v1/projects", json={"name": "T"})).json()["id"]
    async with SessionLocal() as db:
        ch = Chapter(project_id=pid, title="Chương 1", order_index=1)
        db.add(ch); await db.flush()
        sc = Scene(project_id=pid, chapter_id=ch.id, title="S1",
                   order_index=0, narrative_order=1, prose="")
        hidden = Character(project_id=pid, name="Bà Tàng", importance=5)
        th1 = Thread(project_id=pid, title="Hố được ghim", status="OPEN")
        th2 = Thread(project_id=pid, title="Hố lạc lõng", status="OPEN")
        ab = AbilityModel(project_id=pid, name="Mở tàng khố",
                          can_do="phá phong ấn", cannot_do="hồi sinh người chết",
                          cost="mất một ký ức")
        db.add_all([sc, hidden, th1, th2, ab]); await db.flush()
        ch.cast_json = json.dumps(
            {"characters": [hidden.id], "threads": [th1.id],
             "abilities": [ab.id]})
        await db.commit()
        sid = sc.id
    async with SessionLocal() as db:
        _, body, manifest = await build_story_prompt(
            db, pid, "scene_expand", "Viết cảnh.", scene_id=sid)
        assert "Bà Tàng" in body and "tác giả chọn cho chương này" in body
        assert "Năng lực trong chương" in body and "Mở tàng khố" in body
        assert "KHÔNG làm được: hồi sinh người chết" in body
        assert "giá phải trả: mất một ký ức" in body
        assert "cast-abilities" in "\n".join(manifest)
        # constraints: pinned thread → must_respect, thread thường → may_use
        scene = await db.get(Scene, sid)
        cons = build_constraints and render_constraints(
            await build_constraints(db, pid, scene))
        assert "tác giả chọn cho chương này" in cons
        assert "Hố được ghim" in cons
