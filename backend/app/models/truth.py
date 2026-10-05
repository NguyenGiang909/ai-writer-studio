
import uuid
from datetime import datetime
from sqlalchemy import String,Text,ForeignKey,Integer,DateTime,Boolean,Float,UniqueConstraint
from sqlalchemy.orm import Mapped,mapped_column
from app.db.base import Base
def uid(): return str(uuid.uuid4())

class CanonFact(Base):
    __tablename__="canon_facts"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    project_id:Mapped[str]=mapped_column(ForeignKey("projects.id",ondelete="CASCADE"),index=True)
    subject_type:Mapped[str]=mapped_column(String(64)); subject_id:Mapped[str|None]=mapped_column(String(36),index=True)
    predicate:Mapped[str]=mapped_column(String(120)); value_text:Mapped[str]=mapped_column(Text)
    truth_status:Mapped[str]=mapped_column(String(24),default="CANON")
    locked:Mapped[bool]=mapped_column(Boolean,default=False)
    valid_from:Mapped[int|None]=mapped_column(Integer); valid_to:Mapped[int|None]=mapped_column(Integer)
    source_scene_id:Mapped[str|None]=mapped_column(ForeignKey("scenes.id",ondelete="SET NULL"))
class AuthorDecision(Base):
    __tablename__="author_decisions"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    project_id:Mapped[str]=mapped_column(ForeignKey("projects.id",ondelete="CASCADE"),index=True)
    title:Mapped[str]=mapped_column(String(240)); decision_text:Mapped[str]=mapped_column(Text)
    status:Mapped[str]=mapped_column(String(24),default="active")
    rationale:Mapped[str|None]=mapped_column(Text); rejected_json:Mapped[str|None]=mapped_column(Text)
class StoryEvent(Base):
    __tablename__="story_events"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    project_id:Mapped[str]=mapped_column(ForeignKey("projects.id",ondelete="CASCADE"),index=True)
    scene_id:Mapped[str|None]=mapped_column(ForeignKey("scenes.id",ondelete="SET NULL"),index=True)
    event_type:Mapped[str]=mapped_column(String(64)); summary:Mapped[str]=mapped_column(Text)
    story_time:Mapped[int|None]=mapped_column(Integer,index=True)
    narrative_order:Mapped[int|None]=mapped_column(Integer,index=True)
    location_id:Mapped[str|None]=mapped_column(ForeignKey("locations.id",ondelete="SET NULL"))
class StoryState(Base):
    __tablename__="story_states"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    project_id:Mapped[str]=mapped_column(ForeignKey("projects.id",ondelete="CASCADE"),index=True)
    entity_type:Mapped[str]=mapped_column(String(64)); entity_id:Mapped[str]=mapped_column(String(36),index=True)
    key:Mapped[str]=mapped_column(String(120)); value_text:Mapped[str]=mapped_column(Text)
    story_time:Mapped[int|None]=mapped_column(Integer,index=True); narrative_order:Mapped[int|None]=mapped_column(Integer,index=True)
    source_event_id:Mapped[str|None]=mapped_column(ForeignKey("story_events.id",ondelete="SET NULL"))
class KnowledgeState(Base):
    __tablename__="knowledge_states"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    project_id:Mapped[str]=mapped_column(ForeignKey("projects.id",ondelete="CASCADE"),index=True)
    knower_type:Mapped[str]=mapped_column(String(32),default="character"); knower_id:Mapped[str|None]=mapped_column(String(36),index=True)
    fact_id:Mapped[str]=mapped_column(ForeignKey("canon_facts.id",ondelete="CASCADE"),index=True)
    state:Mapped[str]=mapped_column(String(24),default="KNOWS")
    disclosure_level:Mapped[int]=mapped_column(Integer,default=100)
    known_aspects:Mapped[str|None]=mapped_column(Text)
    acquired_story_time:Mapped[int|None]=mapped_column(Integer,index=True)
    acquired_narrative_order:Mapped[int|None]=mapped_column(Integer,index=True)
class Secret(Base):
    __tablename__="secrets"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    project_id:Mapped[str]=mapped_column(ForeignKey("projects.id",ondelete="CASCADE"),index=True)
    fact_id:Mapped[str]=mapped_column(ForeignKey("canon_facts.id",ondelete="CASCADE"),index=True)
    title:Mapped[str]=mapped_column(String(240)); status:Mapped[str]=mapped_column(String(24),default="active")
