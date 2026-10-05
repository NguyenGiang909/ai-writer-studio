
import uuid
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, Integer, DateTime, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

def uid() -> str:
    return str(uuid.uuid4())

class Character(Base):
    __tablename__="characters"
    __table_args__=(UniqueConstraint("project_id","name"),)
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    project_id: Mapped[str]=mapped_column(ForeignKey("projects.id",ondelete="CASCADE"),index=True)
    name: Mapped[str]=mapped_column(String(240))
    role: Mapped[str|None]=mapped_column(String(64))
    summary: Mapped[str|None]=mapped_column(Text)
    voice_notes: Mapped[str|None]=mapped_column(Text)
    status: Mapped[str]=mapped_column(String(32),default="active")
    importance: Mapped[int|None]=mapped_column(Integer)
    sort_order: Mapped[int]=mapped_column(Integer,default=0)

class WorldEntity(Base):
    __tablename__="world_entities"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    project_id: Mapped[str]=mapped_column(ForeignKey("projects.id",ondelete="CASCADE"),index=True)
    name: Mapped[str]=mapped_column(String(240))
    entity_type: Mapped[str]=mapped_column(String(64),default="lore")
    description: Mapped[str|None]=mapped_column(Text)

class Location(Base):
    __tablename__="locations"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    project_id: Mapped[str]=mapped_column(ForeignKey("projects.id",ondelete="CASCADE"),index=True)
    parent_location_id: Mapped[str|None]=mapped_column(ForeignKey("locations.id",ondelete="SET NULL"),index=True)
    name: Mapped[str]=mapped_column(String(240))
    description: Mapped[str|None]=mapped_column(Text)

class Faction(Base):
    __tablename__="factions"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    project_id: Mapped[str]=mapped_column(ForeignKey("projects.id",ondelete="CASCADE"),index=True)
    name: Mapped[str]=mapped_column(String(240))
    description: Mapped[str|None]=mapped_column(Text)

class Item(Base):
    __tablename__="items"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    project_id: Mapped[str]=mapped_column(ForeignKey("projects.id",ondelete="CASCADE"),index=True)
    name: Mapped[str]=mapped_column(String(240))
    description: Mapped[str|None]=mapped_column(Text)
    unique_item: Mapped[bool]=mapped_column(Boolean,default=False)

class Ability(Base):
    __tablename__="abilities"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    project_id: Mapped[str]=mapped_column(ForeignKey("projects.id",ondelete="CASCADE"),index=True)
    name: Mapped[str]=mapped_column(String(240))
    ability_type: Mapped[str|None]=mapped_column(String(64))
    can_do: Mapped[str|None]=mapped_column(Text)
    cannot_do: Mapped[str|None]=mapped_column(Text)
    limits: Mapped[str|None]=mapped_column(Text)
    cost: Mapped[str|None]=mapped_column(Text)
    conditions: Mapped[str|None]=mapped_column(Text)
    counters: Mapped[str|None]=mapped_column(Text)

class Relationship(Base):
    __tablename__="relationships"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    project_id: Mapped[str]=mapped_column(ForeignKey("projects.id",ondelete="CASCADE"),index=True)
    source_character_id: Mapped[str]=mapped_column(ForeignKey("characters.id",ondelete="CASCADE"),index=True)
    target_character_id: Mapped[str]=mapped_column(ForeignKey("characters.id",ondelete="CASCADE"),index=True)
    relationship_type: Mapped[str]=mapped_column(String(64))
    notes: Mapped[str|None]=mapped_column(Text)
    importance: Mapped[int|None]=mapped_column(Integer)
    sort_order: Mapped[int]=mapped_column(Integer,default=0)

class Alias(Base):
    __tablename__="aliases"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    project_id: Mapped[str]=mapped_column(ForeignKey("projects.id",ondelete="CASCADE"),index=True)
    character_id: Mapped[str]=mapped_column(ForeignKey("characters.id",ondelete="CASCADE"),index=True)
    alias: Mapped[str]=mapped_column(String(240))
    notes: Mapped[str|None]=mapped_column(Text)

class CharacterArc(Base):
    __tablename__="character_arcs"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    project_id: Mapped[str]=mapped_column(ForeignKey("projects.id",ondelete="CASCADE"),index=True)
    character_id: Mapped[str]=mapped_column(ForeignKey("characters.id",ondelete="CASCADE"),index=True)
    title: Mapped[str]=mapped_column(String(240))
    status: Mapped[str]=mapped_column(String(32),default="planned")
    opening_state: Mapped[str|None]=mapped_column(Text)
    target_state: Mapped[str|None]=mapped_column(Text)

class StyleProfile(Base):
    __tablename__="style_profiles"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    project_id: Mapped[str]=mapped_column(ForeignKey("projects.id",ondelete="CASCADE"),index=True)
    name: Mapped[str]=mapped_column(String(240))
    scope_type: Mapped[str]=mapped_column(String(32),default="global")
    scope_id: Mapped[str|None]=mapped_column(String(36),index=True)
    priority: Mapped[int]=mapped_column(Integer,default=0)
    active: Mapped[bool]=mapped_column(Boolean,default=True)
    instructions: Mapped[str|None]=mapped_column(Text)

class StyleSample(Base):
    __tablename__="style_samples"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    project_id: Mapped[str]=mapped_column(ForeignKey("projects.id",ondelete="CASCADE"),index=True)
    style_profile_id: Mapped[str]=mapped_column(ForeignKey("style_profiles.id",ondelete="CASCADE"),index=True)
    sample_type: Mapped[str]=mapped_column(String(64),default="general")
    title: Mapped[str|None]=mapped_column(String(240))
    text: Mapped[str]=mapped_column(Text)
