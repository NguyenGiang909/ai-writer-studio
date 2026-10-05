
import uuid
from datetime import datetime
from sqlalchemy import String,Text,ForeignKey,Boolean,DateTime
from sqlalchemy.orm import Mapped,mapped_column
from app.db.base import Base
def uid(): return str(uuid.uuid4())
class DiscussionThread(Base):
    __tablename__="discussion_threads"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); project_id:Mapped[str]=mapped_column(ForeignKey("projects.id",ondelete="CASCADE"),index=True)
    title:Mapped[str]=mapped_column(String(240)); role:Mapped[str]=mapped_column(String(40),default="brainstorm"); summary:Mapped[str|None]=mapped_column(Text)
class DiscussionMessage(Base):
    __tablename__="discussion_messages"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); project_id:Mapped[str]=mapped_column(ForeignKey("projects.id",ondelete="CASCADE"),index=True)
    thread_id:Mapped[str]=mapped_column(ForeignKey("discussion_threads.id",ondelete="CASCADE"),index=True); author:Mapped[str]=mapped_column(String(16)); content:Mapped[str]=mapped_column(Text); pinned:Mapped[bool]=mapped_column(Boolean,default=False)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,nullable=True)
class StylePreference(Base):
    __tablename__="style_preferences"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); project_id:Mapped[str]=mapped_column(ForeignKey("projects.id",ondelete="CASCADE"),index=True)
    style_profile_id:Mapped[str]=mapped_column(ForeignKey("style_profiles.id",ondelete="CASCADE"),index=True); preference_type:Mapped[str]=mapped_column(String(16)); pattern:Mapped[str]=mapped_column(Text); explicit_author_feedback:Mapped[bool]=mapped_column(Boolean,default=True)
