
from pydantic import BaseModel, ConfigDict, Field

class ORMModel(BaseModel): model_config=ConfigDict(from_attributes=True)

# ---- truth ----
class CanonFactCreate(BaseModel):
    subject_type:str; subject_id:str|None=None
    predicate:str=Field(min_length=1,max_length=120); value_text:str
    truth_status:str="CANON"; locked:bool=False
    valid_from:int|None=None; valid_to:int|None=None; source_scene_id:str|None=None
class CanonFactPatch(BaseModel):
    truth_status:str|None=None; locked:bool|None=None
    value_text:str|None=None; valid_to:int|None=None
class AuthorDecisionCreate(BaseModel):
    title:str=Field(min_length=1,max_length=240); decision_text:str; status:str="active"
    rationale:str|None=None; rejected:list|None=None
class AuthorDecisionPatch(BaseModel):
    title:str|None=None; decision_text:str|None=None; status:str|None=None
    rationale:str|None=None; rejected:list|None=None
class StoryEventCreate(BaseModel):
    scene_id:str|None=None; event_type:str; summary:str
    story_time:int|None=None; narrative_order:int|None=None; location_id:str|None=None
class StoryStateCreate(BaseModel):
    entity_type:str; entity_id:str; key:str; value_text:str
    story_time:int|None=None; narrative_order:int|None=None; source_event_id:str|None=None
class KnowledgeStateCreate(BaseModel):
    knower_type:str="character"; knower_id:str|None=None; fact_id:str
    state:str="KNOWS"; disclosure_level:int=100; known_aspects:str|None=None
    acquired_story_time:int|None=None; acquired_narrative_order:int|None=None
class SecretCreate(BaseModel):
    fact_id:str; title:str=Field(min_length=1,max_length=240); status:str="active"

# ---- narrative ----
class ThreadCreate(BaseModel):
    title:str=Field(min_length=1,max_length=240); thread_type:str="mystery"
    status:str="OPEN"; description:str|None=None; planned_payoff_order:int|None=None
class ThreadPatch(BaseModel):
    title:str|None=None; status:str|None=None
    description:str|None=None; planned_payoff_order:int|None=None
class ThreadBeatCreate(BaseModel):
    scene_id:str|None=None; beat_type:str; narrative_order:int|None=None; notes:str|None=None
class ThreadDependencyCreate(BaseModel):
    thread_id:str; depends_on_thread_id:str

# ---- discussion ----
class DiscussionThreadCreate(BaseModel):
    title:str=Field(min_length=1,max_length=240); role:str="brainstorm"
class MessageCreate(BaseModel):
    content:str=Field(min_length=1)
class AiReplyRequest(BaseModel):
    context:str|None=None; scene_id:str|None=None
class MessagePatch(BaseModel):
    pinned:bool|None=None
class StylePreferenceCreate(BaseModel):
    style_profile_id:str; preference_type:str; pattern:str; explicit_author_feedback:bool=True

# ---- review ----
class SuggestionCreate(BaseModel):
    scene_id:str|None=None; change_type:str; payload:dict=Field(default_factory=dict)

# ---- memory ----
class SummaryCreate(BaseModel):
    scope_type:str; scope_id:str; summary:str; narrative_end:int|None=None
class SummaryPatch(BaseModel):
    summary:str|None=None; stale:bool|None=None
class RetconCreate(BaseModel):
    target_type:str; target_id:str; proposal:str

# ---- account ----
class CredentialCreate(BaseModel):
    provider:str=Field(min_length=1,max_length=32); secret:str=Field(min_length=1)
    base_url:str|None=Field(default=None,max_length=300)
class ModelPreferenceCreate(BaseModel):
    task:str; provider:str; model:str; project_id:str|None=None
class ModelPreferencePatch(BaseModel):
    task:str|None=None; provider:str|None=None; model:str|None=None; project_id:str|None=None
class BranchCreate(BaseModel):
    name:str=Field(min_length=1,max_length=240)
class BranchPatch(BaseModel):
    status:str|None=None
class BranchChangeCreate(BaseModel):
    change_type:str; payload:dict=Field(default_factory=dict)

# ---- ai ----
class ContextItemIn(BaseModel):
    bucket:str; text:str; priority:int=0; source:str="api"; estimated_tokens:int=0
class ContextPreviewRequest(BaseModel):
    items:list[ContextItemIn]; budget:int=8000
class ParseBriefRequest(BaseModel):
    text:str; target_words:int=2000
class WordBudgetRequest(BaseModel):
    target:int; scene_count:int
class CompleteRequest(BaseModel):
    task:str; prompt:str; model:str|None=None; scene_id:str|None=None; chapter_id:str|None=None
class ContextManifestRequest(BaseModel):
    task:str|None=None; scene_id:str|None=None; chapter_id:str|None=None
class PruneTurnsRequest(BaseModel):
    keep:int=Field(ge=0,default=50)
class SummaryGenerateRequest(BaseModel):
    scope_type:str; scope_id:str
class CharacterAssistRequest(BaseModel):
    name:str=Field(min_length=1,max_length=240); hint:str|None=None
class LineDiffRequest(BaseModel):
    original:str; replacement:str
class AuthoringStartRequest(BaseModel):
    # prompt optional — dự án đã có khung thì AI tự tiếp nhận, prompt chỉ là định hướng
    prompt:str|None=Field(default=None,max_length=4000); name:str|None=None
    target_chapters:int|None=Field(default=None,ge=1,le=500)
    words_per_scene:int|None=Field(default=None,ge=200,le=5000)
    # safe = call nhỏ theo đơn vị (mặc định); fast = call gộp lớn khi API mạnh
    call_mode:str|None=Field(default="safe",pattern="^(safe|fast)$")
    # rolling = sóng theo hồi, hồi sau học văn đã viết (mặc định cho run mới);
    # batch = lên toàn bộ khung trước rồi viết
    flow:str|None=Field(default="rolling",pattern="^(batch|rolling)$")
    # end = viết hết: chạy liền tới mục tiêu/hết sóng (mặc định);
    # waves = theo tiến độ: dừng checkpoint sau MỖI hồi để tác giả đặt goal dần
    goal_mode:str|None=Field(default="end",pattern="^(end|waves)$")
class AuthoringRegenerateRequest(BaseModel):
    hint:str|None=Field(default=None,max_length=2000)
class AuthoringApproveRequest(BaseModel):
    # định hướng cho HỒI SAU (rolling + goal_mode=waves) — "tạo goal dần"
    hint:str|None=Field(default=None,max_length=2000)
