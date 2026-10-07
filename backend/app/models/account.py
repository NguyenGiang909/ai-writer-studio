
import uuid
from sqlalchemy import String,Text,ForeignKey,Boolean,Integer
from sqlalchemy.orm import Mapped,mapped_column
from app.db.base import Base
def uid(): return str(uuid.uuid4())
class ProviderCredential(Base):
    __tablename__="provider_credentials"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); user_id:Mapped[str]=mapped_column(String(36),index=True)
    provider:Mapped[str]=mapped_column(String(32)); encrypted_secret:Mapped[str]=mapped_column(Text); key_hint:Mapped[str]=mapped_column(String(16)); status:Mapped[str]=mapped_column(String(20),default="connected")
    base_url:Mapped[str|None]=mapped_column(String(300))
class ModelPreference(Base):
    __tablename__="model_preferences"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); user_id:Mapped[str]=mapped_column(String(36),index=True)
    project_id:Mapped[str|None]=mapped_column(ForeignKey("projects.id",ondelete="CASCADE"),index=True); task:Mapped[str]=mapped_column(String(32)); provider:Mapped[str]=mapped_column(String(32)); model:Mapped[str]=mapped_column(String(120))
class StoryBranch(Base):
    __tablename__="story_branches"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); project_id:Mapped[str]=mapped_column(ForeignKey("projects.id",ondelete="CASCADE"),index=True)
    name:Mapped[str]=mapped_column(String(240)); status:Mapped[str]=mapped_column(String(20),default="draft")
class BranchChange(Base):
    __tablename__="branch_changes"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); project_id:Mapped[str]=mapped_column(ForeignKey("projects.id",ondelete="CASCADE"),index=True)
    branch_id:Mapped[str]=mapped_column(ForeignKey("story_branches.id",ondelete="CASCADE"),index=True); change_type:Mapped[str]=mapped_column(String(32)); payload_json:Mapped[str]=mapped_column(Text)
    merged_decision_id:Mapped[str|None]=mapped_column(ForeignKey("author_decisions.id",ondelete="SET NULL"),index=True)
class UsageLog(Base):
    __tablename__="usage_logs"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); user_id:Mapped[str]=mapped_column(String(36),index=True)
    project_id:Mapped[str|None]=mapped_column(String(36),index=True); task:Mapped[str]=mapped_column(String(32),index=True)
    provider:Mapped[str]=mapped_column(String(32)); model:Mapped[str]=mapped_column(String(120))
    prompt_tokens:Mapped[int]=mapped_column(Integer,default=0); completion_tokens:Mapped[int]=mapped_column(Integer,default=0); total_tokens:Mapped[int]=mapped_column(Integer,default=0)
    created_at:Mapped[str]=mapped_column(String(32),default=lambda:__import__("datetime").datetime.utcnow().isoformat())
