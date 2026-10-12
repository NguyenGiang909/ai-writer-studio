
import asyncio,json,random,re,time
from datetime import datetime as _dt
from fastapi import APIRouter,Depends,HTTPException,Body
from sqlalchemy import select,delete,func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db,SessionLocal
from app.models import Project,Chapter,Scene,Arc
from app.models.review import SuggestedChange,AuditFinding,AuditJob
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
    phase_leak,missing_extraction,scene_no_narr,fatigue_phrases,style_fatigue,
    title_content_drift,fact_drift,_FACT_LABEL_RX)
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
    t0=time.monotonic()
    try:
        result=await ModelRouter(db).complete(
            ModelRequest(task=p.task,prompt=prompt,model=p.model,project_id=pid,system=system))
    except RuntimeError as e: raise HTTPException(503,str(e))
    db.add(AiTurn(project_id=pid,scope_id=p.scene_id or pid,task=p.task,
                  prompt_excerpt=p.prompt[:4000],reply_text=(result.text or "")[:20000],
                  provider=result.provider or "",model=result.model or "",
                  latency_ms=int((time.monotonic()-t0)*1000)))
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
    t0=time.monotonic()
    try:
        result=await ModelRouter(db).complete(
            ModelRequest(task="character_profile",prompt=prompt,project_id=pid,system=system))
    except RuntimeError as e: raise HTTPException(503,str(e))
    db.add(AiTurn(project_id=pid,scope_id=existing.id if existing else pid,
                  task="character_profile",prompt_excerpt=prompt[:1500],
                  reply_text=(result.text or "")[:20000],
                  provider=result.provider or "",model=result.model or "",
                  latency_ms=int((time.monotonic()-t0)*1000)))
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

    # ---- quét hiện diện entity 1 PASS/cảnh (thay ~scene×entity×term re.search).
    # Hai bảng term: IGNORECASE (multi-word char + item/ability/location) và
    # case-sensitive (single-word char term — giữ ngữ nghĩa cũ tránh nhầm danh
    # từ thường). Mỗi cảnh chỉ 2 finditer; checker tra set O(1).
    chars={c.id:c for c in (await db.scalars(select(Character).where(Character.project_id==pid))).all()}
    aliases=list((await db.scalars(select(Alias).where(Alias.project_id==pid))).all())
    terms:dict[str,list[str]]={}
    for c in chars.values():
        ts=[c.name]+[a.alias for a in aliases if a.character_id==c.id and a.alias]
        ts+=[w for w in re.split(r"\s+",c.name or "") if len(w)>=4]
        terms[c.id]=[t for t in dict.fromkeys(ts) if t]

    locs={l.id:l for l in (await db.scalars(select(Location).where(Location.project_id==pid))).all()}
    items={i.id:i for i in (await db.scalars(select(Item).where(Item.project_id==pid))).all()}
    abilities=list((await db.scalars(select(Ability).where(Ability.project_id==pid))).all())

    ic_map:dict[str,list[tuple[str,str]]]={}   # norm term -> [(kind,id)] (IGNORECASE)
    cs_map:dict[str,list[str]]={}            # single-word term -> [char_id] (case-sensitive)
    ic_terms:set[str]=set()
    for cid,ts in terms.items():
        for t in ts:
            if " " in t:
                k=t.strip().lower()
                ic_terms.add(k); ic_map.setdefault(k,[]).append(("character",cid))
            else:
                cs_map.setdefault(t,[]).append(cid)
    for it in items.values():
        if it.name and len(it.name.strip())>=2:
            k=it.name.strip().lower(); ic_terms.add(k); ic_map.setdefault(k,[]).append(("item",it.id))
    for ab in abilities:
        if ab.name and len(ab.name.strip())>=2:
            k=ab.name.strip().lower(); ic_terms.add(k); ic_map.setdefault(k,[]).append(("ability",ab.id))
    for l in locs.values():
        if l.name and len(l.name.strip())>=3:
            k=l.name.strip().lower(); ic_terms.add(k); ic_map.setdefault(k,[]).append(("location",l.id))

    def _big(terms_, flags=0):
        return re.compile(r"\b("+"|".join(re.escape(t) for t in sorted(terms_,key=len,reverse=True))+r")\b",flags) if terms_ else None
    rx_ic=_big(ic_terms,re.IGNORECASE)
    rx_cs=_big(set(cs_map))

    present:dict[str,set[str]]={}      # char có mặt trong prose cảnh
    item_hit:dict[str,set[str]]={}     # item được nhắc
    ab_hit:dict[str,set[str]]={}       # ability được nhắc
    loc_hit:dict[str,set[str]]={}      # location được nhắc
    for sc in scenes:
        if not sc.prose: continue
        hit={"character":set(),"item":set(),"ability":set(),"location":set()}
        if rx_ic:
            for m in rx_ic.finditer(sc.prose):
                for kind,eid in ic_map.get(m.group(0).lower(),()):
                    hit[kind].add(eid)
        if rx_cs:
            for m in rx_cs.finditer(sc.prose):
                hit["character"].update(cs_map.get(m.group(0),()))
        present[sc.id]=hit["character"]; item_hit[sc.id]=hit["item"]
        ab_hit[sc.id]=hit["ability"]; loc_hit[sc.id]=hit["location"]

    # γ1 restricted lifecycle appearance — char có mặt trong cảnh nhưng
    # lifecycle state cấm hiện diện
    life_states=[s for s in await states_at(db,pid,entity_type="character")
                 if canonical_state_key(s.key)=="lifecycle"]
    for sc in scenes:
        if not sc.prose: continue
        for st in life_states:
            c=chars.get(st.entity_id)
            if not c or not c.name or st.entity_id not in present.get(sc.id,set()): continue
            iss=restricted_appearance(c.name,st.value_text,sc.scene_type,
                                      st.story_time,scene_t(sc),sc.id,c.id)
            if iss: issues.append(iss)

    # γ4 location conflict — character "location" StoryState vs scene.location_id
    loc_states=list((await db.scalars(select(StoryState).where(
        StoryState.project_id==pid,StoryState.entity_type=="character",
        StoryState.key=="location"))).all())
    if loc_states:
        for sc in scenes:
            if not sc.prose or not sc.location_id: continue
            sloc=locs.get(sc.location_id)
            if not sloc: continue
            pa=present.get(sc.id,set())
            if not pa: continue
            eff=effective_at(loc_states,scene_t(sc))
            for (et,eid,k),st in eff.items():
                c=chars.get(eid)
                if not c or not c.name or eid not in pa: continue
                iss=location_conflict(c.name,st.value_text,sloc.name,sloc.id,
                                      st.story_time,scene_t(sc),sc.id,c.id)
                if iss: issues.append(iss)

    # γ5 ability not unlocked — ability được nhắc nhưng chưa UNLOCKED
    if abilities:
        ab_states=list((await db.scalars(select(StoryState).where(
            StoryState.project_id==pid,StoryState.entity_type=="ability",
            StoryState.key=="status"))).all())
        ab_latest={}
        for s in ab_states:
            cur=ab_latest.get(s.entity_id)
            if cur is None or (s.story_time or -1)>=(cur.story_time or -1): ab_latest[s.entity_id]=s
        for sc in scenes:
            if not sc.prose or not ab_hit.get(sc.id): continue
            eff=effective_at(ab_states,scene_t(sc))
            for ab in abilities:
                if ab.id not in ab_hit.get(sc.id,set()): continue
                st=eff.get(("ability",ab.id,"status")) or ab_latest.get(ab.id)
                iss=ability_locked(ab.name,st.value_text if st else None,
                                   st.story_time if st else None,scene_t(sc),sc.id,ab.id)
                if iss: issues.append(iss)

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
            if not sc.prose or not item_hit.get(sc.id): continue
            eff=effective_at(own_states,scene_t(sc))
            for it in items.values():
                if not it.name or it.id not in item_hit.get(sc.id,set()): continue
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
        if not sc.prose or sc.narrative_order is None or not loc_hit.get(sc.id): continue
        skel=(sc.skeleton or "").lower()
        allowed=set().union(*(vv for n,vv in known_locs.items() if n<=sc.narrative_order)) \
                if known_locs else set()
        for lid in loc_hit.get(sc.id,set()):
            ln=loc_terms.get(lid)
            if not ln: continue
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
        hits=item_hit.get(sc.id,set())|loc_hit.get(sc.id,set())
        if not hits: continue
        for (et,eid),fn in first_narr.items():
            if et not in ("location","item") or fn<=sc.narrative_order or eid not in hits: continue
            nm=_entity_label(et,eid)
            if ":" in nm[:len(et)+2]: continue
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

    # STYLE_FATIGUE — cụm 3 từ lặp bất thường trong chương (dấu hiệu văn mẫu)
    for ch in chapters.values():
        prose="\n\n".join(s.prose or "" for s in scenes if s.chapter_id==ch.id)
        if len(prose)<800: continue
        for phrase,n in fatigue_phrases(prose):
            issues.append(style_fatigue(phrase,n,ch.id,ch.order_index))

    # TITLE_CONTENT_DRIFT (C13) — tên cảnh nhắc Location/tên riêng latin đã
    # biết mà văn không hề nhắc → tên trôi khỏi nội dung
    for sc in scenes:
        title=(sc.title or "").strip()
        if not sc.prose or len(title)<3: continue
        lh=loc_hit.get(sc.id,set())
        for lid,ln in loc_terms.items():
            if re.search(r"\b"+re.escape(ln)+r"\b",title,re.IGNORECASE) and \
               lid not in lh:
                ch=chapters.get(sc.chapter_id)
                issues.append(title_content_drift(
                    ln,sc.id,title,ch.order_index if ch else None))
        # tên riêng kiểu latin trong title ("Lakeview", "Starbucks") vắng mặt
        # trong văn — bắt lớp lệch không nằm trong bảng Location
        for w in re.findall(r"[A-Za-z]{4,}",title):
            if not re.search(r"\b"+re.escape(w)+r"\b",sc.prose,re.IGNORECASE):
                ch=chapters.get(sc.chapter_id)
                issues.append(title_content_drift(
                    w,sc.id,title,ch.order_index if ch else None))

    # FACT_DRIFT (C14) — nhãn lặp kiểu 'Mục 011' gắn ngày khác nhau giữa
    # các chương mà không dữ kiện nào giải thích
    dated:dict[str,list[tuple[str,int|None]]]={}
    for sc in scenes:
        if not sc.prose: continue
        ch=chapters.get(sc.chapter_id)
        for label,d in _FACT_LABEL_RX.findall(sc.prose):
            key=re.sub(r"\s+"," ",label.strip().lower())
            dated.setdefault(key,[]).append((d,ch.order_index if ch else None))
    for key,pairs in dated.items():
        ds={d for d,_ in pairs}
        if len(ds)>=2:
            issues.append(fact_drift(key,sorted(ds),
                                     [o for _,o in pairs if o is not None]))

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

_BG_TASKS: set = set()


def _spawn_job(coro):
    """Giữ strong-ref tới task nền — create_task không ref sẽ bị GC hủy giữa
    chừng (job kẹt status 'running' mãi, không log lỗi)."""
    t = asyncio.create_task(coro)
    _BG_TASKS.add(t)
    t.add_done_callback(_BG_TASKS.discard)
    return t


async def _job_heartbeat(job_id: str, stop: asyncio.Event):
    """Ghi ts vào result_json mỗi 60s chừng nào task còn sống — bằng chứng
    'còn chạy' cho _reap_stale_job (1 call provider có thể >8ph, progress
    chỉ nhảy giữa các call → không đủ tin). Process chết → ts ngừng → reap."""
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=60)
            break
        except asyncio.TimeoutError:
            pass
        try:
            async with SessionLocal() as hb:
                job = await hb.get(AuditJob, job_id)
                if not job or job.status != "running":
                    break
                r = json.loads(job.result_json) if job.result_json else {}
                if not isinstance(r, dict):
                    r = {}
                r["ts"] = _dt.utcnow().isoformat()
                job.result_json = json.dumps(r, ensure_ascii=False)
                await hb.commit()
        except Exception:
            pass  # heartbeat không được giết job


async def _audit_job_run(job_id: str, work):
    """Vỏ chạy job nền: session riêng, kết quả cuối vào result_json, lỗi vào
    error — client poll GET /audit/jobs/{id} thấy cả progress lẫn kết quả."""
    stop = asyncio.Event()
    beat = asyncio.create_task(_job_heartbeat(job_id, stop))
    _BG_TASKS.add(beat)
    beat.add_done_callback(_BG_TASKS.discard)
    try:
        async with SessionLocal() as db:
            job = await db.get(AuditJob, job_id)
            if not job:
                return
            try:
                out = await work(db)
                job.status = "done"
                job.result_json = json.dumps(out, ensure_ascii=False)
            except Exception as e:  # noqa: BLE001 — job fail không giết server
                import traceback; traceback.print_exc()
                job.status = "failed"
                job.error = str(e)[:1000]
            job.finished_at = _dt.utcnow().isoformat()
            await db.commit()
    finally:
        stop.set()
        beat.cancel()


_JOB_STALE_MIN = 8


def _job_last_activity(job) -> str:
    """Mốc hoạt động cuối: ts trong progress (ghi mỗi call xong) nếu có,
    ngược lại created_at. Job sống lâu (>8ph vì provider chậm) vẫn có
    progress mới → không bị reap nhầm."""
    if job.result_json:
        try:
            ts = (json.loads(job.result_json) or {}).get("ts")
            if ts:
                return ts
        except Exception:
            pass
    return job.created_at


async def _reap_stale_job(db, job) -> bool:
    """Job 'running' im quá lâu → process chủ đã chết (restart/crash) — đánh
    failed để dedupe không chặn mọi lần thử sau (mồ côi = kẹt vĩnh viễn)."""
    try:
        age_min = (_dt.utcnow() - _dt.fromisoformat(
            _job_last_activity(job))).total_seconds() / 60
    except Exception:
        age_min = 0
    if age_min < _JOB_STALE_MIN:
        return False
    job.status = "failed"
    job.error = f"job mất theo tiến trình chết (restart/crash) — chạy lại được"
    job.finished_at = _dt.utcnow().isoformat()
    await db.commit()
    return True


async def _job_progress(db, job_id: str, **kw):
    """Cập nhật progress vào result_json + commit — poll session khác thấy
    được (flush không đủ vì SQLite đọc qua connection riêng). ts = nhịp
    tim cho _reap_stale_job (job sống lâu vẫn có tiến triển mới)."""
    job = await db.get(AuditJob, job_id)
    if job:
        job.result_json = json.dumps(
            {**kw, "ts": _dt.utcnow().isoformat()}, ensure_ascii=False)
        await db.commit()


@router.get("/projects/{pid}/audit/jobs/{jid}")
async def audit_job_status(pid: str, jid: str, db: AsyncSession = Depends(get_db)):
    job = await db.get(AuditJob, jid)
    if not job or job.project_id != pid:
        raise HTTPException(404, "job not found")
    result = None
    if job.result_json:
        try:
            result = json.loads(job.result_json)
        except Exception:
            result = None
    return {"id": job.id, "scope_type": job.scope_type, "scope_id": job.scope_id,
            "status": job.status, "result": result, "error": job.error,
            "created_at": job.created_at, "finished_at": job.finished_at}


@router.get("/projects/{pid}/audit/jobs")
async def audit_jobs_list(pid: str, db: AsyncSession = Depends(get_db)):
    """Job gần nhất — UI resume trạng thái sau reload (job vẫn chạy khi đổi trang)."""
    rows = list((await db.scalars(select(AuditJob).where(
        AuditJob.project_id == pid).order_by(
        AuditJob.created_at.desc()))).all()[:20])
    for j in rows:  # job 'running' mồ côi (process chết) → failed ngay khi đọc
        if j.status == "running":
            await _reap_stale_job(db, j)
    out = []
    for j in rows:
        result = None
        if j.result_json:
            try:
                result = json.loads(j.result_json)
            except Exception:
                result = None
        out.append({"id": j.id, "scope_type": j.scope_type, "scope_id": j.scope_id,
                    "status": j.status, "result": result, "error": j.error,
                    "created_at": j.created_at, "finished_at": j.finished_at})
    return {"jobs": out}


@router.post("/projects/{pid}/chapters/{chid}/deep-check")
async def deep_check_chapter(pid:str,chid:str,db:AsyncSession=Depends(get_db)):
    """Tạo job nền soi một chương (C10: bản đồng bộ chạy >4ph → vượt client-
    timeout, không ghi gì). Trả job_id ngay; poll GET /audit/jobs/{id}.
    1 scope chỉ 1 job running — gọi lại trả job cũ thay vì chồng call."""
    await project_ok(db,pid)
    ch=await db.get(Chapter,chid)
    if not ch or ch.project_id!=pid: raise HTTPException(404,"chapter not found")
    n_prose=await db.scalar(select(func.count(Scene.id)).where(
        Scene.chapter_id==chid,Scene.prose.is_not(None),Scene.prose!=""))
    if not n_prose: raise HTTPException(400,"chapter has no prose")
    running=(await db.scalars(select(AuditJob).where(
        AuditJob.project_id==pid,AuditJob.scope_type=="chapter",
        AuditJob.scope_id==chid,AuditJob.status=="running"))).first()
    if running:
        if await _reap_stale_job(db, running):
            pass  # job mồ côi đã đánh failed → rơi xuống tạo job mới
        else:
            return {"job_id":running.id,"status":"running","dedup":True}
    job=AuditJob(project_id=pid,scope_type="chapter",scope_id=chid)
    db.add(job); await db.commit(); await db.refresh(job)
    _spawn_job(_audit_job_run(
        job.id,lambda s: _deep_check_chapter_work(s,pid,chid,job.id)))
    return {"job_id":job.id,"status":"running"}


async def _deep_check_chapter_work(db:AsyncSession,pid:str,chid:str,
                                   job_id:str|None=None)->dict:
    """Thân soi chương — semantic issues checker deterministic không bắt được.
    Kết quả lưu audit_findings (bản nháp phát hiện, không phải canon)."""
    ch=await db.get(Chapter,chid)
    if not ch or ch.project_id!=pid: raise ValueError("chapter not found")
    scs=list((await db.scalars(select(Scene).where(Scene.chapter_id==chid)
                               .order_by(Scene.order_index))).all())
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
    t0 = time.monotonic()
    for pi, prt in enumerate(prompts):
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
                    await asyncio.sleep(4 + attempt * 6 + random.uniform(0, 3))
        if job_id:
            await _job_progress(db, job_id, progress=f"{pi + 1}/{len(prompts)}",
                                provider=provider, model=model)
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

    # lọc motif tác giả đã đánh 'không phải lỗi' (dismissed) — không tái xuất
    dismissed = await _dismissed_issue_keys(db, pid)
    if dismissed:
        found = [it for it in found if _issue_key(it) not in dismissed]
    f = AuditFinding(project_id=pid, scope_type="chapter", scope_id=chid,
                     issues_json=json.dumps(found, ensure_ascii=False))
    db.add(f)
    db.add(AiTurn(project_id=pid, scope_id=chid, task="deep_check",
                  prompt_excerpt=(f"[{len(prompts)} calls] " + prompts[0][0])[:4000],
                  reply_text="\n---\n".join(replies)[:20000],
                  provider=provider, model=model,
                  latency_ms=int((time.monotonic() - t0) * 1000)))
    await db.commit()
    out = {"finding_id": f.id, "issues": found, "count": len(found),
           "provider": provider or _prov, "model": model, "calls": len(prompts),
           "tier": _tier}
    if skipped:
        out["skipped_windows"] = skipped
    return out

_DEEP_RANGE_SYSTEM=(
    "Bạn là biên tập viên tổng của truyện dài. Soi MỘT KHOẢNG CHƯƠNG qua "
    "tóm tắt, xương cảnh và mẫu văn được cung cấp. Chỉ báo LỖI CẤP KHOẢNG "
    "(xuyên từ 2 chương trở lên) — KHÔNG lặp lại lỗi đã ghi trong mục "
    "'findings đã biết', không bình luận văn phong từng câu:\n"
    "- THREAD_DRIFT: hố/tuyến mở trước hoặc trong khoảng mà không chương nào nhích\n"
    "- CHARACTER_FADE: nhân vật quan trọng vắng mặt bất thường qua nhiều chương\n"
    "- PREMISE_DRIFT: các chương chệch hướng/premise của khoảng truyện\n"
    "- PACING_FLAT: các chương lặp cùng một kiểu beat, nhịp không đổi\n"
    "- CROSS_CHAPTER_CONTRADICTION: hai chương tự phủ nhận (tóm tắt/văn mâu thuẫn)\n"
    "- ARC_CONTRACT: điều hứa ở đầu khoảng không được trả ở cuối\n"
    "Nếu khoảng chưa có văn (chỉ xương cảnh): báo OUTLINE_GAP (lỗ hổng dàn ý), "
    "BEAT_DUP (beat trùng), INTRO_MISSING (nhân vật/địa danh dùng chưa giới thiệu), "
    "PAYOFF_SETUP (hứa không có chuẩn bị).\n"
    "Trả JSON THUẦN (không markdown): [{\"chapter\": số chương hoặc null,"
    "\"severity\":\"error|warning\",\"code\":\"MÃ\",\"message\":\"gọn\","
    "\"suggestion\":\"ngắn\"}]. Không có lỗi thì trả []."
)

@router.post("/projects/{pid}/deep-check")
async def deep_check_range(pid:str,p:dict=Body(...),db:AsyncSession=Depends(get_db)):
    """Tạo job nền soi một KHOẢNG chương — trả job_id ngay (C10: bản đồng
    bộ vượt client-timeout). Poll GET /audit/jobs/{id}. Context chia tầng:
    summary + skeleton + mẫu prose mỗi chương + nguyên văn đầu/cuối (tier
    ≥ standard). 1 scope chỉ 1 job running (dedupe)."""
    await project_ok(db,pid)
    chs=sorted((await db.scalars(select(Chapter).where(Chapter.project_id==pid))).all(),
               key=lambda c:c.order_index)
    if not chs: raise HTTPException(400,"project has no chapters")
    fo=int(p.get("from_order") or chs[0].order_index)
    to=int(p.get("to_order") or chs[-1].order_index)
    if fo>to: raise HTTPException(400,"from_order > to_order")
    if not any(fo<=c.order_index<=to for c in chs):
        raise HTTPException(400,"no chapters in range")
    scope=f"{fo}-{to}"
    running=(await db.scalars(select(AuditJob).where(
        AuditJob.project_id==pid,AuditJob.scope_type=="range",
        AuditJob.scope_id==scope,AuditJob.status=="running"))).first()
    if running:
        if await _reap_stale_job(db, running):
            pass
        else:
            return {"job_id":running.id,"status":"running","dedup":True}
    job=AuditJob(project_id=pid,scope_type="range",scope_id=scope)
    db.add(job); await db.commit(); await db.refresh(job)
    _spawn_job(_audit_job_run(
        job.id,lambda s: _deep_check_range_work(s,pid,fo,to,job.id)))
    return {"job_id":job.id,"status":"running"}


async def _deep_check_range_work(db:AsyncSession,pid:str,fo:int,to:int,
                                 job_id:str|None=None)->dict:
    """Thân soi khoảng — lỗi xuyên-chương mà check từng chương không thấy.
    Không ghi prose; findings là bản nháp, không phải canon."""
    chs=sorted((await db.scalars(select(Chapter).where(Chapter.project_id==pid))).all(),
               key=lambda c:c.order_index)
    in_range=[c for c in chs if fo<=c.order_index<=to]
    if not in_range: raise ValueError("no chapters in range")

    scs=list((await db.scalars(select(Scene)
        .where(Scene.chapter_id.in_([c.id for c in in_range]))
        .order_by(Scene.order_index))).all())
    scs_by_ch:dict[str,list]={}
    for s in scs: scs_by_ch.setdefault(s.chapter_id,[]).append(s)
    has_prose=any((s.prose or "").strip() for s in scs)
    has_outline=any((s.skeleton or "").strip() for s in scs)
    if not has_prose and not has_outline:
        raise HTTPException(400,"range has no prose or outline")
    mode="prose" if has_prose else "outline"

    from app.models.memory import StorySummary
    sums={r.scope_id:r for r in (await db.scalars(select(StorySummary)
        .where(StorySummary.project_id==pid,StorySummary.scope_type=="chapter",
               StorySummary.scope_id.in_([c.id for c in in_range])))).all()}
    threads=list((await db.scalars(select(Thread)
        .where(Thread.project_id==pid,Thread.status=="OPEN"))).all())
    beats=list((await db.scalars(select(ThreadBeat)
        .where(ThreadBeat.project_id==pid))).all())
    last_touch={}
    for b in beats:
        if b.narrative_order is not None:
            last_touch[b.thread_id]=max(last_touch.get(b.thread_id,0),b.narrative_order)
    thread_lines=[f'- "{t.title}" — chạm cuối chương {last_touch.get(t.id,"chưa từng")}'
                  for t in threads if last_touch.get(t.id,0)<=to]

    router=ModelRouter(db)
    tier=await router.provider_tier("review",pid)
    grp_len={"low":6500,"standard":16000}.get(tier,45000)
    edge_cap={"low":0,"standard":6000}.get(tier,20000)

    warnings=[]
    miss=sum(1 for c in in_range if c.id not in sums)
    stale=sum(1 for c in in_range if c.id in sums and sums[c.id].stale)
    if miss: warnings.append(f"{miss} chương thiếu tóm tắt — độ tin cậy giảm")
    if stale: warnings.append(f"{stale} tóm tắt đã cũ (văn đổi sau tóm tắt)")

    hdr=[f"=== SOI KHOẢNG: Chương {fo} → {to} ({len(in_range)} chương, mode={mode}) ==="]
    if thread_lines: hdr.append("Hố đang OPEN:\n"+"\n".join(thread_lines[:15]))
    olds=list((await db.scalars(select(AuditFinding)
        .where(AuditFinding.project_id==pid,AuditFinding.scope_type=="chapter",
               AuditFinding.status=="open"))).all())
    ch_by_id={c.id:c for c in in_range}
    known=[]
    for f in olds:
        c=ch_by_id.get(f.scope_id)
        if not c: continue
        for it in json.loads(f.issues_json or "[]")[:6]:
            known.append(f"Ch{c.order_index}: {str(it.get('message'))[:120]}")
    if known: hdr.append("Findings đã biết (ĐỪNG lặp):\n"+"\n".join(known[:20]))

    segs=[]
    for c in in_range:
        lines=[f"--- Chương {c.order_index}: \"{c.title}\""]
        ss=sums.get(c.id)
        if ss: lines.append(f"Tóm tắt{'(ĐÃ CŨ)' if ss.stale else ''}: {(ss.summary or '')[:700]}")
        skel=" | ".join((s.skeleton or "")[:180] for s in scs_by_ch.get(c.id,[]) if s.skeleton)
        if skel: lines.append(f"Xương: {skel[:700]}")
        full="\n\n".join(s.prose for s in scs_by_ch.get(c.id,[]) if (s.prose or "").strip())
        if full: lines.append(f"Mẫu văn: {full[:400]}")
        segs.append((c,"\n".join(lines),full))

    # nguyên văn chương đầu + cuối — chỗ mạch vào/ra hay gãy (tier low: bỏ)
    edge=[]
    if edge_cap and has_prose:
        edge_chs=[segs[0]]+([segs[-1]] if len(segs)>1 else [])
        for c,_,full in edge_chs:
            if full: edge.append(f"=== NGUYÊN VĂN Chương {c.order_index} ===\n{full[:edge_cap]}")

    prompts=[]; cur=list(hdr); curlen=len("\n\n".join(cur))
    for _,seg,_f in segs:
        if curlen+len(seg)+2>grp_len and len(cur)>len(hdr) and len(prompts)<5:
            prompts.append(cur); cur=list(hdr); curlen=len("\n\n".join(cur))
        cur.append(seg); curlen+=len(seg)+2
    for e in edge:
        if curlen+len(e)+2>grp_len and len(prompts)<5:
            prompts.append(cur); cur=list(hdr); curlen=len("\n\n".join(cur))
        cur.append(e); curlen+=len(e)+2
    prompts.append(cur)

    ord2id={c.order_index:c.id for c in in_range}
    found=[]; seen_msg=set(); replies=[]; provider=model=""; skipped=0
    t0=time.monotonic()
    for pi,prt in enumerate(prompts):
        prompt="\n\n".join(prt)+"\n\nTrả JSON theo schema đã nêu trong system."
        result=None
        for attempt in range(3):
            try:
                result=await router.complete(ModelRequest(task="review",prompt=prompt,
                    project_id=pid,system=_DEEP_RANGE_SYSTEM))
                break
            except RuntimeError:
                if attempt<2: await asyncio.sleep(4+attempt*6+random.uniform(0,3))
        if job_id:
            await _job_progress(db,job_id,progress=f"{pi+1}/{len(prompts)}",
                                provider=provider,model=model)
        if result is None: skipped+=1; continue
        provider,model=result.provider or "",result.model or ""
        txt=(result.text or "").strip(); replies.append(txt)
        m=re.search(r"\[.*\]",txt,re.DOTALL)
        if not m: continue
        try: raw=json.loads(m.group())
        except (json.JSONDecodeError,TypeError): continue
        for it in (raw if isinstance(raw,list) else []):
            if not isinstance(it,dict) or not it.get("message"): continue
            key=re.sub(r"\s+"," ",str(it["message"]))[:50].lower()
            if key in seen_msg: continue
            seen_msg.add(key)
            cord=it.get("chapter")
            try: cord=int(cord) if cord is not None else None
            except (TypeError,ValueError): cord=None
            found.append({"code":str(it.get("code") or "AI_REVIEW")[:40],
                "severity":it.get("severity") if it.get("severity") in("error","warning","info") else "warning",
                "message":str(it["message"])[:400],
                "suggestion":str(it.get("suggestion") or "")[:300],
                "chapter_id":ord2id.get(cord),"chapter_order":cord})

    # lọc motif tác giả đã đánh 'không phải lỗi' (dismissed)
    dismissed=await _dismissed_issue_keys(db,pid)
    if dismissed:
        found=[it for it in found if _issue_key(it) not in dismissed]
    f=AuditFinding(project_id=pid,scope_type="range",scope_id=f"{fo}-{to}",
                   issues_json=json.dumps(found,ensure_ascii=False))
    db.add(f)
    db.add(AiTurn(project_id=pid,scope_id=pid,task="deep_check_range",
                  prompt_excerpt=(f"[{len(prompts)} calls] "+hdr[0])[:4000],
                  reply_text="\n---\n".join(replies)[:20000],
                  provider=provider,model=model,
                  latency_ms=int((time.monotonic()-t0)*1000)))
    await db.commit()
    out={"finding_id":f.id,"issues":found,"count":len(found),"mode":mode,
         "from_order":fo,"to_order":to,"provider":provider,"model":model,
         "calls":len(prompts),"tier":tier,"warnings":warnings}
    if skipped: out["skipped_windows"]=skipped
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
    t0=time.monotonic()
    try:
        result=await ModelRouter(db).complete(
            ModelRequest(task="revision",prompt=prompt,project_id=pid,system=system))
    except RuntimeError as e: raise HTTPException(503,str(e))
    db.add(AiTurn(project_id=pid,scope_id=sid,task="ai_fix",
                  prompt_excerpt=prompt[:4000],reply_text=(result.text or "")[:20000],
                  provider=result.provider or "",model=result.model or "",
                  latency_ms=int((time.monotonic()-t0)*1000)))
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
    def _label(r):
        if r.scope_type=="range":
            a,_,b=(r.scope_id or "").partition("-")
            return f"Chương {a}–{b}" if a and b else "Khoảng chương"
        return None
    return {"findings":[{"id":r.id,"scope_type":r.scope_type,"scope_id":r.scope_id,
                         "scope_label":_label(r),
                         "chapter_title":chs.get(r.scope_id).title if r.scope_id in chs else None,
                         "chapter_order":chs.get(r.scope_id).order_index if r.scope_id in chs else None,
                         "status":r.status,
                         "issues":json.loads(r.issues_json or "[]"),"created_at":r.created_at}
                        for r in rows]}


def _dismiss_key(issues: list) -> str:
    """Khoá nhận diện motif finding — dismiss 1 lần thì deep-check sau skip
    finding trùng motif chủ đích (mục tiêu #10)."""
    parts = sorted(re.sub(r"\s+", " ", str(i.get("message", ""))).lower()[:80]
                   for i in issues if isinstance(i, dict))[:6]
    return "|".join(parts)[:120]


def _issue_key(it: dict) -> str:
    return re.sub(r"\s+", " ", str(it.get("message", ""))).lower()[:80]


async def _dismissed_issue_keys(db, pid: str) -> set:
    """Tập key issue đã bị tác giả đánh 'không phải lỗi' — deep-check lọc
    khỏi kết quả mới lẫn prompt 'findings đã biết'."""
    rows = list((await db.scalars(select(AuditFinding).where(
        AuditFinding.project_id == pid,
        AuditFinding.status == "dismissed"))).all())
    keys = set()
    for r in rows:
        for it in json.loads(r.issues_json or "[]"):
            if isinstance(it, dict):
                keys.add(_issue_key(it))
    return keys


@router.post("/projects/{pid}/audit/findings/{fid}/dismiss")
async def dismiss_finding(pid: str, fid: str,
                          db: AsyncSession = Depends(get_db)):
    """Đánh finding 'không phải lỗi' — tác giả giữ quyền quyết. Finding
    dismissed vẫn lưu (không xoá) + ghi dismiss_key để deep-check sau lọc
    motif trùng khỏi 'findings đã biết' lẫn kết quả mới."""
    r = await db.get(AuditFinding, fid)
    if not r or r.project_id != pid:
        raise HTTPException(404, "not found")
    r.status = "dismissed"
    r.dismiss_key = _dismiss_key(json.loads(r.issues_json or "[]"))
    await db.commit()
    return {"id": r.id, "status": r.status}


@router.post("/projects/{pid}/audit/findings/{fid}/reopen")
async def reopen_finding(pid: str, fid: str,
                         db: AsyncSession = Depends(get_db)):
    r = await db.get(AuditFinding, fid)
    if not r or r.project_id != pid:
        raise HTTPException(404, "not found")
    r.status = "open"
    r.dismiss_key = None
    await db.commit()
    return {"id": r.id, "status": r.status}


@router.delete("/audit/findings/{fid}")
async def delete_finding(fid:str,db:AsyncSession=Depends(get_db)):
    r=await db.get(AuditFinding,fid)
    if not r: raise HTTPException(404,"not found")
    await db.delete(r); await db.commit(); return {"ok":True}

# ---- AI turn history (audit trail mọi call ai/complete) ----
def _turn_out(t:AiTurn)->dict:
    return {"id":t.id,"task":t.task,"scope_id":t.scope_id,"provider":t.provider,
            "model":t.model,"prompt_excerpt":t.prompt_excerpt,"reply_text":t.reply_text,
            "latency_ms":t.latency_ms,
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
