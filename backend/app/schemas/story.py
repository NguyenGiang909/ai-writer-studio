
from pydantic import BaseModel, ConfigDict, Field
class ORMModel(BaseModel): model_config=ConfigDict(from_attributes=True)

class CharacterCreate(BaseModel):
    name:str=Field(min_length=1,max_length=240); role:str|None=None; summary:str|None=None; voice_notes:str|None=None
class CharacterPatch(BaseModel):
    name:str|None=None; role:str|None=None; summary:str|None=None; voice_notes:str|None=None; status:str|None=None
    importance:int|None=None; sort_order:int|None=None
class CharacterOut(ORMModel):
    id:str; project_id:str; name:str; role:str|None=None; summary:str|None=None; voice_notes:str|None=None; status:str

class NamedCreate(BaseModel):
    name:str=Field(min_length=1,max_length=240); description:str|None=None
class WorldEntityCreate(NamedCreate): entity_type:str="lore"
class LocationCreate(NamedCreate): parent_location_id:str|None=None
class ItemCreate(NamedCreate): unique_item:bool=False
class AbilityCreate(BaseModel):
    name:str; ability_type:str|None=None; can_do:str|None=None; cannot_do:str|None=None
    limits:str|None=None; cost:str|None=None; conditions:str|None=None; counters:str|None=None
class RelationshipCreate(BaseModel):
    source_character_id:str; target_character_id:str; relationship_type:str; notes:str|None=None
class RelationshipPatch(BaseModel):
    relationship_type:str|None=None; notes:str|None=None; importance:int|None=None; sort_order:int|None=None
class MoveRequest(BaseModel):
    direction:str="up"  # "up" | "down"
class ReorderRequest(BaseModel):
    ids:list[str]=[]
class AliasCreate(BaseModel):
    character_id:str; alias:str; notes:str|None=None
class CharacterArcCreate(BaseModel):
    character_id:str; title:str; status:str="planned"; opening_state:str|None=None; target_state:str|None=None
class StyleProfileCreate(BaseModel):
    name:str; scope_type:str="global"; scope_id:str|None=None; priority:int=0; active:bool=True; instructions:str|None=None
class StyleSampleCreate(BaseModel):
    style_profile_id:str; sample_type:str="general"; title:str|None=None; text:str

class GenericOut(ORMModel):
    id:str; project_id:str
