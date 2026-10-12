
import uuid
from sqlalchemy import String,Text,ForeignKey,Boolean
from sqlalchemy.orm import Mapped,mapped_column
from app.db.base import Base
def uid(): return str(uuid.uuid4())
class SuggestedChange(Base):
    __tablename__="suggested_changes"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); project_id:Mapped[str]=mapped_column(ForeignKey("projects.id",ondelete="CASCADE"),index=True)
    scene_id:Mapped[str|None]=mapped_column(ForeignKey("scenes.id",ondelete="SET NULL")); change_type:Mapped[str]=mapped_column(String(40)); payload_json:Mapped[str]=mapped_column(Text)
    status:Mapped[str]=mapped_column(String(20),default="pending"); auto_applied:Mapped[bool]=mapped_column(Boolean,default=False)

class AuditFinding(Base):
    """Kết quả AI soi chương (deep-check) — lưu lại để tác giả xem/xoá, không phải canon."""
    __tablename__="audit_findings"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    project_id:Mapped[str]=mapped_column(ForeignKey("projects.id",ondelete="CASCADE"),index=True)
    scope_type:Mapped[str]=mapped_column(String(32),default="chapter")   # chapter
    scope_id:Mapped[str]=mapped_column(String(36),index=True)
    issues_json:Mapped[str]=mapped_column(Text)  # [{code,severity,message,suggestion,scene_id?}]
    # open | dismissed — tác giả đánh "không phải lỗi"; dismiss_key (code+message
    # chuẩn hoá) để deep-check sau skip finding trùng motif chủ đích (mục tiêu #10)
    status:Mapped[str]=mapped_column(String(16),default="open")
    dismiss_key:Mapped[str|None]=mapped_column(String(120),index=True)
    created_at:Mapped[str]=mapped_column(String(40),default=lambda:__import__("datetime").datetime.utcnow().isoformat())

class AuditJob(Base):
    """Job nền cho deep-check — endpoint POST trả job_id ngay, client poll status.
    Trước đây deep-check chạy đồng bộ >4ph → vượt client-timeout, không ghi gì (C10)."""
    __tablename__="audit_jobs"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    project_id:Mapped[str]=mapped_column(ForeignKey("projects.id",ondelete="CASCADE"),index=True)
    scope_type:Mapped[str]=mapped_column(String(32),default="chapter")   # chapter | range
    scope_id:Mapped[str]=mapped_column(String(36))
    status:Mapped[str]=mapped_column(String(16),default="running")      # running|done|failed
    result_json:Mapped[str|None]=mapped_column(Text)
    error:Mapped[str|None]=mapped_column(String(1000))
    created_at:Mapped[str]=mapped_column(String(40),default=lambda:__import__("datetime").datetime.utcnow().isoformat())
    finished_at:Mapped[str|None]=mapped_column(String(40))
