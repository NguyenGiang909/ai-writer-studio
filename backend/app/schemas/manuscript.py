import json
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, computed_field

class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=240)
    description: str | None = None
class ProjectPatch(BaseModel):
    name: str | None = None; description: str | None = None
class ProjectOut(ORMModel):
    id: str; name: str; description: str | None = None

class VolumeCreate(BaseModel):
    title: str; order_index: int = 0
class VolumeOut(ORMModel):
    id: str; project_id: str; title: str; order_index: int

class ArcCreate(BaseModel):
    title: str; order_index: int = 0; volume_id: str | None = None
class ArcOut(ORMModel):
    id: str; project_id: str; title: str; order_index: int; volume_id: str | None = None

class ChapterCreate(BaseModel):
    title: str; order_index: int = 0; volume_id: str | None = None; arc_id: str | None = None
class ChapterPatch(BaseModel):
    title: str | None = None; order_index: int | None = None
    status: str | None = None; arc_id: str | None = None
    cast_json: str | None = None
class ChapterInsert(BaseModel):
    """Chèn chương vào trước order_index — backend dời trục narrative đồng bộ."""
    title: str; order_index: int
    volume_id: str | None = None; arc_id: str | None = None
class ChapterOut(ORMModel):
    id: str; project_id: str; title: str; order_index: int; status: str
    volume_id: str | None = None; arc_id: str | None = None
    cast_json: str | None = None

class SceneCreate(BaseModel):
    title: str | None = None
    order_index: int = 0
    prose: str = ""
    skeleton: str | None = None
    pov_character_id: str | None = None
    scene_type: str | None = None
    story_time: int | None = None
    narrative_order: int | None = None
    location_id: str | None = None
class SceneBatchItem(BaseModel):
    title: str | None = None
    skeleton: str | None = None
    scene_type: str | None = None
    pov_character_id: str | None = None
    location_id: str | None = None
class SceneBatchCreate(BaseModel):
    scenes: list[SceneBatchItem] = Field(min_length=1, max_length=30)
class ScenePatch(BaseModel):
    title: str | None = None
    prose: str | None = None
    skeleton: str | None = None
    pov_character_id: str | None = None
    scene_type: str | None = None
    brief: dict | None = None
    story_time: int | None = None
    narrative_order: int | None = None
    location_id: str | None = None
class SceneOut(ORMModel):
    id: str; project_id: str; chapter_id: str; title: str | None
    order_index: int; prose: str; skeleton: str | None = None
    pov_character_id: str | None = None; scene_type: str | None = None
    story_time: int | None = None; narrative_order: int | None = None
    location_id: str | None = None
    brief_json: str | None = Field(default=None, exclude=True)

    @computed_field
    @property
    def brief(self) -> dict | None:
        return json.loads(self.brief_json) if self.brief_json else None

class SceneVersionOut(ORMModel):
    id: str; scene_id: str; title: str | None
    created_at: datetime | None = None
    chars: int = 0
    excerpt: str = ""

class SceneVersionFullOut(SceneVersionOut):
    prose: str = ""
