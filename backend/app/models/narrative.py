
import uuid
from sqlalchemy import String,Text,ForeignKey,Integer
from sqlalchemy.orm import Mapped,mapped_column
from app.db.base import Base
def uid(): return str(uuid.uuid4())
class Thread(Base):
    __tablename__="threads"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); project_id:Mapped[str]=mapped_column(ForeignKey("projects.id",ondelete="CASCADE"),index=True)
    title:Mapped[str]=mapped_column(String(240)); thread_type:Mapped[str]=mapped_column(String(32),default="mystery"); status:Mapped[str]=mapped_column(String(24),default="OPEN")
    description:Mapped[str|None]=mapped_column(Text); planned_payoff_order:Mapped[int|None]=mapped_column(Integer)
class ThreadBeat(Base):
    __tablename__="thread_beats"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); project_id:Mapped[str]=mapped_column(ForeignKey("projects.id",ondelete="CASCADE"),index=True)
    thread_id:Mapped[str]=mapped_column(ForeignKey("threads.id",ondelete="CASCADE"),index=True); scene_id:Mapped[str|None]=mapped_column(ForeignKey("scenes.id",ondelete="SET NULL"))
    beat_type:Mapped[str]=mapped_column(String(24)); narrative_order:Mapped[int|None]=mapped_column(Integer); notes:Mapped[str|None]=mapped_column(Text)
class ThreadDependency(Base):
    __tablename__="thread_dependencies"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); project_id:Mapped[str]=mapped_column(ForeignKey("projects.id",ondelete="CASCADE"),index=True)
    thread_id:Mapped[str]=mapped_column(ForeignKey("threads.id",ondelete="CASCADE")); depends_on_thread_id:Mapped[str]=mapped_column(ForeignKey("threads.id",ondelete="CASCADE"))
