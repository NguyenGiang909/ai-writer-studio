
import uuid
from sqlalchemy import String,Text,ForeignKey,Integer,Boolean
from sqlalchemy.orm import Mapped,mapped_column
from app.db.base import Base
def uid(): return str(uuid.uuid4())
class StorySummary(Base):
    __tablename__="story_summaries"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); project_id:Mapped[str]=mapped_column(ForeignKey("projects.id",ondelete="CASCADE"),index=True)
    scope_type:Mapped[str]=mapped_column(String(16)); scope_id:Mapped[str]=mapped_column(String(36),index=True); summary:Mapped[str]=mapped_column(Text)
    stale:Mapped[bool]=mapped_column(Boolean,default=False); narrative_end:Mapped[int|None]=mapped_column(Integer,index=True)
class RetconProposal(Base):
    __tablename__="retcon_proposals"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); project_id:Mapped[str]=mapped_column(ForeignKey("projects.id",ondelete="CASCADE"),index=True)
    target_type:Mapped[str]=mapped_column(String(24)); target_id:Mapped[str]=mapped_column(String(36)); proposal:Mapped[str]=mapped_column(Text); impact_snapshot_json:Mapped[str]=mapped_column(Text)
class AiTurn(Base):
    __tablename__="ai_turns"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); project_id:Mapped[str]=mapped_column(ForeignKey("projects.id",ondelete="CASCADE"),index=True)
    scope_id:Mapped[str]=mapped_column(String(36),index=True)
    task:Mapped[str]=mapped_column(String(32),index=True); prompt_excerpt:Mapped[str]=mapped_column(Text,default=""); reply_text:Mapped[str]=mapped_column(Text,default="")
    provider:Mapped[str]=mapped_column(String(32),default=""); model:Mapped[str]=mapped_column(String(120),default="")
    created_at:Mapped[str]=mapped_column(String(32),default=lambda:__import__("datetime").datetime.utcnow().isoformat(),index=True)
