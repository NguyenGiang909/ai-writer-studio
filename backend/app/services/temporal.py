
from sqlalchemy import select,or_
from app.models.truth import StoryState,KnowledgeState
async def story_state_as_of(db,project_id,entity_id,key,story_time,narrative_order):
    q=select(StoryState).where(StoryState.project_id==project_id,StoryState.entity_id==entity_id,StoryState.key==key)
    if story_time is not None: q=q.where(or_(StoryState.story_time==None,StoryState.story_time<=story_time))
    if narrative_order is not None: q=q.where(or_(StoryState.narrative_order==None,StoryState.narrative_order<=narrative_order))
    q=q.order_by(StoryState.story_time.desc(),StoryState.narrative_order.desc()).limit(1)
    return (await db.scalars(q)).first()
async def knowledge_as_of(db,project_id,knower_id,narrative_order):
    q=select(KnowledgeState).where(KnowledgeState.project_id==project_id,KnowledgeState.knower_id==knower_id)
    if narrative_order is not None: q=q.where(or_(KnowledgeState.acquired_narrative_order==None,KnowledgeState.acquired_narrative_order<=narrative_order))
    return list((await db.scalars(q)).all())
