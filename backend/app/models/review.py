
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
