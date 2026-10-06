import pytest, pytest_asyncio
import app.services.authoring as eng
from app.db.session import SessionLocal
from app.models.authoring import AuthoringRun, AuthoringStep, EntityProvenance
from app.models import (Character, Location, Chapter, Scene, Faction, Item,
                        Ability, WorldEntity, StyleProfile)
from app.models.truth import StoryEvent, StoryState, CanonFact
from app.models.narrative import Thread
from sqlalchemy import select


@pytest.fixture(autouse=True)
def _no_spawn(monkeypatch):
    """Tắt background spawn — test drive tick() thủ công cho deterministic."""
    monkeypatch.setattr(eng, "spawn", lambda rid: None)


async def _pump(client, run_id: str, max_ticks: int = 60):
    """Tick tới khi run rời trạng thái running. Trả (status, phase)."""
    for _ in range(max_ticks):
        r = await eng.tick(run_id)
        if r != "step":
            break
    st = (await client.get("/api/v1/projects/_noop/authoring/status"))
    return r


async def _drive(client, pid: str, start_json: dict | None = None):
    """Start → chạy tới hết pipeline, approve ở mỗi checkpoint."""
    (await client.post(f"/api/v1/projects/{pid}/authoring/start",
                       json=start_json or {"prompt": "người mất ký ức tìm lại chính mình"})).raise_for_status()
    st = (await client.get(f"/api/v1/projects/{pid}/authoring/status")).json()
    run_id = st["run"]["id"]
    assert st["run"]["phase"] == "premise" and st["run"]["status"] == "running"

    transitions = []
    for _ in range(80):
        r = await eng.tick(run_id)
        transitions.append(r)
        cur = (await client.get(f"/api/v1/projects/{pid}/authoring/status")).json()["run"]
        if cur["status"] == "awaiting_review":
            ap = (await client.post(f"/api/v1/projects/{pid}/authoring/approve")).json()
            transitions.append(f"approve→{ap['phase']}")
            if ap["status"] == "complete":
                break
        elif cur["status"] in {"complete", "failed"}:
            break
    return run_id, transitions


@pytest.mark.asyncio
async def test_full_pipeline_creates_story(client):
    pid = (await client.post("/api/v1/projects", json={"name": "Truyện mới AI"})).json()["id"]
    run_id, log = await _drive(client, pid)

    st = (await client.get(f"/api/v1/projects/{pid}/authoring/status")).json()["run"]
    assert st["status"] == "complete"
    assert st["phase"] == "build"        # rolling mặc định — phase cuối là build
    assert st["flow"] == "rolling"
    assert "checkpoint" in log  # đã dừng ở ranh giới stage

    async with SessionLocal() as db:
        chars = (await db.scalars(select(Character).where(Character.project_id == pid))).all()
        assert len(chars) >= 3  # fake cast: Minh, Lão Tạp, Kẻ Đốp
        locs = (await db.scalars(select(Location).where(Location.project_id == pid))).all()
        assert len(locs) >= 1
        chapters = (await db.scalars(select(Chapter).where(Chapter.project_id == pid))).all()
        assert len(chapters) == 2
        scenes = (await db.scalars(select(Scene).where(Scene.project_id == pid))).all()
        assert len(scenes) >= 4 and all((s.prose or "").strip() for s in scenes)
        evs = (await db.scalars(select(StoryEvent).where(StoryEvent.project_id == pid))).all()
        assert len(evs) >= 1
        ths = (await db.scalars(select(Thread).where(Thread.project_id == pid))).all()
        assert len(ths) >= 1  # fake facts mở thread "Bí ẩn ký ức"
        prov = (await db.scalars(select(EntityProvenance).where(
            EntityProvenance.project_id == pid, EntityProvenance.origin == "ai"))).all()
        assert len(prov) >= len(chars) + len(chapters) + len(scenes)


@pytest.mark.asyncio
async def test_pause_and_checkpoints(client):
    pid = (await client.post("/api/v1/projects", json={"name": "T"})).json()["id"]
    (await client.post(f"/api/v1/projects/{pid}/authoring/start",
                       json={"prompt": "test"})).raise_for_status()
    st = (await client.get(f"/api/v1/projects/{pid}/authoring/status")).json()["run"]
    run_id = st["id"]

    await eng.tick(run_id)  # premise.generate done
    r = await eng.tick(run_id)  # phase hết → checkpoint
    assert r == "checkpoint"
    st = (await client.get(f"/api/v1/projects/{pid}/authoring/status")).json()["run"]
    assert st["status"] == "awaiting_review" and st["phase"] == "premise"
    assert st["stage_payload"]["title"] == "Truyện Giả Lập"

    # approve mà không qua review → 409 khi đang running
    (await client.post(f"/api/v1/projects/{pid}/authoring/approve")).raise_for_status()
    st = (await client.get(f"/api/v1/projects/{pid}/authoring/status")).json()["run"]
    assert st["phase"] == "cast" and st["status"] == "running"

    # pause: tick nữa không chạy
    (await client.post(f"/api/v1/projects/{pid}/authoring/pause")).raise_for_status()
    r = await eng.tick(run_id)
    assert r == "stopped"
    (await client.post(f"/api/v1/projects/{pid}/authoring/resume")).raise_for_status()
    r = await eng.tick(run_id)
    assert r == "step"  # cast.generate chạy


@pytest.mark.asyncio
async def test_start_conflict_and_resume_idempotent(client):
    pid = (await client.post("/api/v1/projects", json={"name": "T"})).json()["id"]
    (await client.post(f"/api/v1/projects/{pid}/authoring/start",
                       json={"prompt": "ý tưởng đầu"})).raise_for_status()
    # start lần 2 khi đang mở → 409
    r2 = await client.post(f"/api/v1/projects/{pid}/authoring/start",
                           json={"prompt": "ý tưởng hai"})
    assert r2.status_code == 409
    # project không tồn tại
    r3 = await client.post("/api/v1/projects/nonexistent/authoring/start",
                           json={"prompt": "ý tưởng ba"})
    assert r3.status_code == 404


@pytest.mark.asyncio
async def test_steps_endpoint_audit_log(client):
    pid = (await client.post("/api/v1/projects", json={"name": "T"})).json()["id"]
    (await client.post(f"/api/v1/projects/{pid}/authoring/start",
                       json={"prompt": "premise test"})).raise_for_status()
    st = (await client.get(f"/api/v1/projects/{pid}/authoring/status")).json()["run"]
    await eng.tick(st["id"])
    steps = (await client.get(f"/api/v1/projects/{pid}/authoring/steps")).json()["steps"]
    assert any(s["key"] == "premise.generate" and s["status"] == "done" for s in steps)
    assert steps[0]["output"]["title"] == "Truyện Giả Lập"


@pytest.mark.asyncio
async def test_regenerate_cast_replaces_entities(client):
    """Regenerate ở checkpoint cast: entity AI cũ bị xoá, stage chạy lại sạch."""
    pid = (await client.post("/api/v1/projects", json={"name": "T"})).json()["id"]
    (await client.post(f"/api/v1/projects/{pid}/authoring/start",
                       json={"prompt": "đề tài về lòng tin"})).raise_for_status()
    st = (await client.get(f"/api/v1/projects/{pid}/authoring/status")).json()["run"]
    run_id = st["id"]
    # premise → approve → cast.generate → checkpoint
    await eng.tick(run_id)
    await eng.tick(run_id)
    (await client.post(f"/api/v1/projects/{pid}/authoring/approve")).raise_for_status()
    await eng.tick(run_id)   # cast.generate
    r = await eng.tick(run_id)  # → checkpoint
    assert r == "checkpoint"

    async with SessionLocal() as db:
        before = len((await db.scalars(select(Character).where(
            Character.project_id == pid))).all())
        assert before >= 3
        prov_before = len((await db.scalars(select(EntityProvenance).where(
            EntityProvenance.project_id == pid))).all())

    # regenerate cast → entity cũ xoá hết, chạy lại tạo mới
    rg = await client.post(f"/api/v1/projects/{pid}/authoring/regenerate",
                           json={"hint": "ít nhân vật hơn"})
    assert rg.status_code == 200 and rg.json()["status"] == "running"
    await eng.tick(run_id)
    await eng.tick(run_id)
    st = (await client.get(f"/api/v1/projects/{pid}/authoring/status")).json()["run"]
    assert st["status"] == "awaiting_review" and st["phase"] == "cast"

    async with SessionLocal() as db:
        after = (await db.scalars(select(Character).where(
            Character.project_id == pid))).all()
        assert len(after) >= 3  # tạo lại được
        prov = (await db.scalars(select(EntityProvenance).where(
            EntityProvenance.project_id == pid))).all()
        # provenance cũ của character/alias/relationship đã xoá, chỉ còn bộ mới
        char_prov = [p for p in prov if p.entity_type == "character"]
        assert len(char_prov) == len(after)


@pytest.mark.asyncio
async def test_regenerate_guards(client):
    pid = (await client.post("/api/v1/projects", json={"name": "T"})).json()["id"]
    # chưa có run → 404
    r = await client.post(f"/api/v1/projects/{pid}/authoring/regenerate", json={})
    assert r.status_code == 404
    (await client.post(f"/api/v1/projects/{pid}/authoring/start",
                       json={"prompt": "xxx"})).raise_for_status()
    # đang running (chưa checkpoint) → 409
    r = await client.post(f"/api/v1/projects/{pid}/authoring/regenerate", json={})
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_cast_importance_clamped(client):
    """Model trả importance 1-5 → map về bucket 0-3 của app."""
    pid = (await client.post("/api/v1/projects", json={"name": "T"})).json()["id"]
    (await client.post(f"/api/v1/projects/{pid}/authoring/start",
                       json={"prompt": "ttt"})).raise_for_status()
    st = (await client.get(f"/api/v1/projects/{pid}/authoring/status")).json()["run"]
    await eng.tick(st["id"]); await eng.tick(st["id"])
    (await client.post(f"/api/v1/projects/{pid}/authoring/approve")).raise_for_status()
    await eng.tick(st["id"])
    async with SessionLocal() as db:
        imps = [c.importance for c in (await db.scalars(select(Character).where(
            Character.project_id == pid))).all()]
        assert all(i is None or 0 <= i <= 3 for i in imps)


@pytest.mark.asyncio
async def test_continue_existing_project(client):
    """Dự án có sẵn khung: skip premise/cast/world/outline, chỉ điền chỗ thiếu.

    Setup: ch1 có scene với prose tác giả viết; ch2 có scene rỗng; ch3 chưa có scene.
    Kỳ vọng: không checkpoint rỗng; prose tác giả nguyên vẹn; scene rỗng được viết;
    ch3 được dàn cảnh; facts trích từ toàn bộ chương; provenance chỉ trên entity AI."""
    pid = (await client.post("/api/v1/projects", json={
        "name": "Vĩnh Thành", "description": "Đại gia đình buôn tơ lụa"})).json()["id"]
    async with SessionLocal() as db:
        db.add(Character(project_id=pid, name="Bảy Vĩnh", role="protagonist"))
        # world đủ 6 loại → world phase skip hẳn, không gọi AI bù
        db.add(Location(project_id=pid, name="Làng lụa Vĩnh Thành"))
        db.add(Faction(project_id=pid, name="Hội tơ lụa"))
        db.add(Item(project_id=pid, name="Khung dệt cổ"))
        db.add(Ability(project_id=pid, name="Thấu vân tơ", ability_type="nghề"))
        db.add(WorldEntity(project_id=pid, name="Lễ hội tơ", entity_type="lore"))
        db.add(StyleProfile(project_id=pid, name="chính", scope_type="global"))
        ch1 = Chapter(project_id=pid, title="Hồi mở", order_index=1)
        ch2 = Chapter(project_id=pid, title="Biến cố", order_index=2)
        ch3 = Chapter(project_id=pid, title="Lật bài", order_index=3)
        db.add_all([ch1, ch2, ch3]); await db.flush()
        author_prose = "Đoạn văn tác giả tự viết. " * 30
        db.add(Scene(project_id=pid, chapter_id=ch1.id, title="S1",
                     order_index=0, prose=author_prose))
        db.add(Scene(project_id=pid, chapter_id=ch2.id, title="S2",
                     order_index=0, prose=None, skeleton="beat sẵn"))
        await db.commit()

    # không prompt — dự án có sẵn nên hợp lệ
    r = await client.post(f"/api/v1/projects/{pid}/authoring/start", json={})
    assert r.status_code == 200
    run_id = r.json()["run_id"]

    log = []
    for _ in range(80):
        r_ = await eng.tick(run_id)
        log.append(r_)
        cur = (await client.get(f"/api/v1/projects/{pid}/authoring/status")).json()["run"]
        if cur["status"] == "awaiting_review":
            (await client.post(f"/api/v1/projects/{pid}/authoring/approve")).raise_for_status()
            log.append("approve")
        elif cur["status"] in {"complete", "failed"}:
            break
    st = (await client.get(f"/api/v1/projects/{pid}/authoring/status")).json()["run"]
    assert st["status"] == "complete"

    async with SessionLocal() as db:
        steps = (await db.scalars(select(AuthoringStep).where(
            AuthoringStep.project_id == pid))).all()
        keys = {s.step_key for s in steps}
        # premise/cast/world/outline.generate KHÔNG chạy — dữ liệu có sẵn
        assert not any(k.startswith(("premise.", "cast.", "world.", "outline.")) for k in keys)
        # ch3 được dàn cảnh
        assert any(k.startswith("chapter_scenes.") for k in keys)
        scenes = (await db.scalars(select(Scene).where(
            Scene.project_id == pid).order_by(Scene.order_index))).all()
        s_author = [s for s in scenes if s.title == "S1"][0]
        assert s_author.prose == author_prose  # prose tác giả nguyên vẹn
        s2 = [s for s in scenes if s.title == "S2"][0]
        assert (s2.prose or "").strip()       # scene rỗng được AI viết
        assert all((s.prose or "").strip() for s in scenes)
        # facts được trích cho các chương có prose
        evs = (await db.scalars(select(StoryEvent).where(
            StoryEvent.project_id == pid))).all()
        assert len(evs) >= 1
        # provenance: scene của tác giả KHÔNG có badge, scene AI có
        prov = {p.entity_id for p in (await db.scalars(select(EntityProvenance).where(
            EntityProvenance.project_id == pid))).all()}
        assert s_author.id not in prov
        assert s2.id not in prov  # scene row do tác giả tạo — chỉ prose là AI
        ch3_scenes = [s for s in scenes if s.chapter_id == ch3.id]
        assert ch3_scenes and all(s.id in prov for s in ch3_scenes)


@pytest.mark.asyncio
async def test_world_partial_fills_only_missing(client):
    """World tách 3 sub-step: dự án có location sẵn nhưng thiếu faction/item/
    ability/lore/style → places chỉ bù faction (không đụng location),
    rules/lore chạy bù → checkpoint ở cuối world."""
    pid = (await client.post("/api/v1/projects", json={
        "name": "T", "description": "premise sẵn"})).json()["id"]
    async with SessionLocal() as db:
        db.add(Character(project_id=pid, name="A"))
        db.add(Location(project_id=pid, name="Làng sẵn"))
        await db.commit()
    (await client.post(f"/api/v1/projects/{pid}/authoring/start",
                       json={})).raise_for_status()
    st = (await client.get(f"/api/v1/projects/{pid}/authoring/status")).json()["run"]
    for _ in range(40):
        await eng.tick(st["id"])
        cur = (await client.get(f"/api/v1/projects/{pid}/authoring/status")).json()["run"]
        if cur["status"] != "running":
            break
    assert cur["status"] == "awaiting_review" and cur["phase"] == "world"
    async with SessionLocal() as db:
        locs = (await db.scalars(select(Location).where(
            Location.project_id == pid))).all()
        assert [l.name for l in locs] == ["Làng sẵn"]  # không trùng/không thêm
        fcts = (await db.scalars(select(Faction).where(
            Faction.project_id == pid))).all()
        assert len(fcts) >= 1  # fake world → "Hội Thủ Thư" bù vào
        items = (await db.scalars(select(Item).where(
            Item.project_id == pid))).all()
        assert len(items) >= 1
        keys = {s.step_key for s in (await db.scalars(select(AuthoringStep).where(
            AuthoringStep.project_id == pid))).all()}
        assert {"world.places", "world.rules", "world.lore"} <= keys


@pytest.mark.asyncio
async def test_outline_partial_fills_only_empty_arcs(client):
    """Outline tách 2 tầng: arc1 có chương sẵn + arc2 rỗng → chỉ dàn arc2,
    chương mới gắn đúng arc2, chương sẵn không bị đụng."""
    from app.models import Arc
    pid = (await client.post("/api/v1/projects", json={
        "name": "T", "description": "premise sẵn"})).json()["id"]
    async with SessionLocal() as db:
        db.add(Character(project_id=pid, name="A"))
        db.add(Location(project_id=pid, name="L"))
        db.add(Faction(project_id=pid, name="F"))
        db.add(Item(project_id=pid, name="I"))
        db.add(Ability(project_id=pid, name="Ab"))
        db.add(WorldEntity(project_id=pid, name="W"))
        db.add(StyleProfile(project_id=pid, name="S", scope_type="global"))
        arc1 = Arc(project_id=pid, title="Hồi 1", order_index=1)
        arc2 = Arc(project_id=pid, title="Hồi 2", order_index=2)
        db.add_all([arc1, arc2]); await db.flush()
        ch_old = Chapter(project_id=pid, arc_id=arc1.id, title="Chương cũ",
                         order_index=1, status="draft")
        db.add(ch_old); await db.flush()
        db.add(Scene(project_id=pid, chapter_id=ch_old.id, title="S",
                     order_index=0, prose="x " * 200))
        arc1_id, arc2_id, ch_old_id = arc1.id, arc2.id, ch_old.id
        await db.commit()
    (await client.post(f"/api/v1/projects/{pid}/authoring/start",
                       json={})).raise_for_status()
    st = (await client.get(f"/api/v1/projects/{pid}/authoring/status")).json()["run"]
    for _ in range(60):
        await eng.tick(st["id"])
        cur = (await client.get(f"/api/v1/projects/{pid}/authoring/status")).json()["run"]
        if cur["status"] == "awaiting_review":
            (await client.post(f"/api/v1/projects/{pid}/authoring/approve")).raise_for_status()
        elif cur["status"] in {"complete", "failed"}:
            break
    assert cur["status"] == "complete"
    async with SessionLocal() as db:
        keys = {s.step_key for s in (await db.scalars(select(AuthoringStep).where(
            AuthoringStep.project_id == pid))).all()}
        assert not any(k.startswith("outline.skeleton") for k in keys)  # arcs sẵn → skip
        assert f"outline.chapters.{arc2_id}" in keys
        assert f"outline.chapters.{arc1_id}" not in keys  # arc1 đã có chương
        chs = (await db.scalars(select(Chapter).where(
            Chapter.project_id == pid).order_by(Chapter.order_index))).all()
        new = [c for c in chs if c.id != ch_old_id]
        assert new and all(c.arc_id == arc2.id for c in new)


@pytest.mark.asyncio
async def test_start_empty_prompt_rejected_on_empty_project(client):
    pid = (await client.post("/api/v1/projects", json={"name": "Trống"})).json()["id"]
    r = await client.post(f"/api/v1/projects/{pid}/authoring/start", json={})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_second_run_does_not_reextract_facts(client):
    """Run thứ 2 trên cùng project: chapter_facts không trích lại → không trùng events."""
    pid = (await client.post("/api/v1/projects", json={"name": "T2"})).json()["id"]
    async with SessionLocal() as db:
        ch = Chapter(project_id=pid, title="C1", order_index=1)
        db.add(ch); await db.flush()
        db.add(Scene(project_id=pid, chapter_id=ch.id, title="S",
                     order_index=0, prose="Prose đủ dài để trích facts. " * 10))
        await db.commit()
    for run_no in range(2):
        r = await client.post(f"/api/v1/projects/{pid}/authoring/start", json={})
        run_id = r.json()["run_id"]
        for _ in range(60):
            await eng.tick(run_id)
            cur = (await client.get(f"/api/v1/projects/{pid}/authoring/status")).json()["run"]
            if cur["status"] == "awaiting_review":
                (await client.post(f"/api/v1/projects/{pid}/authoring/approve")).raise_for_status()
            elif cur["status"] in {"complete", "failed"}:
                break
    async with SessionLocal() as db:
        evs = (await db.scalars(select(StoryEvent).where(
            StoryEvent.project_id == pid))).all()
        n_events = len(evs)
        keys = [s.step_key for s in (await db.scalars(select(AuthoringStep).where(
            AuthoringStep.project_id == pid, AuthoringStep.status == "done"))).all()]
        # chapter_facts chỉ chạy 1 lần duy nhất dù 2 run
        assert len([k for k in keys if k.startswith("chapter_facts.")]) == 1
        assert n_events <= 15  # fake provider trả ~2/chapter; không nhân đôi


@pytest.mark.asyncio
async def test_failed_step_fails_run_then_resume(client, monkeypatch):
    """Step lỗi 2 lần → run 'failed'; sửa handler → resume chạy tiếp được."""
    pid = (await client.post("/api/v1/projects", json={"name": "T"})).json()["id"]
    (await client.post(f"/api/v1/projects/{pid}/authoring/start",
                       json={"prompt": "test fail"})).raise_for_status()
    st = (await client.get(f"/api/v1/projects/{pid}/authoring/status")).json()["run"]

    real = eng.HANDLERS["premise"]
    monkeypatch.setitem(eng.HANDLERS, "premise",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))

    for _ in range(3):
        await eng.tick(st["id"])  # fail, fail, lần 3 thấy failed>=2 → run failed
    cur = (await client.get(f"/api/v1/projects/{pid}/authoring/status")).json()["run"]
    assert cur["status"] == "failed"
    assert "premise.generate" in (cur["last_error"] or "")

    # sửa xong → resume → tick → premise.generate thành công
    monkeypatch.setitem(eng.HANDLERS, "premise", real)
    (await client.post(f"/api/v1/projects/{pid}/authoring/resume")).raise_for_status()
    await eng.tick(st["id"])
    r = await eng.tick(st["id"])
    assert r == "checkpoint"
    cur = (await client.get(f"/api/v1/projects/{pid}/authoring/status")).json()["run"]
    assert cur["status"] == "awaiting_review"


@pytest.mark.asyncio
async def test_provenance_entity_type_filter(client):
    pid = (await client.post("/api/v1/projects", json={"name": "T"})).json()["id"]
    run_id, _ = await _drive(client, pid)
    all_items = (await client.get(
        f"/api/v1/projects/{pid}/authoring/provenance")).json()["items"]
    chars = (await client.get(
        f"/api/v1/projects/{pid}/authoring/provenance?entity_type=character")).json()["items"]
    assert chars and all(i["entity_type"] == "character" for i in chars)
    assert len(chars) < len(all_items)
    assert all(i["origin"] == "ai" for i in all_items)


@pytest.mark.asyncio
async def test_regenerate_outline_replaces_tree(client):
    """Regenerate outline: volume/arc/chapter/scene AI cũ bị xoá sạch, dựng bộ mới."""
    pid = (await client.post("/api/v1/projects", json={"name": "T"})).json()["id"]
    (await client.post(f"/api/v1/projects/{pid}/authoring/start",
                       json={"prompt": "chu du thời gian",
                             "flow": "batch"})).raise_for_status()
    run_id = (await client.get(f"/api/v1/projects/{pid}/authoring/status")).json()["run"]["id"]

    # chạy tới checkpoint outline (premise→cast→world→outline xong)
    for _ in range(80):
        await eng.tick(run_id)
        cur = (await client.get(f"/api/v1/projects/{pid}/authoring/status")).json()["run"]
        if cur["status"] == "awaiting_review" and cur["phase"] == "outline":
            break
        if cur["status"] == "awaiting_review":
            (await client.post(f"/api/v1/projects/{pid}/authoring/approve")).raise_for_status()
    else:
        raise AssertionError("không tới checkpoint outline")

    async with SessionLocal() as db:
        old_ch_ids = {c.id for c in (await db.scalars(select(Chapter).where(
            Chapter.project_id == pid))).all()}
        assert old_ch_ids

    (await client.post(f"/api/v1/projects/{pid}/authoring/regenerate", json={})).raise_for_status()
    for _ in range(80):
        r = await eng.tick(run_id)
        if r != "step":
            break
    cur = (await client.get(f"/api/v1/projects/{pid}/authoring/status")).json()["run"]
    assert cur["status"] == "awaiting_review" and cur["phase"] == "outline"

    async with SessionLocal() as db:
        new_chs = (await db.scalars(select(Chapter).where(
            Chapter.project_id == pid))).all()
        new_ids = {c.id for c in new_chs}
        assert new_ids and not (new_ids & old_ch_ids)  # toàn id mới
        # provenance chỉ trỏ entity còn sống
        prov_ids = {p.entity_id for p in (await db.scalars(select(EntityProvenance).where(
            EntityProvenance.project_id == pid,
            EntityProvenance.entity_type == "chapter"))).all()}
        assert prov_ids == new_ids
        scs = (await db.scalars(select(Scene).where(Scene.project_id == pid))).all()
        assert all(s.chapter_id in new_ids for s in scs)  # không scene mồ côi


@pytest.mark.asyncio
async def test_chapter_facts_writes_canon_and_beats(client):
    """Facts extraction ghi đủ story_event + canon_fact + thread_beat có provenance."""
    pid = (await client.post("/api/v1/projects", json={"name": "T"})).json()["id"]
    await _drive(client, pid)
    async with SessionLocal() as db:
        evs = (await db.scalars(select(StoryEvent).where(StoryEvent.project_id == pid))).all()
        cf = (await db.scalars(select(CanonFact).where(CanonFact.project_id == pid))).all()
        assert evs and cf  # fake facts trả cả hai
        from app.models.narrative import ThreadBeat
        beats = (await db.scalars(select(ThreadBeat).where(ThreadBeat.project_id == pid))).all()
        assert beats
        prov_types = {p.entity_type for p in (await db.scalars(select(EntityProvenance).where(
            EntityProvenance.project_id == pid))).all()}
        assert {"story_event", "canon_fact", "thread_beat"} <= prov_types


@pytest.mark.asyncio
async def test_goals_reach_prompts(client):
    """target_chapters → outline prompt; words_per_scene → scene_write prompt."""
    pid = (await client.post("/api/v1/projects", json={"name": "T"})).json()["id"]
    r = await client.post(f"/api/v1/projects/{pid}/authoring/start", json={
        "prompt": "hải trình cuối", "target_chapters": 12, "words_per_scene": 1500,
        "flow": "batch"})
    assert r.status_code == 200
    run_id = r.json()["run_id"]

    # chạy tới hết outline
    for _ in range(60):
        await eng.tick(run_id)
        cur = (await client.get(f"/api/v1/projects/{pid}/authoring/status")).json()["run"]
        if cur["status"] == "awaiting_review" and cur["phase"] == "outline":
            break
        if cur["status"] == "awaiting_review":
            (await client.post(f"/api/v1/projects/{pid}/authoring/approve")).raise_for_status()

    async with SessionLocal() as db:
        from app.models.memory import AiTurn
        turns = (await db.scalars(select(AiTurn).where(
            AiTurn.project_id == pid, AiTurn.task == "book_outline"))).all()
        assert turns and "~12" in turns[-1].prompt_excerpt

    # approve outline → writing: check scene_write prompt mang độ dài mục tiêu
    (await client.post(f"/api/v1/projects/{pid}/authoring/approve")).raise_for_status()
    for _ in range(60):
        r_ = await eng.tick(run_id)
        cur = (await client.get(f"/api/v1/projects/{pid}/authoring/status")).json()["run"]
        if cur["status"] == "awaiting_review" and cur["phase"] == "writing":
            break
        if cur["status"] == "awaiting_review":
            (await client.post(f"/api/v1/projects/{pid}/authoring/approve")).raise_for_status()
        elif cur["status"] in {"complete", "failed"}:
            break
    async with SessionLocal() as db:
        from app.models.memory import AiTurn
        turns = (await db.scalars(select(AiTurn).where(
            AiTurn.project_id == pid, AiTurn.task == "scene_expand"))).all()
        assert turns and "~1500" in turns[-1].prompt_excerpt
        run = await db.get(AuthoringRun, run_id)
        assert run.target_chapters == 12 and run.words_per_scene == 1500
    # status trả progress
    st = (await client.get(f"/api/v1/projects/{pid}/authoring/status")).json()["run"]
    assert st["progress"]["scenes"] >= 1


@pytest.mark.asyncio
async def test_call_mode_default_safe_and_validation(client):
    """call_mode mặc định safe; giá trị lạ bị 422; status trả đúng mode."""
    pid = (await client.post("/api/v1/projects", json={"name": "T"})).json()["id"]
    r = await client.post(f"/api/v1/projects/{pid}/authoring/start",
                          json={"prompt": "x", "call_mode": "turbo"})
    assert r.status_code == 422
    (await client.post(f"/api/v1/projects/{pid}/authoring/start",
                       json={"prompt": "x"})).raise_for_status()
    st = (await client.get(f"/api/v1/projects/{pid}/authoring/status")).json()["run"]
    assert st["call_mode"] == "safe"
    async with SessionLocal() as db:
        run = await db.get(AuthoringRun, st["id"])
        assert run.call_mode == "safe"


@pytest.mark.asyncio
async def test_fast_mode_uses_grouped_calls(client):
    """fast: world + outline gộp 1 call mỗi stage; phần thiếu vẫn granular bù."""
    pid = (await client.post("/api/v1/projects", json={"name": "T"})).json()["id"]
    run_id, log = await _drive(client, pid, {"prompt": "kẻ trộm ký ức",
                                           "call_mode": "fast", "flow": "batch"})
    st = (await client.get(f"/api/v1/projects/{pid}/authoring/status")).json()["run"]
    assert st["status"] == "complete" and st["call_mode"] == "fast"

    async with SessionLocal() as db:
        keys = {s.step_key for s in (await db.scalars(select(AuthoringStep).where(
            AuthoringStep.run_id == run_id))).all()}
        assert "world.generate" in keys
        assert "outline.generate" in keys
        assert not any(k.startswith("world.places") for k in keys)
        assert "outline.skeleton" not in keys
        # fake outline trả chapter_count (không dàn chương) → per-arc vẫn bù
        assert any(k.startswith("outline.chapters.") for k in keys)
        chapters = (await db.scalars(select(Chapter).where(
            Chapter.project_id == pid))).all()
        assert len(chapters) == 2


@pytest.mark.asyncio
async def test_safe_mode_uses_split_calls(client):
    """safe: world 3 sub-step + outline skeleton/arc — không call gộp."""
    pid = (await client.post("/api/v1/projects", json={"name": "T"})).json()["id"]
    run_id, log = await _drive(client, pid)
    async with SessionLocal() as db:
        keys = {s.step_key for s in (await db.scalars(select(AuthoringStep).where(
            AuthoringStep.run_id == run_id))).all()}
        assert {"world.places", "world.rules", "world.lore"} <= keys
        assert "outline.skeleton" in keys
        assert "world.generate" not in keys and "outline.generate" not in keys


# ---------- rolling flow ----------

async def _seed_ready_for_build(db, pid: str, n_arcs: int = 2):
    """Project đã đủ premise/cast/world + n hồi rỗng → run rolling vào thẳng build."""
    from app.models import Arc
    db.add(Character(project_id=pid, name="Nhân"))
    for m, kw in ((Location, {"name": "L"}), (Faction, {"name": "F"}),
                  (Item, {"name": "I"}), (Ability, {"name": "Ab"}),
                  (WorldEntity, {"name": "W"}),
                  (StyleProfile, {"name": "S", "scope_type": "global"})):
        db.add(m(project_id=pid, **kw))
    ids = []
    for i in range(1, n_arcs + 1):
        a = Arc(project_id=pid, title=f"Hồi {i}", order_index=i)
        db.add(a); await db.flush()
        ids.append(a.id)
    await db.commit()
    return ids


async def _status(client, pid: str):
    return (await client.get(f"/api/v1/projects/{pid}/authoring/status")).json()


@pytest.mark.asyncio
async def test_flow_default_rolling_and_validation(client):
    """flow mặc định rolling; giá trị lạ bị 422; batch chọn tường minh được."""
    pid = (await client.post("/api/v1/projects", json={"name": "T"})).json()["id"]
    r = await client.post(f"/api/v1/projects/{pid}/authoring/start",
                          json={"prompt": "x", "flow": "weird"})
    assert r.status_code == 422
    (await client.post(f"/api/v1/projects/{pid}/authoring/start",
                       json={"prompt": "x"})).raise_for_status()
    st = (await _status(client, pid))["run"]
    assert st["flow"] == "rolling" and st["pause_after_wave"] is False
    async with SessionLocal() as db:
        assert (await db.get(AuthoringRun, st["id"])).flow == "rolling"

    pid2 = (await client.post("/api/v1/projects", json={"name": "T2"})).json()["id"]
    (await client.post(f"/api/v1/projects/{pid2}/authoring/start",
                       json={"prompt": "x", "flow": "batch"})).raise_for_status()
    st2 = (await _status(client, pid2))["run"]
    assert st2["flow"] == "batch"


@pytest.mark.asyncio
async def test_rolling_waves_arc_by_arc(client):
    """Rolling: hồi 1 viết xong (chapter_facts) MỚI dàn chương hồi 2 —
    không lên hết khung rồi mới viết như batch."""
    from app.models import Arc
    pid = (await client.post("/api/v1/projects", json={
        "name": "T", "description": "premise sẵn"})).json()["id"]
    async with SessionLocal() as db:
        a1, a2 = await _seed_ready_for_build(db, pid, 2)
    (await client.post(f"/api/v1/projects/{pid}/authoring/start",
                       json={})).raise_for_status()
    st = (await _status(client, pid))["run"]
    run_id = st["id"]
    assert st["flow"] == "rolling"

    for _ in range(120):
        r = await eng.tick(run_id)
        cur = (await _status(client, pid))["run"]
        if cur["status"] == "awaiting_review":
            (await client.post(f"/api/v1/projects/{pid}/authoring/approve")).raise_for_status()
        elif cur["status"] in {"complete", "failed"}:
            break
    cur = (await _status(client, pid))["run"]
    assert cur["status"] == "complete" and cur["phase"] == "build"

    async with SessionLocal() as db:
        done = [s.step_key for s in (await db.scalars(select(AuthoringStep).where(
            AuthoringStep.project_id == pid, AuthoringStep.status == "done")
            .order_by(AuthoringStep.created_at))).all()]
        chs_a1 = [c.id for c in (await db.scalars(select(Chapter).where(
            Chapter.arc_id == a1))).all()]
        assert not any(k.startswith("outline.skeleton") for k in done)  # arcs sẵn → skip
        last_a1 = max(i for i, k in enumerate(done)
                      if any(k == f"chapter_facts.{c}" for c in chs_a1))
        first_a2 = done.index(f"outline.chapters.{a2}")
        assert last_a1 < first_a2  # hồi 1 viết xong mới dàn hồi 2


@pytest.mark.asyncio
async def test_pause_after_wave_stops_at_boundary(client):
    """Cờ 1-lần: hồi 1 viết xong → checkpoint chờ duyệt (không complete),
    cờ tự tắt; approve → hồi 2 chạy tiếp."""
    pid = (await client.post("/api/v1/projects", json={
        "name": "T", "description": "premise sẵn"})).json()["id"]
    async with SessionLocal() as db:
        a1, a2 = await _seed_ready_for_build(db, pid, 2)
    (await client.post(f"/api/v1/projects/{pid}/authoring/start",
                       json={})).raise_for_status()
    st = (await _status(client, pid))["run"]
    run_id = st["id"]

    # đặt cờ sớm — run vẫn running (premise/cast/world skip → vào build ngay)
    r = await client.post(f"/api/v1/projects/{pid}/authoring/pause-after-wave")
    assert r.status_code == 200 and r.json()["pause_after_wave"] is True

    r = "step"
    while r == "step":
        r = await eng.tick(run_id)
    assert r == "checkpoint"  # không phải complete — đây là ranh giới sóng
    cur = (await _status(client, pid))["run"]
    assert cur["status"] == "awaiting_review" and cur["phase"] == "build"
    assert cur["pause_after_wave"] is False  # cờ 1-lần đã tự tắt
    assert cur["wave_arc"] == a1            # sóng vừa dừng là hồi 1
    # hồi 1 đã viết xong thật
    async with SessionLocal() as db:
        scs = [s for s in (await db.scalars(select(Scene).where(
            Scene.project_id == pid))).all()
            if (await db.get(Chapter, s.chapter_id)).arc_id == a1]
        assert scs and all((s.prose or "").strip() for s in scs)

    # approve → hồi 2 build tiếp → hết việc → complete
    (await client.post(f"/api/v1/projects/{pid}/authoring/approve")).raise_for_status()
    r = "step"
    while r == "step":
        r = await eng.tick(run_id)
    cur = (await _status(client, pid))["run"]
    assert cur["status"] == "complete"
    async with SessionLocal() as db:
        assert f"outline.chapters.{a2}" in {s.step_key for s in (await db.scalars(
            select(AuthoringStep).where(AuthoringStep.project_id == pid))).all()}


@pytest.mark.asyncio
async def test_regen_wave_only_deletes_current_arc(client):
    """Tạo lại ở checkpoint sóng: chỉ xoá entity AI của hồi đang sóng —
    hồi trước (đã viết + facts) nguyên vẹn."""
    from app.models import Arc
    pid = (await client.post("/api/v1/projects", json={
        "name": "T", "description": "premise sẵn"})).json()["id"]
    async with SessionLocal() as db:
        a1, a2, a3 = await _seed_ready_for_build(db, pid, 3)
    (await client.post(f"/api/v1/projects/{pid}/authoring/start",
                       json={})).raise_for_status()
    st = (await _status(client, pid))["run"]
    run_id = st["id"]

    # sóng 1 → checkpoint (cờ đặt sớm)
    await client.post(f"/api/v1/projects/{pid}/authoring/pause-after-wave")
    r = "step"
    while r == "step":
        r = await eng.tick(run_id)
    assert (await _status(client, pid))["run"]["status"] == "awaiting_review"
    # approve → tick 1 lần để sóng 2 thật sự bắt đầu (wave_arc→a2),
    # rồi mới đặt cờ — đặt sớm hơn sẽ bắn ngay ở ranh giới sóng 1→2 đang chờ
    (await client.post(f"/api/v1/projects/{pid}/authoring/approve")).raise_for_status()
    assert await eng.tick(run_id) == "step"
    await client.post(f"/api/v1/projects/{pid}/authoring/pause-after-wave")
    r = "step"
    while r == "step":
        r = await eng.tick(run_id)
    cur = (await _status(client, pid))["run"]
    assert cur["status"] == "awaiting_review" and cur["wave_arc"] == a2

    # snapshot hồi 1 — tài sản phải còn nguyên sau regen
    async with SessionLocal() as db:
        a1_chs = {c.id for c in (await db.scalars(select(Chapter).where(
            Chapter.arc_id == a1))).all()}
        a1_scs = {s.id for s in (await db.scalars(select(Scene).where(
            Scene.chapter_id.in_(a1_chs)))).all()}
        a1_evs = len([e for e in (await db.scalars(select(StoryEvent).where(
            StoryEvent.project_id == pid))).all() if e.scene_id in a1_scs])
        assert a1_chs and a1_scs and a1_evs

    rg = await client.post(f"/api/v1/projects/{pid}/authoring/regenerate", json={})
    assert rg.status_code == 200
    async with SessionLocal() as db:
        assert set((await db.scalars(select(Chapter.id).where(
            Chapter.arc_id == a1))).all()) == a1_chs            # hồi 1 nguyên
        assert set((await db.scalars(select(Scene.id).where(
            Scene.chapter_id.in_(a1_chs)))).all()) == a1_scs
        assert not (await db.scalars(select(Chapter).where(
            Chapter.arc_id == a2))).all()                        # hồi 2 bị dọn
        keys = {s.step_key for s in (await db.scalars(select(AuthoringStep).where(
            AuthoringStep.project_id == pid))).all()}
        assert f"outline.chapters.{a2}" not in keys              # step hồi 2 reset
        assert any(k.startswith("chapter_facts.") for k in keys)  # facts hồi 1 còn
        evs = len([e for e in (await db.scalars(select(StoryEvent).where(
            StoryEvent.project_id == pid))).all() if e.scene_id in a1_scs])
        assert evs == a1_evs                                     # facts hồi 1 nguyên

    # run chạy lại → hồi 2 dựng lại từ đầu
    r = "step"
    while r == "step":
        r = await eng.tick(run_id)
    cur = (await _status(client, pid))["run"]
    async with SessionLocal() as db:
        assert (await db.scalars(select(Chapter).where(
            Chapter.arc_id == a2))).all()                        # hồi 2 dựng lại
