
import asyncio,json,re
from fastapi import APIRouter,Depends,HTTPException,Body
from sqlalchemy import select,delete,func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models import Project,Chapter,Scene,Arc
from app.models.review import SuggestedChange,AuditFinding
from app.models.story import Character,Alias,Location,Ability,Item,Relationship
from app.models.narrative import Thread,ThreadBeat
from app.models.truth import KnowledgeState,StoryState,CanonFact,StoryEvent
from app.models.memory import AiTurn
from app.services.state import states_at,effective_at
from app.services.constraints import canonical_state_key,build_constraints
from app.ai.context import ContextBuilder,ContextItem
from app.ai.router import ModelRouter,ModelRequest
from app.ai.compose import build_story_prompt
from app.ai.writer import parse_author_brief,allocate_word_budget,line_diff
from app.services.continuity import (restricted_appearance,location_conflict,ability_locked,
    item_owner_mismatch,relationship_ended,stale_thread,dedupe,Issue,
    canon_conflict,state_conflict,state_regression,unplanned_location,
    phase_leak,missing_extraction,scene_no_narr)
from app.schemas.extras import *
router=APIRouter()

async def project_ok(db,pid):
    if not await db.get(Project,pid): raise HTTPException(404,"project not found")

@router.post("/projects/{pid}/context/preview")
async def context_preview(pid:str,p:ContextPreviewRequest,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    items=[ContextItem(bucket=i.bucket,text=i.text,priority=i.priority,source=i.source,
                       estimated_tokens=i.estimated_tokens) for i in p.items]
    text,manifest=ContextBuilder().build(items,budget=p.budget)
    return {"text":text,"manifest":{"included":manifest.included,"omitted":manifest.omitted,
            "total_estimated_tokens":manifest.total_estimated_tokens}}

@router.post("/writer/parse-brief")
async def parse_brief(p:ParseBriefRequest):
    plan=parse_author_brief(p.text,p.target_words)
    return {"beats":plan.beats,"constraints":plan.constraints,
            "target_words":plan.target_words,"plan_hash":plan.plan_hash}
@router.post("/writer/word-budget")
async def word_budget(p:WordBudgetRequest):
    try: return {"allocation":allocate_word_budget(p.target,p.scene_count)}
    except ValueError: raise HTTPException(400,"scene_count must be >= 1")
@router.post("/writer/line-diff")
async def diff(p:LineDiffRequest):
    return {"diff":line_diff(p.original,p.replacement)}

@router.post("/projects/{pid}/ai/complete")
async def complete(pid:str,p:CompleteRequest,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    system,prompt,manifest=await build_story_prompt(db,pid,p.task,p.prompt,p.scene_id,getattr(p,"chapter_id",None))
    try:
        result=await ModelRouter(db).complete(
            ModelRequest(task=p.task,prompt=prompt,model=p.model,project_id=pid,system=system))
    except RuntimeError as e: raise HTTPException(503,str(e))
    db.add(AiTurn(project_id=pid,scope_id=p.scene_id or pid,task=p.task,
                  prompt_excerpt=p.prompt[:4000],reply_text=(result.text or "")[:4000],
                  provider=result.provider or "",model=result.model or ""))
    await db.commit()
    issues=[]
    if p.task in {"writing","expand","scene_expand","revision"} and p.scene_id and result.text:
        sc=await db.get(Scene,p.scene_id)
        if sc:
            st_t=sc.story_time if sc.story_time is not None else sc.narrative_order
            chars={c.id:c for c in (await db.scalars(select(Character).where(Character.project_id==pid))).all()}
            aliases=list((await db.scalars(select(Alias).where(Alias.project_id==pid))).all())
            life=[s for s in await states_at(db,pid,story_time=st_t,entity_type="character")
                  if canonical_state_key(s.key)=="lifecycle"]
            for st in life:
                c=chars.get(st.entity_id)
                if not c or not c.name: continue
                names=[c.name]+[a.alias for a in aliases if a.character_id==c.id and a.alias]
                names+=[w for w in re.split(r"\s+",c.name) if len(w)>=4]
                hit=any(re.search(r"\b"+re.escape(n)+r"\b",result.text,
                                  re.IGNORECASE if " " in n else 0) for n in dict.fromkeys(names))
                if not hit: continue
                iss=restricted_appearance(c.name,st.value_text,sc.scene_type,st.story_time,st_t,sc.id,c.id)
                if iss: issues.append({"code":iss.code,"severity":iss.severity,"message":iss.message})
    return {"reply":result.text,"provider":result.provider,"model":result.model,
            "usage":result.usage,"context":manifest,"issues":issues}

@router.post("/projects/{pid}/ai/context-manifest")
async def context_manifest(pid:str,p:ContextManifestRequest,db:AsyncSession=Depends(get_db)):
    """Preview what context the AI would receive — no model call, free."""
    await project_ok(db,pid)
    _sys,_prompt,manifest=await build_story_prompt(db,pid,p.task or "writing","",p.scene_id,getattr(p,"chapter_id",None))
    return {"manifest":manifest}

@router.post("/projects/{pid}/scenes/{sid}/extract-suggestions")
async def extract_suggestions(pid:str,sid:str,db:AsyncSession=Depends(get_db)):
    """F2 after-write extraction: read scene prose → suggestions into Review queue."""
    await project_ok(db,pid)
    sc=await db.get(Scene,sid)
    if not sc or sc.project_id!=pid: raise HTTPException(404,"scene not found in project")
    if not (sc.prose or "").strip(): raise HTTPException(400,"scene has no prose to extract")
    system,prompt,_=await build_story_prompt(db,pid,"extraction",sc.prose.strip()[-8000:],sid)
    try:
        result=await ModelRouter(db).complete(
            ModelRequest(task="extraction",prompt=prompt,project_id=pid,system=system))
    except RuntimeError as e: raise HTTPException(503,str(e))
    data=_parse_json(result.text)
    created=[]
    for f in (data.get("canon_facts") or [])[:20]:
        created.append(await _mk(db,pid,sid,"canon_fact",f))
    for e in (data.get("events") or [])[:20]:
        created.append(await _mk(db,pid,sid,"story_event",e))
    for e in (data.get("entities") or [])[:20]:
        created.append(await _mk(db,pid,sid,"entity",e))
    for s_ in (data.get("story_states") or [])[:20]:
        created.append(await _mk(db,pid,sid,"story_state",s_))
    for k in (data.get("knowledge") or [])[:20]:
        created.append(await _mk(db,pid,sid,"knowledge_state",k))
    for t in (data.get("thread_touches") or [])[:20]:
        created.append(await _mk(db,pid,sid,"thread_beat",t))
    return {"created":len(created),"provider":result.provider,
            "items":[{"change_type":s.change_type,"payload":json.loads(s.payload_json)} for s in created]}

@router.post("/projects/{pid}/characters/assist")
async def character_assist(pid:str,p:CharacterAssistRequest,db:AsyncSession=Depends(get_db)):
    """Quét prose tìm tên nhân vật → AI đề xuất hồ sơ nháp (JSON). Không ghi DB."""
    await project_ok(db,pid)
    name=p.name.strip()
    if not name: raise HTTPException(400,"name required")
    excerpts=[]
    for sc in (await db.scalars(select(Scene).where(Scene.project_id==pid))).all():
        prose=sc.prose or ""
        m=re.search(re.escape(name),prose,re.IGNORECASE)
        if not m: continue
        a,b=max(0,m.start()-260),min(len(prose),m.end()+260)
        excerpts.append(f"[{sc.title or 'Cảnh'}] …{prose[a:b].strip()}…")
        if len(excerpts)>=8: break
    existing=None
    for c in (await db.scalars(select(Character).where(Character.project_id==pid))).all():
        if (c.name or "").strip().lower()==name.lower(): existing=c; break
    parts=[f"=== NHÂN VẬT ===\nTên: {name}"]
    if existing:
        parts.append("Hồ sơ hiện có (bổ sung, không lặp lại):\n"+json.dumps(
            {"role":existing.role,"summary":existing.summary,
             "voice_notes":existing.voice_notes,"status":existing.status},ensure_ascii=False))
    if p.hint: parts.append(f"Gợi ý của tác giả: {p.hint.strip()}")
    if excerpts:
        parts.append(f"=== ĐOẠN TRÍCH BẢN THẢO ({len(excerpts)}) ===\n"+"\n\n".join(excerpts))
    parts.append("=== YÊU CẦU ===\nTrả về JSON hồ sơ nháp theo đúng khóa trong system prompt.")
    system,prompt,_=await build_story_prompt(db,pid,"character_profile","\n\n".join(parts))
    try:
        result=await ModelRouter(db).complete(
            ModelRequest(task="character_profile",prompt=prompt,project_id=pid,system=system))
    except RuntimeError as e: raise HTTPException(503,str(e))
    db.add(AiTurn(project_id=pid,scope_id=existing.id if existing else pid,
                  task="character_profile",prompt_excerpt=prompt[:1500],
                  reply_text=(result.text or "")[:4000],
                  provider=result.provider or "",model=result.model or ""))
    await db.commit()
    data=_parse_json(result.text)
    draft={"name":name,"role":data.get("role"),"summary":data.get("summary"),
           "voice_notes":data.get("voice_notes"),
           "status":data.get("status") or "active",
           "aliases":[a.strip() for a in (data.get("aliases") or [])
                      if isinstance(a,str) and a.strip()][:6]}
    return {"draft":draft,"excerpts_used":len(excerpts),
            "existing_id":existing.id if existing else None,
            "provider":result.provider,"model":result.model}

def _parse_json(text:str)->dict:
    t=(text or "").strip()
    if "```" in t:
        t=t.split("```",2)[1]
        if t.startswith("json"): t=t[4:]
        t=t.split("```")[0]
    try: return json.loads(t)
    except Exception:
        a,b=t.find("{"),t.rfind("}")
        try: return json.loads(t[a:b+1]) if a>=0 and b>a else {}
        except Exception: return {}

async def _mk(db,pid,sid,change_type,payload:dict):
    obj=SuggestedChange(project_id=pid,scene_id=sid,change_type=change_type,
        payload_json=json.dumps(payload or {},ensure_ascii=False),
        status="pending",auto_applied=False)
    db.add(obj); await db.commit(); await db.refresh(obj); return obj

@router.get("/projects/{pid}/continuity/check")
async def continuity_check(pid:str,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    issues=[]
    chapters={c.id:c for c in (await db.scalars(select(Chapter).where(Chapter.project_id==pid))).all()}
    scenes=list((await db.scalars(select(Scene).where(Scene.project_id==pid))).all())
    knowledge=list((await db.scalars(select(KnowledgeState).where(KnowledgeState.project_id==pid))).all())

    def scene_t(sc):
        return sc.story_time if sc.story_time is not None else sc.narrative_order

    # knowledge check moved below — needs `present` char map + entity maps built first

    # γ1 restricted lifecycle appearance — name match in prose vs StoryState at scene time
    chars={c.id:c for c in (await db.scalars(select(Character).where(Character.project_id==pid))).all()}
    aliases=list((await db.scalars(select(Alias).where(Alias.project_id==pid))).all())
    terms:dict[str,list[str]]={}
    for c in chars.values():
        ts=[c.name]+[a.alias for a in aliases if a.character_id==c.id and a.alias]
        ts+=[w for w in re.split(r"\s+",c.name or "") if len(w)>=4]
        terms[c.id]=[t for t in dict.fromkeys(ts) if t]
    life_states=[s for s in await states_at(db,pid,entity_type="character")
                 if canonical_state_key(s.key)=="lifecycle"]
    for sc in scenes:
        if not sc.prose: continue
        prose_l=sc.prose.lower()
        for st in life_states:
            c=chars.get(st.entity_id)
            if not c or not c.name: continue
            hit=False
            for t in terms.get(c.id,[]):
                if " " in t:
                    if re.search(r"\b"+re.escape(t)+r"\b",sc.prose,re.IGNORECASE): hit=True; break
                elif re.search(r"\b"+re.escape(t)+r"\b",sc.prose): hit=True; break
            if not hit: continue
            iss=restricted_appearance(c.name,st.value_text,sc.scene_type,
                                      st.story_time,scene_t(sc),sc.id,c.id)
            if iss: issues.append(iss)

    # γ4 location conflict — character "location" StoryState vs scene.location_id
    locs={l.id:l for l in (await db.scalars(select(Location).where(Location.project_id==pid))).all()}
    loc_states=list((await db.scalars(select(StoryState).where(
        StoryState.project_id==pid,StoryState.entity_type=="character",
        StoryState.key=="location"))).all())
    if loc_states:
        for sc in scenes:
            if not sc.prose or not sc.location_id: continue
            sloc=locs.get(sc.location_id)
            if not sloc: continue
            eff=effective_at(loc_states,scene_t(sc))
            for (et,eid,k),st in eff.items():
                c=chars.get(eid)
                if not c or not c.name: continue
                hit=any(re.search(r"\b"+re.escape(t)+r"\b",sc.prose,
                                  re.IGNORECASE if " " in t else 0)
                        for t in terms.get(c.id,[]))
                if not hit: continue
                iss=location_conflict(c.name,st.value_text,sloc.name,sloc.id,
                                      st.story_time,scene_t(sc),sc.id,c.id)
                if iss: issues.append(iss)

    # γ5 ability not unlocked — ability name in prose vs its status StoryState
    abilities=list((await db.scalars(select(Ability).where(Ability.project_id==pid))).all())
    if abilities:
        ab_states=list((await db.scalars(select(StoryState).where(
            StoryState.project_id==pid,StoryState.entity_type=="ability",
            StoryState.key=="status"))).all())
        ab_latest={}
        for s in ab_states:
            cur=ab_latest.get(s.entity_id)
            if cur is None or (s.story_time or -1)>=(cur.story_time or -1): ab_latest[s.entity_id]=s
        for sc in scenes:
            if not sc.prose: continue
            eff=effective_at(ab_states,scene_t(sc))
            for ab in abilities:
                if not ab.name or not re.search(r"\b"+re.escape(ab.name)+r"\b",sc.prose,re.IGNORECASE): continue
                st=eff.get(("ability",ab.id,"status")) or ab_latest.get(ab.id)
                iss=ability_locked(ab.name,st.value_text if st else None,
                                   st.story_time if st else None,scene_t(sc),sc.id,ab.id)
                if iss: issues.append(iss)

    # presence map: which characters' names actually appear in each scene's prose
    present:dict[str,set[str]]={}
    for sc in scenes:
        if not sc.prose: continue
        hit=set()
        for c in chars.values():
            if not c.name: continue
            if any(re.search(r"\b"+re.escape(t)+r"\b",sc.prose,
                             re.IGNORECASE if " " in t else 0) for t in terms.get(c.id,[])):
                hit.add(c.id)
        present[sc.id]=hit

    # γ7 item ownership — item name in prose but recorded holder absent
    items={i.id:i for i in (await db.scalars(select(Item).where(Item.project_id==pid))).all()}
    own_states=list((await db.scalars(select(StoryState).where(
        StoryState.project_id==pid,StoryState.entity_type=="item",
        StoryState.key=="ownership"))).all())

    # knowledge leaks — nhân vật thể hiện tri thức trước mốc họ được nó.
    # Cảnh có POV: chỉ POV đó mới "lộ". Không POV (tác giả kể): chỉ flag khi
    # knower có mặt trong văn. Và chỉ tính là lộ khi fact thật sự được nhắc tới.
    abilities_map={a.id:a for a in abilities} if abilities else {}
    facts_by_id={f.id:f for f in (await db.scalars(select(CanonFact).where(CanonFact.project_id==pid))).all()}
    _SUBJ={"item":items,"character":chars,"location":locs,"ability":abilities_map}
    def _fact_terms(f):
        if not f: return []
        ts=[]
        ent=_SUBJ.get(f.subject_type,{}).get(f.subject_id)
        nm=getattr(ent,"name",None)
        if nm: ts.append(nm)
        ts += [w for w in re.findall(r"[\wÀ-ỹ]+", f.value_text or "") if len(w)>=5]
        return list(dict.fromkeys(ts))
    def _fact_label(f):
        if not f: return "dữ kiện"
        ent=_SUBJ.get(f.subject_type,{}).get(f.subject_id)
        nm=getattr(ent,"name",None) or "?"
        return f"{f.predicate.replace('_',' ')} của {nm}" if f.predicate else (f.value_text or "?")[:90]
    for sc in scenes:
        ch=chapters.get(sc.chapter_id)
        if not ch or not sc.prose: continue
        for k in knowledge:
            if not k.knower_id or k.knower_type!="character": continue
            can_leak=(k.knower_id==sc.pov_character_id) if sc.pov_character_id \
                     else (k.knower_id in present.get(sc.id,set()))
            if not can_leak: continue
            if (k.acquired_narrative_order is None or k.acquired_narrative_order<=ch.order_index) and \
               (k.acquired_story_time is None or k.acquired_story_time<=scene_t(sc)):
                continue
            f=facts_by_id.get(k.fact_id)
            fterms=_fact_terms(f)
            if fterms and not any(re.search(r"\b"+re.escape(t)+r"\b",sc.prose,re.IGNORECASE) for t in fterms):
                continue
            kn=chars.get(k.knower_id)
            acq=k.acquired_narrative_order if k.acquired_narrative_order is not None else k.acquired_story_time
            issues.append(Issue(
                "KNOWLEDGE_LEAK","knowledge","warning",
                f"{kn.name if kn else 'Nhân vật'} mới biết { _fact_label(f)} từ mốc {acq} — cảnh này ở mốc {ch.order_index}; kiểm tra cảnh có để lộ không.",
                {"scene_id":sc.id,"knower_id":k.knower_id,"fact_id":k.fact_id,
                 "acquired_narrative_order":k.acquired_narrative_order,
                 "acquired_story_time":k.acquired_story_time,
                 "scene_chapter":ch.order_index,"scene_time":scene_t(sc)}))

    if items and own_states:
        for sc in scenes:
            if not sc.prose: continue
            eff=effective_at(own_states,scene_t(sc))
            for it in items.values():
                if not it.name or not re.search(r"\b"+re.escape(it.name)+r"\b",sc.prose,re.IGNORECASE): continue
                st=eff.get(("item",it.id,"ownership"))
                if not st: continue
                owner_id=st.value_text.strip()
                owner=chars.get(owner_id)
                iss=item_owner_mismatch(it.name,it.id,owner.name if owner else owner_id,
                                        owner_id,present.get(sc.id,set()),sc.id)
                if iss: issues.append(iss)

    # γ8 relationship ended/hostile — both members co-appear in prose
    rels=list((await db.scalars(select(Relationship).where(Relationship.project_id==pid))).all())
    rel_states=list((await db.scalars(select(StoryState).where(
        StoryState.project_id==pid,StoryState.entity_type=="relationship",
        StoryState.key=="status"))).all())
    if rels and rel_states:
        for sc in scenes:
            if not sc.prose: continue
            eff=effective_at(rel_states,scene_t(sc))
            for r in rels:
                st=eff.get(("relationship",r.id,"status"))
                if not st: continue
                pa=present.get(sc.id,set())
                if r.source_character_id in pa and r.target_character_id in pa:
                    iss=relationship_ended(
                        chars[r.source_character_id].name if r.source_character_id in chars else "?",
                        chars[r.target_character_id].name if r.target_character_id in chars else "?",
                        st.value_text,r.id,sc.id)
                    if iss: issues.append(iss)

    # γ3 narrative debt — open threads gone quiet or past payoff window
    threads=list((await db.scalars(select(Thread).where(Thread.project_id==pid,Thread.status=="OPEN"))).all())
    if threads:
        beats=list((await db.scalars(select(ThreadBeat).where(ThreadBeat.project_id==pid))).all())
        last_beat={}
        for b in beats:
            if b.narrative_order is None: continue
            last_beat[b.thread_id]=max(last_beat.get(b.thread_id,0),b.narrative_order)
        narr_orders=[sc.narrative_order for sc in scenes if sc.narrative_order is not None]
        current=max(narr_orders) if narr_orders else (max((c.order_index for c in chapters.values()),default=None))
        for th in threads:
            iss=stale_thread(th,last_beat.get(th.id),current)
            if iss: issues.append(iss)

    # ---- audit mở rộng (deterministic): lớp lỗi phát hiện từ project 58 chương ----
    all_states=list((await db.scalars(select(StoryState).where(StoryState.project_id==pid))).all())
    events=list((await db.scalars(select(StoryEvent).where(StoryEvent.project_id==pid))).all())

    def _entity_label(et,eid):
        ent=_SUBJ.get(et,{}).get(eid)
        return getattr(ent,"name",None) or f"{et}:{(eid or '')[:8]}"

    # CANON_CONFLICT — cùng (subject, predicate) nhiều value_text khác nhau.
    # Extractor ghi subject_id=NULL và nhét subject vào subject_type text tự do
    # → phải resolve entity trước khi group, và chỉ flag predicate đơn-trị.
    _GENERIC_SUBJ={"nhân vật","nhan vat","nhân_vật","person","character","người",
        "địa điểm","địa_điểm","place","location","sự kiện","sự_kiện","event",
        "đồ vật","đồ_vật","object","item","sự vật","sự_vật","vật","vật_dụng",
        "document","group","tổ chức","phong tục","phong_tục","thời gian",
        "bối cảnh","rule","trò chơi","hoạt động","phương tiện","hàng xóm",
        "gia đình","thời_sự","sự việc","chi tiết","quy tắc","khái niệm","giai đoạn"}
    _SINGLEVAL_PRED={"age","education","location","lifecycle","ownership","status",
        "tên","tên gọi","tên_gọi","tuổi","lớp","nghề","nghề nghiệp","nghề_nghiệp",
        "công việc","công_việc","quê","quê quán","quê_quán","năm sinh","nick",
        "nickname","nick_yahoo","vị trí lớp","tiền tiết kiệm","địa chỉ","chức vụ"}
    ent_terms=[]  # (pattern, etype, eid, name) — match tên entity trong text tự do
    for et,mp in (("character",chars),("location",locs),("item",items)):
        for eid,e in mp.items():
            for nm in {getattr(e,"name",None) or "",
                       *((a.alias or "") for a in aliases if et=="character" and a.character_id==eid)}:
                nm=nm.strip()
                if len(nm)>=2: ent_terms.append((re.compile(r"\b"+re.escape(nm)+r"\b",re.IGNORECASE),et,eid,nm))
            if et=="character" and getattr(e,"name",None):
                last=e.name.split()[-1]
                if len(last)>=3: ent_terms.append((re.compile(r"\b"+re.escape(last)+r"\b"),et,eid,last))
    ent_terms.sort(key=lambda t:-len(t[3]))
    def _match_entity(text):
        for pat,et,eid,_nm in ent_terms:
            if pat.search(text or ""): return (et,eid)
        return None
    def _subject_of(f):
        if f.subject_id:
            for et,mp in (("character",chars),("location",locs),("item",items)):
                if f.subject_id in mp: return (et,f.subject_id)
            m=_match_entity(f.subject_id)
            if m: return m
        st=(f.subject_type or "").strip()
        if st and st.lower() not in _GENERIC_SUBJ:
            return _match_entity(st) or ("label",st.lower())
        return _match_entity(f.value_text or "")
    cgroups={}
    for f in facts_by_id.values():
        if (f.truth_status or "CANON").upper()=="REJECTED": continue
        pk=canonical_state_key(f.predicate or "") or (f.predicate or "").strip().lower()
        if pk not in _SINGLEVAL_PRED: continue
        subj=_subject_of(f)
        if subj is None: continue
        cgroups.setdefault((subj,pk),[]).append(f)
    for (subj,pk),fs in cgroups.items():
        lbl=_entity_label(*subj) if subj[0]!="label" else subj[1]
        cid=subj[1] if subj[0]=="character" else None
        iss=canon_conflict(lbl,pk,[f.id for f in fs],
                           [f.value_text for f in fs],cid)
        if iss: issues.append(iss)

    # STATE_CONFLICT — cùng entity+canonical key tại cùng narrative_order
    sgroups={}
    for s in all_states:
        sgroups.setdefault((s.entity_type,s.entity_id,canonical_state_key(s.key),
                            s.narrative_order),[]).append(s)
    for (et,eid,ck,narr),ss in sgroups.items():
        iss=state_conflict(_entity_label(et,eid),ck,narr,[s.id for s in ss],
                           [s.value_text for s in ss],et,eid)
        if iss: issues.append(iss)

    # STATE_REGRESSION — tuổi/lớp lùi khi narrative_order tăng
    regseq={}
    for (et,eid,ck,narr),ss in sgroups.items():
        if ck not in ("age","education") or narr is None: continue
        regseq.setdefault((et,eid,ck),[]).append((narr,ss[-1].value_text))
    for (et,eid,ck),seq in regseq.items():
        seq.sort(key=lambda x:x[0]); prev=None
        for narr,val in seq:
            if prev is not None:
                iss=state_regression(_entity_label(et,eid),ck,prev,(narr,val),et,eid)
                if iss: issues.append(iss); break
            prev=(narr,val)

    # LOCATION_DRIFT — prose nhắc Location ∉ (skeleton ∪ nơi-ở đã ghi)
    loc_terms={l.id:l.name.strip() for l in locs.values() if l.name and len(l.name.strip())>=3}
    known_locs={}
    for s in all_states:
        if (s.entity_type=="character" and canonical_state_key(s.key)=="location"
            and s.narrative_order is not None):
            known_locs.setdefault(s.narrative_order,set()).add(s.value_text.strip().lower())
    for sc in scenes:
        if not sc.prose or sc.narrative_order is None or not loc_terms: continue
        skel=(sc.skeleton or "").lower()
        allowed=set().union(*(vv for n,vv in known_locs.items() if n<=sc.narrative_order)) \
                if known_locs else set()
        for lid,ln in loc_terms.items():
            if not re.search(r"\b"+re.escape(ln)+r"\b",sc.prose,re.IGNORECASE): continue
            if ln.lower() in skel or any(ln.lower() in a or a in ln.lower() for a in allowed):
                continue
            iss=unplanned_location(ln,lid,sc.id,sc.title or "?",sc.narrative_order)
            if iss: issues.append(iss)

    # PHASE_LEAK — prose nhắc entity trước mốc nó xuất hiện trong dữ kiện
    first_narr={}
    for s in all_states:
        if s.narrative_order is None: continue
        k=(s.entity_type,s.entity_id)
        if k not in first_narr or s.narrative_order<first_narr[k]: first_narr[k]=s.narrative_order
    for ev in events:
        if ev.narrative_order is None or not ev.location_id: continue
        k=("location",ev.location_id)
        if k not in first_narr or ev.narrative_order<first_narr[k]: first_narr[k]=ev.narrative_order
    for sc in scenes:
        if not sc.prose or sc.narrative_order is None: continue
        for (et,eid),fn in first_narr.items():
            if et not in ("location","item") or fn<=sc.narrative_order: continue
            nm=_entity_label(et,eid)
            if ":" in nm[:len(et)+2]: continue
            if not re.search(r"\b"+re.escape(nm)+r"\b",sc.prose,re.IGNORECASE): continue
            issues.append(phase_leak(nm,et,eid,sc.id,sc.title or "?",sc.narrative_order,fn))

    # MISSING_EXTRACTION — chương có prose nhưng chưa trích sự kiện
    ev_narrs={ev.narrative_order for ev in events if ev.narrative_order is not None}
    for ch in chapters.values():
        if ch.order_index in ev_narrs: continue
        if any(s.chapter_id==ch.id and s.prose for s in scenes):
            issues.append(missing_extraction(ch.id,ch.title or "?",ch.order_index))

    # SCENE_NO_NARR — prose có mà thiếu narrative_order
    for sc in scenes:
        if sc.prose and sc.narrative_order is None:
            ch=chapters.get(sc.chapter_id)
            issues.append(scene_no_narr(sc.id,sc.title or "?",ch.order_index if ch else None))

    out=dedupe(issues)
    return {"issues":[{"code":i.code,"category":i.category,"severity":i.severity,
                       "message":i.message,"evidence":i.evidence} for i in out],
            "count":len(out),"auto_mutations":0}

# ---- AI deep-check: soi 1 chương bằng model (lỗi nghĩa deterministic không bắt được) ----
_DEEP_SYSTEM=(
    "Bạn là biên tập viên kiểm tra tính liên tục của truyện dài. Đọc chương được cung cấp "
    "(xương cảnh + văn) và chỉ ra CÁC LỖI NỘI DUNG:\n"
    "- sự kiện bị viết 2 lần với chi tiết mâu thuẫn giữa các cảnh trong chương\n"
    "- chi tiết nhân vật/sự vật tự phủ nhận (con số, tuổi, đồ vật, hành động)\n"
    "- văn lệch xương cảnh đã dàn hoặc lệch trạng thái đã chốt (bối cảnh, thời điểm, ai ở đâu)\n"
    "- nhân vật/địa danh xuất hiện sai pha truyện\n"
    "Mỗi lỗi một mục. KHÔNG bình luận văn phong, không chế lỗi khi văn ổn. "
    "Trả về JSON THUẦN (không markdown, không giải thích ngoài): "
    '[{"scene":"tên cảnh hoặc null","severity":"error|warning","message":"mô tả lỗi gọn",'
    '"suggestion":"gợi ý sửa ngắn"}]. Không có lỗi thì trả [].'
)

@router.post("/projects/{pid}/chapters/{chid}/deep-check")
async def deep_check_chapter(pid:str,chid:str,db:AsyncSession=Depends(get_db)):
    """AI soi một chương — semantic issues mà checker deterministic không bắt được.
    Kết quả lưu vào audit_findings (bản nháp phát hiện, không phải canon)."""
    await project_ok(db,pid)
    ch=await db.get(Chapter,chid)
    if not ch or ch.project_id!=pid: raise HTTPException(404,"chapter not found")
    scs=list((await db.scalars(select(Scene).where(Scene.chapter_id==chid)
                               .order_by(Scene.order_index))).all())
    if not any(s.prose for s in scs): raise HTTPException(400,"chapter has no prose")
    total=(await db.scalar(select(func.max(Chapter.order_index))
                           .where(Chapter.project_id==pid))) or ch.order_index
    arc=await db.get(Arc,ch.arc_id) if ch.arc_id else None
    cons=await build_constraints(db,pid,Scene(narrative_order=ch.order_index))
    blk=["=== TRẠNG THÁI ĐÃ CHỐT TẠI CHƯƠNG NÀY ==="]+ \
        [f"- {x}" for x in cons.get("must_respect",[])[:15]] if cons.get("must_respect") else []
    hdr="\n\n".join(
        [f"=== CHƯƠNG {ch.order_index}/{total}: \"{ch.title}\""
         + (f" — Hồi \"{arc.title}\"" if arc else "") + " ==="] + blk)

    # Scene dài chia thành windows tại ranh đoạn — bản cũ cắt [:3500]
    # khiến đuôi chương (chỗ lỗi hay nằm) không được soi. Ngưỡng adapt theo
    # tier năng lực của credential (đặt/auto ở trang Kết nối API):
    # low: gateway ~60s cap → window nhỏ; strong: gần như không chia — model
    # thấy trọn chương, bắt được lỗi mâu thuẫn xuyên-cảnh tốt hơn.
    router = ModelRouter(db)
    _prov = await router.provider_name("review", pid)
    _tier = await router.provider_tier("review", pid)
    win_len = {"low": 4500, "standard": 12000}.get(_tier, 40000)
    grp_len = {"low": 6500, "standard": 16000}.get(_tier, 45000)

    def _windows(text: str, max_len: int) -> list:
        paras = text.split("\n\n")
        out, cur = [], ""
        for p in paras:
            if cur and len(cur) + len(p) + 2 > max_len:
                out.append(cur); cur = p
            else:
                cur = f"{cur}\n\n{p}" if cur else p
        if cur: out.append(cur)
        # đoạn đơn vẫn quá dài (ít gặp) → cắt cứng
        return [w if len(w) <= max_len * 1.4 else w[: max_len * 1.4] for w in out] or [text[:max_len]]

    segs: list[str] = []
    for i, sc in enumerate(scs):
        prose = (sc.prose or "").strip()
        skel = f"\nXương cảnh: {sc.skeleton}" if sc.skeleton else ""
        if not prose:
            segs.append(f'--- Cảnh {i+1}: "{sc.title or "?"}"{skel}\n(chưa có văn)')
            continue
        wins = _windows(prose, win_len)
        for k, w in enumerate(wins):
            tag = f" [phần {k+1}/{len(wins)}]" if len(wins) > 1 else ""
            segs.append(f'--- Cảnh {i+1}: "{sc.title or "?"}"{tag}{skel}\nVăn:\n{w}')

    # gom segments vào prompts ≤ grp_len, cap 6 calls/chương
    prompts: list[str] = []
    cur, curlen = [hdr], len(hdr)
    for seg in segs:
        if curlen + len(seg) + 2 > grp_len and len(cur) > 1 and len(prompts) < 5:
            prompts.append(cur); cur, curlen = [hdr], len(hdr)
        cur.append(seg); curlen += len(seg) + 2
    prompts.append(cur)
    title2id = {s.title: s.id for s in scs if s.title}
    found: list = []
    seen_msg: set = set()
    provider = model = ""
    replies: list[str] = []
    skipped = 0
    for prt in prompts:
        prompt = "\n\n".join(prt) + "\n\nTrả JSON theo schema đã nêu trong system."
        result = None
        for attempt in range(3):
            try:
                result = await router.complete(
                    ModelRequest(task="review", prompt=prompt,
                                 project_id=pid, system=_DEEP_SYSTEM))
                break
            except RuntimeError:
                if attempt < 2:
                    await asyncio.sleep(4 + attempt * 6)
        if result is None:
            skipped += 1
            continue
        provider, model = result.provider or "", result.model or ""
        txt = (result.text or "").strip()
        replies.append(txt)
        m = re.search(r"\[.*\]", txt, re.DOTALL)
        if not m:
            continue
        try:
            raw = json.loads(m.group())
        except (json.JSONDecodeError, TypeError):
            continue
        for it in (raw if isinstance(raw, list) else []):
            if not isinstance(it, dict) or not it.get("message"):
                continue
            key = re.sub(r"\s+", " ", str(it["message"]))[:50].lower()
            if key in seen_msg:
                continue
            seen_msg.add(key)
            found.append({
                "code": str(it.get("code") or "AI_REVIEW")[:40],
                "severity": it.get("severity") if it.get("severity") in ("error", "warning", "info") else "warning",
                "message": str(it["message"])[:400],
                "suggestion": str(it.get("suggestion") or "")[:300],
                "scene_id": title2id.get(it.get("scene"))})

    f = AuditFinding(project_id=pid, scope_type="chapter", scope_id=chid,
                     issues_json=json.dumps(found, ensure_ascii=False))
    db.add(f)
    db.add(AiTurn(project_id=pid, scope_id=chid, task="deep_check",
                  prompt_excerpt=(f"[{len(prompts)} calls] " + prompts[0][0])[:4000],
                  reply_text="\n---\n".join(replies)[:4000],
                  provider=provider, model=model))
    await db.commit()
    out = {"finding_id": f.id, "issues": found, "count": len(found),
           "provider": provider or _prov, "model": model, "calls": len(prompts),
           "tier": _tier}
    if skipped:
        out["skipped_windows"] = skipped
    return out

@router.post("/projects/{pid}/scenes/{sid}/ai-fix")
async def ai_fix_scene(pid:str,sid:str,p:dict=Body(...),db:AsyncSession=Depends(get_db)):
    """AI sửa một cảnh theo mô tả lỗi — trả bản nháp, KHÔNG ghi DB.
    Tác giả xem/patch tay → scene_versions tự snapshot nên revert được."""
    await project_ok(db,pid)
    sc=await db.get(Scene,sid)
    if not sc or sc.project_id!=pid: raise HTTPException(404,"scene not found")
    if not (sc.prose or "").strip(): raise HTTPException(400,"scene has no prose")
    issue=str(p.get("issue") or "").strip() or "Tự soi và sửa các lỗi liên tục rõ ràng nhất trong đoạn văn."
    user_prompt=(f"ĐOẠN VĂN GỐC:\n{sc.prose}\n\nGHI CHÚ CẦN SỬA:\n{issue}\n\n"
                 "Chỉ sửa đúng lỗi đã nêu, giữ nguyên phần còn lại và văn phong tác giả.")
    system,prompt,manifest=await build_story_prompt(db,pid,"revision",user_prompt,sid)
    try:
        result=await ModelRouter(db).complete(
            ModelRequest(task="revision",prompt=prompt,project_id=pid,system=system))
    except RuntimeError as e: raise HTTPException(503,str(e))
    db.add(AiTurn(project_id=pid,scope_id=sid,task="ai_fix",
                  prompt_excerpt=prompt[:4000],reply_text=(result.text or "")[:4000],
                  provider=result.provider or "",model=result.model or ""))
    await db.commit()
    return {"revised":result.text or "","provider":result.provider,"model":result.model,
            "context":manifest}

@router.get("/projects/{pid}/audit/findings")
async def audit_findings(pid:str,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    rows=list((await db.scalars(select(AuditFinding)
        .where(AuditFinding.project_id==pid)
        .order_by(AuditFinding.created_at.desc()))).all())
    chs={c.id:c for c in (await db.scalars(select(Chapter).where(Chapter.project_id==pid))).all()}
    return {"findings":[{"id":r.id,"scope_type":r.scope_type,"scope_id":r.scope_id,
                         "chapter_title":chs.get(r.scope_id).title if r.scope_id in chs else None,
                         "chapter_order":chs.get(r.scope_id).order_index if r.scope_id in chs else None,
                         "issues":json.loads(r.issues_json or "[]"),"created_at":r.created_at}
                        for r in rows]}

@router.delete("/audit/findings/{fid}")
async def delete_finding(fid:str,db:AsyncSession=Depends(get_db)):
    r=await db.get(AuditFinding,fid)
    if not r: raise HTTPException(404,"not found")
    await db.delete(r); await db.commit(); return {"ok":True}

# ---- AI turn history (audit trail mọi call ai/complete) ----
def _turn_out(t:AiTurn)->dict:
    return {"id":t.id,"task":t.task,"scope_id":t.scope_id,"provider":t.provider,
            "model":t.model,"prompt_excerpt":t.prompt_excerpt,"reply_text":t.reply_text,
            "created_at":t.created_at}

@router.get("/projects/{pid}/ai/turns")
async def list_ai_turns(pid:str,limit:int=200,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    limit=max(1,min(limit,500))
    turns=list((await db.scalars(select(AiTurn).where(AiTurn.project_id==pid)
        .order_by(AiTurn.created_at.desc(),AiTurn.id.desc()).limit(limit))).all())
    total=await db.scalar(select(func.count(AiTurn.id)).where(AiTurn.project_id==pid))
    return {"total":total or 0,"turns":[_turn_out(t) for t in turns]}

@router.delete("/projects/{pid}/ai/turns/{turn_id}")
async def delete_ai_turn(pid:str,turn_id:str,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    t=await db.get(AiTurn,turn_id)
    if not t or t.project_id!=pid: raise HTTPException(404,"turn not found in project")
    await db.delete(t); await db.commit(); return {"deleted":turn_id}

@router.post("/projects/{pid}/ai/turns/prune")
async def prune_ai_turns(pid:str,p:PruneTurnsRequest,db:AsyncSession=Depends(get_db)):
    """Giữ lại `keep` turn mới nhất, xoá phần còn lại."""
    await project_ok(db,pid)
    ids=list((await db.scalars(select(AiTurn.id).where(AiTurn.project_id==pid)
        .order_by(AiTurn.created_at.desc(),AiTurn.id.desc()))).all())
    doomed=ids[p.keep:]
    if doomed:
        await db.execute(delete(AiTurn).where(AiTurn.id.in_(doomed)))
        await db.commit()
    return {"deleted":len(doomed),"kept":len(ids)-len(doomed)}
