
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models import Project
from app.models.discussion import DiscussionThread,DiscussionMessage,StylePreference
from app.models.memory import StorySummary
from app.models.story import StyleProfile
from app.ai.router import ModelRouter,ModelRequest
from app.ai.compose import build_story_prompt
from app.schemas.extras import *
router=APIRouter()

async def project_ok(db,pid):
    if not await db.get(Project,pid): raise HTTPException(404,"project not found")
async def scoped(db,cls,obj_id,pid,label):
    obj=await db.get(cls,obj_id)
    if not obj or getattr(obj,"project_id",None)!=pid: raise HTTPException(400,f"{label} outside project")
    return obj
async def add(db,obj):
    db.add(obj); await db.commit(); await db.refresh(obj); return obj

@router.post("/projects/{pid}/discussions")
async def create_thread(pid:str,p:DiscussionThreadCreate,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid); return await add(db,DiscussionThread(project_id=pid,**p.model_dump()))
@router.get("/projects/{pid}/discussions")
async def list_threads(pid:str,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    return list((await db.scalars(select(DiscussionThread).where(DiscussionThread.project_id==pid).order_by(DiscussionThread.title))).all())

@router.post("/projects/{pid}/discussions/{tid}/messages")
async def post_message(pid:str,tid:str,p:MessageCreate,db:AsyncSession=Depends(get_db)):
    await scoped(db,DiscussionThread,tid,pid,"discussion")
    return await add(db,DiscussionMessage(project_id=pid,thread_id=tid,author="author",content=p.content))
@router.get("/projects/{pid}/discussions/{tid}/messages")
async def list_messages(pid:str,tid:str,db:AsyncSession=Depends(get_db)):
    await scoped(db,DiscussionThread,tid,pid,"discussion")
    return list((await db.scalars(select(DiscussionMessage).where(DiscussionMessage.thread_id==tid).order_by(DiscussionMessage.created_at))).all())
@router.patch("/projects/{pid}/discussions/{tid}/messages/{mid}")
async def patch_message(pid:str,tid:str,mid:str,p:MessagePatch,db:AsyncSession=Depends(get_db)):
    await scoped(db,DiscussionThread,tid,pid,"discussion")
    obj=await db.get(DiscussionMessage,mid)
    if not obj or obj.thread_id!=tid: raise HTTPException(404,"message not found")
    for k,v in p.model_dump(exclude_unset=True).items(): setattr(obj,k,v)
    await db.commit(); await db.refresh(obj); return obj

ROLE_PERSONA={
    "brainstorm":"Vai trò: ĐỘNG NÃO — đưa nhiều hướng divergent, wild nhưng khả thi, mỗi ý một đoạn ngắn.",
    "plot_doctor":"Vai trò: BÁC SĨ CỐT TRUYỆN — chẩn đoán vấn đề mạch truyện, chỉ ra nguyên nhân gốc và đề xuất phương án chữa cụ thể.",
    "character_analyst":"Vai trò: PHÂN TÍCH NHÂN VẬT — mổ động cơ, arc, mâu thuẫn nội tâm, quan hệ; bám hồ sơ nhân vật đã cho.",
    "continuity_analyst":"Vai trò: PHÂN TÍCH LIÊN TỤC — soi mâu thuẫn canon/timeline/knowledge, dẫn chứng từ dữ kiện truyện.",
    "devils_advocate":"Vai trò: PHẢN BIỆN — cố tình phản bác ý tưởng của tác giả, tìm lỗ hổng và kịch bản xấu nhất.",
    "reader_simulation":"Vai trò: GIẢ LẬP ĐỘC GIẢ — phản ứng như độc giả lần đầu đọc: bất ngờ, đoán trước, hụt hẫng, cảm xúc.",
    "style":"Vai trò: BIÊN TẬP PHONG CÁCH — góp ý giọng văn, nhịp, cú pháp; giữ chất của tác giả.",
    "assistant":"Vai trò: TRỢ LÝ TÁC GIẢ — trả lời thực tế, bám ngữ cảnh phần việc tác giả đang làm.",
}

SUMMARY_EVERY=8

async def _thread_summary(db,pid,tid):
    return (await db.scalars(select(StorySummary).where(
        StorySummary.project_id==pid,StorySummary.scope_type=="discussion",
        StorySummary.scope_id==tid,StorySummary.stale==False))).first()

async def _maybe_summarize(db,pid,thread,msgs):
    if len(msgs)<SUMMARY_EVERY or len(msgs)%SUMMARY_EVERY: return
    lines="\n".join(f"{m.author}: {m.content}" for m in msgs)
    try:
        r=await ModelRouter(db).complete(ModelRequest(task="summarization",
            prompt=f"Tóm tắt cuộc thảo luận sáng tác sau — giữ quyết định đã chốt, ý tưởng chính và vấn đề còn mở. Tối đa 150 từ.\n\n{lines}",
            project_id=pid,
            system="Bạn là bộ tóm tắt cuộc thảo luận. Chỉ ghi lại nội dung đã bàn, không thêm ý mới."))
    except RuntimeError:
        return
    s=await _thread_summary(db,pid,thread.id)
    if s:
        s.summary=r.text; s.stale=False; s.narrative_end=len(msgs)
        await db.commit()
    else:
        db.add(StorySummary(project_id=pid,scope_type="discussion",scope_id=thread.id,
                            summary=r.text,narrative_end=len(msgs)))
        await db.commit()

@router.post("/projects/{pid}/discussions/{tid}/ai-reply")
async def ai_reply(pid:str,tid:str,p:AiReplyRequest|None=None,db:AsyncSession=Depends(get_db)):
    thread=await scoped(db,DiscussionThread,tid,pid,"discussion")
    msgs=list((await db.scalars(select(DiscussionMessage).where(DiscussionMessage.thread_id==tid).order_by(DiscussionMessage.created_at))).all())
    pinned=[m for m in msgs if m.pinned]
    recent=[m for m in msgs if not m.pinned][-16:]
    lines=[f"[Chủ đề thảo luận: {thread.title}]"]
    prior=await _thread_summary(db,pid,tid)
    if prior: lines.append(f"[Tóm tắt thảo luận đến tin #{prior.narrative_end or '?'} — vẫn còn hiệu lực]: {prior.summary}")
    for m in pinned: lines.append(f"📌 {m.author} (đã ghim — coi như quyết định giữ nguyên): {m.content}")
    lines+= [f"{m.author}: {m.content}" for m in recent]
    raw="\n".join(lines)
    if p and p.context: raw=f"[Bối cảnh tác giả đang làm việc: {p.context}]\n"+raw
    system,prompt,_=await build_story_prompt(db,pid,"discussion",raw,p.scene_id if p else None)
    persona=ROLE_PERSONA.get(thread.role or "")
    if persona: system=(system or "")+"\n"+persona
    try:
        result=await ModelRouter(db).complete(
            ModelRequest(task="discussion",prompt=prompt,project_id=pid,system=system))
    except RuntimeError as e:
        raise HTTPException(503,str(e))
    reply=await add(db,DiscussionMessage(project_id=pid,thread_id=tid,author="ai",content=result.text))
    msgs.append(reply)
    await _maybe_summarize(db,pid,thread,msgs)
    return reply

@router.post("/projects/{pid}/style-preferences")
async def create_pref(pid:str,p:StylePreferenceCreate,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid); await scoped(db,StyleProfile,p.style_profile_id,pid,"style profile")
    return await add(db,StylePreference(project_id=pid,**p.model_dump()))
@router.get("/projects/{pid}/style-preferences")
async def list_prefs(pid:str,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    return list((await db.scalars(select(StylePreference).where(StylePreference.project_id==pid))).all())
