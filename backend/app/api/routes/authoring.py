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
                       call_mode=p.call_mode or "safe",
                       flow=p.flow or "rolling")
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
    # context AI đang nắm — panel phải của phòng authoring
    ctx = {}
    try:
        ctx = json.loads(run.cursor_json or "{}")
    except Exception:
        ctx = {}
    from app.models import Arc, Chapter, Character, Location, Faction, Item, Ability
    arcs = list((await db.scalars(select(Arc).where(
        Arc.project_id == pid).order_by(Arc.order_index))).all())
    chs = list((await db.scalars(select(Chapter).where(
        Chapter.project_id == pid))).all())
    done_keys = {r[0] for r in (await db.execute(select(AuthoringStep.step_key).where(
        AuthoringStep.project_id == pid, AuthoringStep.status == "done"))).all()}
    wave = ctx.get("wave_arc")
    arc_list = []
    for a in arcs:
        achs = [c for c in chs if c.arc_id == a.id]
        if a.id == wave:
            st = "current"
        elif achs and all(f"chapter_facts.{c.id}" in done_keys for c in achs):
            st = "done"
        else:
            st = "todo"
        arc_list.append({"id": a.id, "title": a.title, "state": st,
                         "chapters": len(achs)})
    cast = [r[0] for r in (await db.execute(select(Character.name).where(
        Character.project_id == pid).limit(24))).all()]
    # resolve uuid đuôi step_key → tên entity cho nhật ký đọc được
    ent: dict[str, str] = {}
    tail_ids = {s.step_key.rsplit(".", 1)[-1] for s in steps
                if len(s.step_key.rsplit(".", 1)[-1]) == 36}
    if tail_ids:
        ch_map = {c.id: c for c in chs}
        arc_map = {a.id: a for a in arcs}
        sc_rows = (await db.execute(select(
            Scene.id, Scene.title, Scene.order_index, Scene.chapter_id)
            .where(Scene.id.in_(tail_ids)))).all()
        for sid, stitle, sorder, scid in sc_rows:
            c = ch_map.get(scid)
            pre = f"Ch{c.order_index} · " if c else ""
            ent[sid] = f"{pre}{stitle or ('Cảnh ' + str(sorder))}"
        for cid in tail_ids:
            c = ch_map.get(cid)
            if c:
                ent[cid] = f"Ch{c.order_index} {c.title}"
        for aid in tail_ids:
            a = arc_map.get(aid)
            if a:
                ent[aid] = a.title
    counts = {"characters": len(cast),
              "locations": await db.scalar(select(func.count(Location.id)).where(Location.project_id == pid)) or 0,
              "factions": await db.scalar(select(func.count(Faction.id)).where(Faction.project_id == pid)) or 0,
              "items": await db.scalar(select(func.count(Item.id)).where(Item.project_id == pid)) or 0,
              "abilities": await db.scalar(select(func.count(Ability.id)).where(Ability.project_id == pid)) or 0,
              "chapters": len(chs), "scenes": n_scenes or 0, "with_prose": n_prose or 0}
    return {
        "run": {
            "id": run.id, "phase": run.phase, "status": run.status,
            "prompt": run.prompt, "stage_payload": payload,
            "target_chapters": run.target_chapters,
            "words_per_scene": run.words_per_scene,
            "call_mode": run.call_mode,
            "flow": run.flow, "pause_after_wave": run.pause_after_wave,
            "wave_arc": wave,
            "progress": {"scenes": n_scenes or 0, "with_prose": n_prose or 0},
            "last_error": run.last_error, "created_at": str(run.created_at),
            "updated_at": str(run.updated_at), "live": eng.is_live(run.id),
        },
        "steps": [{"key": s.step_key, "status": s.status, "error": s.error,
                   "name": ent.get(s.step_key.rsplit(".", 1)[-1]),
                   "at": str(s.created_at)} for s in steps],
        "phases": eng.phases_for(run),
        "context": {
            "premise": {k: ctx.get(k) for k in
                        ("title", "logline", "genre", "tone") if ctx.get(k)},
            "skeleton": ctx.get("skeleton"),
            "arcs": arc_list,
            "cast": cast, "counts": counts,
        },
    }


@router.post("/projects/{pid}/authoring/approve")
async def approve(pid: str, db: AsyncSession = Depends(get_db)):
    run = await _latest_run(db, pid)
    if not run:
        raise HTTPException(404, "chưa có run")
    if run.status != "awaiting_review":
        raise HTTPException(409, f"run không đang chờ duyệt (status={run.status})")
    phs = eng.phases_for(run)
    idx = phs.index(run.phase)
    if run.phase == "build":
        # build là phase cuối của rolling nhưng checkpoint sóng có thể còn hồi
        # chưa dựng → chạy tiếp cùng phase, tick tự complete khi hết việc
        run.status = "running"
        run.stage_payload_json = None
    elif idx >= len(phs) - 1:
        run.status = "complete"
    else:
        run.phase = phs[idx + 1]
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


@router.post("/projects/{pid}/authoring/pause-after-wave")
async def pause_after_wave(pid: str, db: AsyncSession = Depends(get_db)):
    """Cờ 1-lần: hồi đang sóng viết xong thì dừng checkpoint thay vì sang hồi kế.
    Khác pause (dừng ngay giữa step) — cái này cho tác giả canh điểm dừng sạch."""
    run = await _latest_run(db, pid)
    if not run:
        raise HTTPException(404, "chưa có run")
    if run.status != "running":
        raise HTTPException(409, f"run đang {run.status} — chỉ đặt cờ khi đang chạy")
    run.pause_after_wave = not run.pause_after_wave  # toggle — bấm lại để huỷ
    await db.commit()
    return {"pause_after_wave": run.pause_after_wave}


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
