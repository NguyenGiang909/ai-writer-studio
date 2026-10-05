import uuid
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, Integer, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

def uid() -> str:
    return str(uuid.uuid4())

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class Volume(Base):
    __tablename__ = "volumes"
    __table_args__ = (UniqueConstraint("project_id", "order_index"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(240))
    order_index: Mapped[int] = mapped_column(Integer, default=0)

class Arc(Base):
    __tablename__ = "arcs"
    __table_args__ = (UniqueConstraint("project_id", "order_index"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    volume_id: Mapped[str | None] = mapped_column(ForeignKey("volumes.id", ondelete="SET NULL"), index=True)
    title: Mapped[str] = mapped_column(String(240))
    order_index: Mapped[int] = mapped_column(Integer, default=0)

class Chapter(Base):
    __tablename__ = "chapters"
    __table_args__ = (UniqueConstraint("project_id", "order_index"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    volume_id: Mapped[str | None] = mapped_column(ForeignKey("volumes.id", ondelete="SET NULL"), index=True)
    arc_id: Mapped[str | None] = mapped_column(ForeignKey("arcs.id", ondelete="SET NULL"), index=True)
    title: Mapped[str] = mapped_column(String(240))
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="draft")

class Scene(Base):
    __tablename__ = "scenes"
    __table_args__ = (UniqueConstraint("chapter_id", "order_index"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    chapter_id: Mapped[str] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), index=True)
    title: Mapped[str | None] = mapped_column(String(240))
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    prose: Mapped[str] = mapped_column(Text, default="")
    skeleton: Mapped[str | None] = mapped_column(Text)
    brief_json: Mapped[str | None] = mapped_column(Text)
    pov_character_id: Mapped[str | None] = mapped_column(String(36))
    scene_type: Mapped[str | None] = mapped_column(String(64))
    story_time: Mapped[int | None] = mapped_column(Integer)
    narrative_order: Mapped[int | None] = mapped_column(Integer)
    location_id: Mapped[str | None] = mapped_column(String(36))

class SceneVersion(Base):
    """Snapshot prose của cảnh — lưu bản cũ trước khi ghi đè (patch/restore)."""
    __tablename__ = "scene_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    scene_id: Mapped[str] = mapped_column(ForeignKey("scenes.id", ondelete="CASCADE"), index=True)
    title: Mapped[str | None] = mapped_column(String(240))
    prose: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
