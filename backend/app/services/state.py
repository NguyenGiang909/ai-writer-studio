"""Temporal story-state queries: "what was true at story_time t?"

StoryState rows are point-in-time facts for an entity (character, location,
item, ...). `state_at` returns the newest state not later than t.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.truth import StoryState


async def state_at(
    db: AsyncSession,
    pid: str,
    entity_type: str,
    entity_id: str,
    key: str,
    story_time: int | None = None,
) -> StoryState | None:
    """Latest StoryState for (entity, key) effective at story_time t.

    t=None → latest state overall. Rows with story_time NULL count as always-on
    (story_time treated as -inf).
    """
    q = select(StoryState).where(
        StoryState.project_id == pid,
        StoryState.entity_type == entity_type,
        StoryState.entity_id == entity_id,
        StoryState.key == key,
    )
    rows = list((await db.scalars(q)).all())
    if not rows:
        return None

    def key_fn(s: StoryState) -> int:
        return -1 if s.story_time is None else s.story_time

    if story_time is None:
        return max(rows, key=key_fn)
    eligible = [s for s in rows if s.story_time is None or s.story_time <= story_time]
    return max(eligible, key=key_fn) if eligible else None


def effective_at(states: list[StoryState], story_time: int | None) -> dict[tuple[str, str, str], StoryState]:
    """Group a pre-fetched state list into the latest row per (entity_type, entity_id, key)
    effective at story_time. story_time=None → latest overall; NULL story_time = always-on."""
    grouped: dict[tuple[str, str, str], StoryState] = {}
    for s in states:
        if story_time is not None and s.story_time is not None and s.story_time > story_time:
            continue
        k = (s.entity_type, s.entity_id, s.key)
        cur = grouped.get(k)
        cur_t = -1 if cur is None or cur.story_time is None else cur.story_time
        s_t = -1 if s.story_time is None else s.story_time
        if cur is None or s_t >= cur_t:
            grouped[k] = s
    return grouped


async def states_at(
    db: AsyncSession,
    pid: str,
    story_time: int | None = None,
    entity_type: str | None = None,
    key: str | None = None,
) -> list[StoryState]:
    """All effective (entity,key) states at time t — one row per entity+key."""
    q = select(StoryState).where(StoryState.project_id == pid)
    if entity_type:
        q = q.where(StoryState.entity_type == entity_type)
    if key:
        q = q.where(StoryState.key == key)
    rows = list((await db.scalars(q)).all())
    grouped: dict[tuple[str, str, str], StoryState] = {}
    for s in rows:
        if story_time is not None and s.story_time is not None and s.story_time > story_time:
            continue
        k = (s.entity_type, s.entity_id, s.key)
        cur = grouped.get(k)
        cur_t = -1 if cur is None or cur.story_time is None else cur.story_time
        s_t = -1 if s.story_time is None else s.story_time
        if cur is None or s_t >= cur_t:
            grouped[k] = s
    return list(grouped.values())
