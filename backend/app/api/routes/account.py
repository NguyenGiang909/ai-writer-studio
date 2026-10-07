
import json
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models import Project
from app.models.account import ProviderCredential,ModelPreference,StoryBranch,BranchChange,UsageLog
from app.models.truth import AuthorDecision
from app.services.credentials import encrypt_secret,key_hint,public_credential_view,resolve_model
from app.services.branch import validate_change,merge_contract
from app.schemas.extras import *
router=APIRouter()

DEV_USER="local-author"

async def project_ok(db,pid):
    if not await db.get(Project,pid): raise HTTPException(404,"project not found")
async def add(db,obj):
    db.add(obj); await db.commit(); await db.refresh(obj); return obj

# ---- Provider credentials (BYOK) ----
@router.post("/account/credentials")
async def connect_provider(p:CredentialCreate,db:AsyncSession=Depends(get_db)):
    obj=ProviderCredential(user_id=DEV_USER,provider=p.provider,
        encrypted_secret=encrypt_secret(p.secret),key_hint=key_hint(p.secret),status="connected",
        base_url=(p.base_url or "").strip() or None)
    await add(db,obj)
    return {"id":obj.id,**public_credential_view(obj.provider,obj.key_hint,obj.status,obj.base_url)}
@router.get("/account/credentials")
async def list_credentials(db:AsyncSession=Depends(get_db)):
    rows=(await db.scalars(select(ProviderCredential).where(ProviderCredential.user_id==DEV_USER))).all()
    return [{"id":c.id,**public_credential_view(c.provider,c.key_hint,c.status,c.base_url)} for c in rows]
_TEST_MODELS={"openai":"gpt-4o-mini","anthropic":"claude-haiku-4-5-20251001","gemini":"gemini-2.0-flash",
    "openrouter":"openai/gpt-4o-mini","deepseek":"deepseek-chat","kiraai":"deepseek-v4.1-flash"}
@router.post("/account/credentials/{cid}/test")
async def test_credential(cid:str,model:str|None=None,db:AsyncSession=Depends(get_db)):
    from app.ai.router import build_provider,ModelRequest
    obj=await db.get(ProviderCredential,cid)
    if not obj or obj.user_id!=DEV_USER: raise HTTPException(404,"credential not found")
    use=model or (await db.scalar(select(ModelPreference.model).where(
        ModelPreference.user_id==DEV_USER,ModelPreference.provider==obj.provider).limit(1))) \
        or _TEST_MODELS.get(obj.provider)
    if not use: raise HTTPException(400,f"cần model để thử — tạo model preference cho '{obj.provider}' trước")
    try:
        result=await build_provider(obj,use).complete(ModelRequest(task="chat",prompt="Reply with the word: OK"))
    except Exception as e:
        obj.status="error"; await db.commit()
        raise HTTPException(400,f"Kết nối thất bại ({use}): {type(e).__name__} {e}")
    obj.status="connected"; await db.commit()
    return {"ok":True,"model":result.model,"reply":(result.text or "")[:80]}
@router.delete("/account/credentials/{cid}")
async def disconnect_provider(cid:str,db:AsyncSession=Depends(get_db)):
    obj=await db.get(ProviderCredential,cid)
    if not obj: raise HTTPException(404,"credential not found")
    obj.status="revoked"; await db.commit()
    return {"id":obj.id,**public_credential_view(obj.provider,obj.key_hint,obj.status,obj.base_url)}

# ---- Model preferences ----
@router.post("/account/model-preferences")
async def set_preference(p:ModelPreferenceCreate,db:AsyncSession=Depends(get_db)):
    if p.project_id: await project_ok(db,p.project_id)
    return await add(db,ModelPreference(user_id=DEV_USER,**p.model_dump()))
@router.get("/account/model-preferences")
async def list_preferences(db:AsyncSession=Depends(get_db)):
    return list((await db.scalars(select(ModelPreference).where(ModelPreference.user_id==DEV_USER))).all())
@router.patch("/account/model-preferences/{pref_id}")
async def patch_preference(pref_id:str,p:ModelPreferencePatch,db:AsyncSession=Depends(get_db)):
    obj=await db.get(ModelPreference,pref_id)
    if not obj or obj.user_id!=DEV_USER: raise HTTPException(404,"preference not found")
    for k,v in p.model_dump(exclude_unset=True).items(): setattr(obj,k,v)
    await db.commit(); await db.refresh(obj); return obj
@router.delete("/account/model-preferences/{pref_id}")
async def delete_preference(pref_id:str,db:AsyncSession=Depends(get_db)):
    obj=await db.get(ModelPreference,pref_id)
    if not obj or obj.user_id!=DEV_USER: raise HTTPException(404,"preference not found")
    await db.delete(obj); await db.commit(); return {"deleted":pref_id}
@router.get("/account/model-preferences/resolve")
async def resolve(task:str,project_id:str|None=None,db:AsyncSession=Depends(get_db)):
    rows=list((await db.scalars(select(ModelPreference).where(
        ModelPreference.user_id==DEV_USER,ModelPreference.task==task))).all())
    proj=next((r for r in rows if project_id and r.project_id==project_id),None)
    account=next((r for r in rows if r.project_id is None),None)
    chosen=resolve_model(task,project_override=proj,account_default=account)
    if not chosen: raise HTTPException(404,"no model preference for task")
    return {"task":task,"provider":chosen.provider,"model":chosen.model,
            "source":"project" if chosen is proj else "account"}

# ---- Usage / token log ----
@router.get("/account/usage")
async def account_usage(limit:int=100,db:AsyncSession=Depends(get_db)):
    rows=list((await db.scalars(select(UsageLog).where(
        UsageLog.user_id==DEV_USER).order_by(UsageLog.created_at.desc())
        .limit(min(limit,500)))).all())
    by_task:dict={}
    for r in rows:
        t=by_task.setdefault(r.task,{"calls":0,"prompt_tokens":0,"completion_tokens":0,"total_tokens":0})
        t["calls"]+=1; t["prompt_tokens"]+=r.prompt_tokens
        t["completion_tokens"]+=r.completion_tokens; t["total_tokens"]+=r.total_tokens
    return {
        "rows":[{"id":r.id,"project_id":r.project_id,"task":r.task,"provider":r.provider,
                 "model":r.model,"prompt_tokens":r.prompt_tokens,
                 "completion_tokens":r.completion_tokens,"total_tokens":r.total_tokens,
                 "created_at":r.created_at} for r in rows],
        "by_task":by_task,
    }

# ---- What-if branches ----
@router.post("/projects/{pid}/branches")
async def create_branch(pid:str,p:BranchCreate,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid); return await add(db,StoryBranch(project_id=pid,**p.model_dump()))
@router.get("/projects/{pid}/branches")
async def list_branches(pid:str,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    return list((await db.scalars(select(StoryBranch).where(StoryBranch.project_id==pid).order_by(StoryBranch.name))).all())
@router.patch("/projects/{pid}/branches/{bid}")
async def patch_branch(pid:str,bid:str,p:BranchPatch,db:AsyncSession=Depends(get_db)):
    obj=await db.get(StoryBranch,bid)
    if not obj or obj.project_id!=pid: raise HTTPException(404,"branch not found")
    allowed={"draft","selected","merged","discarded"}
    if p.status and p.status not in allowed: raise HTTPException(400,"invalid branch status")
    for k,v in p.model_dump(exclude_unset=True).items(): setattr(obj,k,v)
    await db.commit(); await db.refresh(obj); return obj

@router.post("/projects/{pid}/branches/{bid}/changes")
async def create_change(pid:str,bid:str,p:BranchChangeCreate,db:AsyncSession=Depends(get_db)):
    br=await db.get(StoryBranch,bid)
    if not br or br.project_id!=pid: raise HTTPException(404,"branch not found")
    if br.status not in {"draft","selected"}: raise HTTPException(400,"branch is closed for changes")
    try: payload=validate_change(p.change_type,p.payload)
    except ValueError as e: raise HTTPException(400,str(e))
    return await add(db,BranchChange(project_id=pid,branch_id=bid,change_type=p.change_type,
                                     payload_json=json.dumps(payload)))
@router.get("/projects/{pid}/branches/{bid}/changes")
async def list_changes(pid:str,bid:str,db:AsyncSession=Depends(get_db)):
    br=await db.get(StoryBranch,bid)
    if not br or br.project_id!=pid: raise HTTPException(404,"branch not found")
    rows=(await db.scalars(select(BranchChange).where(BranchChange.branch_id==bid))).all()
    return [{"id":c.id,"branch_id":c.branch_id,"change_type":c.change_type,
             "payload":json.loads(c.payload_json),"merged_decision_id":c.merged_decision_id} for c in rows]

@router.post("/projects/{pid}/branches/{bid}/changes/{cid}/merge")
async def merge_change(pid:str,bid:str,cid:str,db:AsyncSession=Depends(get_db)):
    br=await db.get(StoryBranch,bid)
    if not br or br.project_id!=pid: raise HTTPException(404,"branch not found")
    ch=await db.get(BranchChange,cid)
    if not ch or ch.branch_id!=bid: raise HTTPException(404,"change not found")
    contract=merge_contract({"merged_decision_id":ch.merged_decision_id})
    if contract["idempotent"]:
        return {"change_id":ch.id,"decision_id":ch.merged_decision_id,"idempotent":True}
    payload=json.loads(ch.payload_json)
    decision=await add(db,AuthorDecision(project_id=pid,
        title=f"Branch merge: {br.name} / {ch.change_type}",
        decision_text=json.dumps({"branch_id":bid,"change_type":ch.change_type,"payload":payload}),
        status="active"))
    ch.merged_decision_id=decision.id; await db.commit()
    return {"change_id":ch.id,"decision_id":decision.id,"idempotent":False,
            "mutates_canon":False,"mutates_manuscript":False}
