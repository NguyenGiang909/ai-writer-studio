import uuid
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, Integer, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


def uid() -> str:
    return str(uuid.uuid4())


class AuthoringRun(Base):
    """Pipeline AI tạo truyện — toàn bộ tiến độ nằm ở đây, engine stateless."""
    __tablename__ = "authoring_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    prompt: Mapped[str] = mapped_column(Text)
    phase: Mapped[str] = mapped_column(String(24), default="premise")
    status: Mapped[str] = mapped_column(String(24), default="running")
    stage_payload_json: Mapped[str | None] = mapped_column(Text)
    cursor_json: Mapped[str | None] = mapped_column(Text)
    # goal do tác giả đặt — định hướng generate, không phải cap cứng
    target_chapters: Mapped[int | None] = mapped_column(Integer)
    words_per_scene: Mapped[int | None] = mapped_column(Integer)
    # safe = call nhỏ theo đơn vị (mặc định, chống timeout); fast = call gộp (API mạnh)
    call_mode: Mapped[str] = mapped_column(String(16), default="safe")
    # batch = lên hết khung rồi viết; rolling = sóng theo hồi (hồi sau học văn hồi trước)
    flow: Mapped[str] = mapped_column(String(16), default="rolling")
    # cờ 1-lần: hồi đang chạy xong thì dừng checkpoint thay vì sang hồi kế
    pause_after_wave: Mapped[bool] = mapped_column(Boolean, default=False)
    # end = viết hết (chạy liền); waves = theo tiến độ (dừng sau mỗi hồi chờ goal)
    goal_mode: Mapped[str] = mapped_column(String(16), default="end")
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class AuthoringStep(Base):
    """Audit log từng bước engine — replay/debug được."""
    __tablename__ = "authoring_steps"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    run_id: Mapped[str] = mapped_column(ForeignKey("authoring_runs.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    step_key: Mapped[str] = mapped_column(String(120), index=True)
    status: Mapped[str] = mapped_column(String(24), default="pending")
    input_json: Mapped[str | None] = mapped_column(Text)
    output_json: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)


class EntityProvenance(Base):
    """Nguồn gốc entity — đánh dấu ai/human tạo, không cần thêm cột vào 13 bảng."""
    __tablename__ = "entity_provenance"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    run_id: Mapped[str | None] = mapped_column(String(36), index=True)
    origin: Mapped[str] = mapped_column(String(16), default="ai")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
