import pytest, pytest_asyncio
import app.services.authoring as eng
from app.db.session import SessionLocal
from app.models.authoring import AuthoringRun, EntityProvenance
from app.models import Character, Location, Chapter, Scene
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


async def _drive(client, pid: str):
    """Start → chạy tới hết pipeline, approve ở mỗi checkpoint."""
    (await client.post(f"/api/v1/projects/{pid}/authoring/start",
                       json={"prompt": "người mất ký ức tìm lại chính mình"})).raise_for_status()
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
    assert st["phase"] == "writing"
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
