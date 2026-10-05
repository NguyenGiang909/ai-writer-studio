
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import Project
from app.models.manuscript import Chapter, Scene
from app.models.story import Character, Alias
from app.models.truth import StoryState
from app.models.narrative import Thread, ThreadBeat
from app.services import signals as sig

router = APIRouter()


@router.get("/projects/{pid}/signals")
async def project_signals(pid: str, db: AsyncSession = Depends(get_db)):
    if not await db.get(Project, pid):
        raise HTTPException(404, "project not found")
    chapters = {c.id: c for c in (await db.scalars(
        select(Chapter).where(Chapter.project_id == pid))).all()}
    scenes = list((await db.scalars(
        select(Scene).where(Scene.project_id == pid))).all())
    characters = list((await db.scalars(
        select(Character).where(Character.project_id == pid))).all())
    aliases = list((await db.scalars(
        select(Alias).where(Alias.project_id == pid))).all())
    life_states = list((await db.scalars(select(StoryState).where(
        StoryState.project_id == pid, StoryState.entity_type == "character",
        StoryState.key == "lifecycle"))).all())
    threads = list((await db.scalars(
        select(Thread).where(Thread.project_id == pid))).all())
    beats = list((await db.scalars(
        select(ThreadBeat).where(ThreadBeat.project_id == pid))).all())

    # effective narrative order: scene's own order, else its chapter's
    eff = []
    for sc in scenes:
        ch = chapters.get(sc.chapter_id)
        eff.append(type("S", (), {"id": sc.id, "title": sc.title,
                                 "prose": sc.prose,
                                 "narrative_order": sc.narrative_order
                                 if sc.narrative_order is not None
                                 else (ch.order_index if ch else None)})())
    orders = [sc.narrative_order for sc in eff if sc.narrative_order is not None]
    current = max(orders) if orders else None
    scene_titles = {sc.id: sc.title for sc in scenes}

    dormancy = sig.cast_dormancy(eff, characters, aliases, life_states)
    health = sig.thread_health(threads, beats, current)
    reps = sig.repetition_candidates(eff)
    for r in reps:
        r["scenes"] = [{"id": sid, "title": scene_titles.get(sid)}
                       for sid in r.pop("scene_ids")]
    return {
        "current_order": current,
        "cast_dormancy": dormancy,
        "thread_health": health,
        "repetition": reps,
    }
