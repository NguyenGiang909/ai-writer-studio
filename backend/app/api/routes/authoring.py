"""AI Authoring endpoints — start/pause/approve/resume pipeline tạo truyện.

Mọi thao tác đọc run từ DB rồi spawn/tick — engine stateless.
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import Project
from app.models.authoring import AuthoringRun, AuthoringStep, EntityProvenance
from app.schemas.extras import AuthoringStartRequest, AuthoringRegenerateRequest
from app.services import authoring as eng

router = APIRouter()


async def _latest_run(db: AsyncSession, pid: str) -> AuthoringRun | None:
    return (await db.scalars(select(AuthoringRun).where(
        AuthoringRun.project_id == pid).order_by(
        AuthoringRun.created_at.desc()))).first()


@router.post("/projects/{pid}/authoring/start")
async def start(pid: str, p: AuthoringStartRequest, db: AsyncSession = Depends(get_db)):
    proj = await db.get(Project, pid)
    if not proj:
        raise HTTPException(404, "project not found")
    existing = await _latest_run(db, pid)
    if existing and existing.status in {"running", "awaiting_review", "paused"}:
        raise HTTPException(409, f"đã có run đang mở (status={existing.status})")
    prompt = (p.prompt or "").strip()
    if not prompt:
        # dự án rỗng bắt buộc ý tưởng; dự án có sẵn → AI tự tiếp nhận khung hiện có
        from app.models import Chapter, Character
        has_content = bool((proj.description or "").strip()) or bool(
            await db.scalar(select(func.count(Chapter.id)).where(Chapter.project_id == pid))) or bool(
            await db.scalar(select(func.count(Character.id)).where(Character.project_id == pid)))
        if not has_content:
            raise HTTPException(400, "truyện mới cần ít nhất 1 câu ý tưởng")
        prompt = "Tiếp tục phát triển truyện theo khung hiện có — điền phần còn thiếu, không ghi đè nội dung tác giả."
    run = AuthoringRun(project_id=pid, prompt=prompt,
                       phase="premise", status="running",
                       target_chapters=p.target_chapters,
                       words_per_scene=p.words_per_scene,
                       call_mode=p.call_mode or "safe")
    db.add(run)
    await db.commit()
    await db.refresh(run)
    eng.spawn(run.id)
    return {"run_id": run.id, "phase": run.phase, "status": run.status}


@router.get("/projects/{pid}/authoring/status")
async def status(pid: str, db: AsyncSession = Depends(get_db)):
    run = await _latest_run(db, pid)
    if not run:
        return {"run": None}
    # auto-heal: run ghi "running" nhưng task chết (restart server) → spawn lại
    if run.status == "running" and not eng.is_live(run.id):
        eng.spawn(run.id)
    steps = list((await db.scalars(select(AuthoringStep).where(
        AuthoringStep.run_id == run.id).order_by(
        AuthoringStep.created_at.desc()))).all()[:30])
    # progress: số scene có prose / tổng scene — cho UI hiển thị "x/y"
    from app.models import Scene
    n_scenes = await db.scalar(select(func.count(Scene.id)).where(
        Scene.project_id == pid))
    n_prose = await db.scalar(select(func.count(Scene.id)).where(
        Scene.project_id == pid, Scene.prose.is_not(None), Scene.prose != ""))
    payload = None
    if run.stage_payload_json:
        try:
            payload = json.loads(run.stage_payload_json)
        except Exception:
            payload = None
    return {
        "run": {
            "id": run.id, "phase": run.phase, "status": run.status,
            "prompt": run.prompt, "stage_payload": payload,
            "target_chapters": run.target_chapters,
            "words_per_scene": run.words_per_scene,
            "call_mode": run.call_mode,
            "progress": {"scenes": n_scenes or 0, "with_prose": n_prose or 0},
            "last_error": run.last_error, "created_at": str(run.created_at),
            "updated_at": str(run.updated_at), "live": eng.is_live(run.id),
        },
        "steps": [{"key": s.step_key, "status": s.status, "error": s.error,
                   "at": str(s.created_at)} for s in steps],
        "phases": eng.PHASES,
    }


@router.post("/projects/{pid}/authoring/approve")
async def approve(pid: str, db: AsyncSession = Depends(get_db)):
    run = await _latest_run(db, pid)
    if not run:
        raise HTTPException(404, "chưa có run")
    if run.status != "awaiting_review":
        raise HTTPException(409, f"run không đang chờ duyệt (status={run.status})")
    idx = eng.PHASES.index(run.phase)
    if idx >= len(eng.PHASES) - 1:
        run.status = "complete"
    else:
        run.phase = eng.PHASES[idx + 1]
        run.status = "running"
        run.stage_payload_json = None
    await db.commit()
    if run.status == "running":
        eng.spawn(run.id)
    return {"phase": run.phase, "status": run.status}


@router.post("/projects/{pid}/authoring/regenerate")
async def regenerate(pid: str, p: AuthoringRegenerateRequest,
                     db: AsyncSession = Depends(get_db)):
    """Tạo lại stage đang checkpoint — xoá entity AI của stage đó rồi chạy lại."""
    run = await _latest_run(db, pid)
    if not run:
        raise HTTPException(404, "chưa có run")
    if run.status != "awaiting_review":
        raise HTTPException(409, f"chỉ tạo lại được khi đang checkpoint (status={run.status})")
    try:
        await eng.regenerate(db, run, (p.hint or "").strip() or None)
    except ValueError as e:
        raise HTTPException(409, str(e))
    await db.commit()
    eng.spawn(run.id)
    return {"phase": run.phase, "status": run.status}


@router.post("/projects/{pid}/authoring/pause")
async def pause(pid: str, db: AsyncSession = Depends(get_db)):
    run = await _latest_run(db, pid)
    if not run:
        raise HTTPException(404, "chưa có run")
    if run.status == "running":
        run.status = "paused"
        await db.commit()
    return {"status": run.status}


@router.post("/projects/{pid}/authoring/resume")
async def resume(pid: str, db: AsyncSession = Depends(get_db)):
    run = await _latest_run(db, pid)
    if not run:
        raise HTTPException(404, "chưa có run")
    if run.status not in {"paused", "failed"}:
        raise HTTPException(409, f"run đang {run.status}")
    # reset bộ đếm lỗi — step fail cũ không chặn lần thử lại sau khi đã sửa
    await db.execute(delete(AuthoringStep).where(
        AuthoringStep.run_id == run.id, AuthoringStep.status == "failed"))
    run.status = "running"
    run.last_error = None
    await db.commit()
    eng.spawn(run.id)
    return {"status": "running"}


@router.get("/projects/{pid}/authoring/provenance")
async def provenance(pid: str, entity_type: str | None = None,
                     db: AsyncSession = Depends(get_db)):
    """Map entity_id → origin cho UI badge 'AI'."""
    q = select(EntityProvenance).where(EntityProvenance.project_id == pid)
    if entity_type:
        q = q.where(EntityProvenance.entity_type == entity_type)
    rows = (await db.scalars(q)).all()
    return {"items": [{"entity_type": r.entity_type, "entity_id": r.entity_id,
                       "origin": r.origin, "run_id": r.run_id} for r in rows]}


@router.get("/projects/{pid}/authoring/steps")
async def steps(pid: str, db: AsyncSession = Depends(get_db)):
    run = await _latest_run(db, pid)
    if not run:
        return {"steps": []}
    rows = list((await db.scalars(select(AuthoringStep).where(
        AuthoringStep.run_id == run.id).order_by(AuthoringStep.created_at))).all())
    return {"steps": [{"key": s.step_key, "status": s.status,
                       "output": json.loads(s.output_json) if s.output_json else None,
                       "error": s.error, "at": str(s.created_at),
                       "finished": str(s.finished_at) if s.finished_at else None}
                      for s in rows]}
