"""Style rules — gu văn tác giả học từ phản hồi (port Novel Humanizer v3).

Lifecycle: candidate (AI suy ra) → confirmed (tác giả duyệt) → rejected |
superseded (khi bị rule mới thay). Chỉ confirmed có hiệu lực trong prompt —
tác giả luôn là người chốt, AI không tự nâng luật.
"""
import json,re,time
from datetime import datetime as _dt
from pathlib import Path

from fastapi import APIRouter,Depends,HTTPException,Body
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import Project
from app.models.story import StyleProfile
from app.models.discussion import StylePreference
from app.models.truth import CanonFact
from app.models.memory import AiTurn
from app.ai.router import ModelRouter,ModelRequest
from app.ai.compose import PRESET_IMPORT_SYSTEM
from app.services import style as style_svc

router=APIRouter()

PRESET_DIR=Path(__file__).resolve().parents[3]/"presets"

async def project_ok(db,pid):
    if not await db.get(Project,pid): raise HTTPException(404,"project not found")


def _out(r:StylePreference,prof:StyleProfile|None)->dict:
    return {"id":r.id,"profile_id":r.style_profile_id,
            "profile_name":prof.name if prof else None,
            "preference_type":r.preference_type,"pattern":r.pattern,
            "strength":r.strength,"status":r.status,"source":r.source,
            "attribute":r.attribute,"scope_type":r.scope_type,
            "scope_id":r.scope_id,"evidence":r.evidence,
            "supersedes_id":r.supersedes_id,"updated_at":r.updated_at}


async def _rules(db,pid):
    profs={p.id:p for p in (await db.scalars(select(StyleProfile).where(
        StyleProfile.project_id==pid))).all()}
    rows=list((await db.scalars(select(StylePreference).where(
        StylePreference.project_id==pid))).all())
    rows.sort(key=lambda r:(r.status!="candidate",r.status!="confirmed",
                            r.updated_at or "",r.id))
    return [_out(r,profs.get(r.style_profile_id)) for r in rows]


@router.get("/projects/{pid}/style-rules")
async def list_rules(pid:str,db:AsyncSession=Depends(get_db)):
    await project_ok(db,pid)
    rules=await _rules(db,pid)
    return {"rules":rules,
            "counts":{"confirmed":sum(1 for r in rules if r["status"]=="confirmed"),
                      "candidate":sum(1 for r in rules if r["status"]=="candidate"),
                      "rejected":sum(1 for r in rules if r["status"]=="rejected"),
                      "superseded":sum(1 for r in rules if r["status"]=="superseded")}}


@router.post("/projects/{pid}/style-rules")
async def create_rule(pid:str,p:dict=Body(...),db:AsyncSession=Depends(get_db)):
    """Luật tác giả chủ động khai → confirmed ngay (không hỏi duyệt lại)."""
    await project_ok(db,pid)
    pat=(p.get("pattern") or "").strip()
    if not pat: raise HTTPException(400,"pattern required")
    r=await style_svc.add_explicit_rule(
        db,pid,pat,attribute=(p.get("attribute") or None),
        strength=p.get("strength") or "PREFERRED",
        polarity=p.get("preference_type") or "prefer",
        scope_type=p.get("scope_type") or None,
        scope_id=p.get("scope_id") or None,
        evidence=p.get("evidence") or None,
        profile_id=p.get("profile_id") or None)
    return _out(r,await db.get(StyleProfile,r.style_profile_id))


async def _rule(db,pid,rid):
    r=await db.get(StylePreference,rid)
    if not r or r.project_id!=pid: raise HTTPException(404,"rule not found")
    return r

_VALID_STATUS={"candidate","confirmed","rejected","superseded"}

@router.patch("/projects/{pid}/style-rules/{rid}")
async def patch_rule(pid:str,rid:str,p:dict=Body(...),db:AsyncSession=Depends(get_db)):
    """Đổi status (confirm/reject/supersede/reopen→candidate) hoặc sửa field.
    supersede kèm supersede_with_id → rule mới trỏ ngược lại để giữ provenance."""
    await project_ok(db,pid)
    r=await _rule(db,pid,rid)
    st=p.get("status")
    if st is not None:
        if st not in _VALID_STATUS: raise HTTPException(400,"invalid status")
        if st=="superseded":
            sup=p.get("supersede_with_id")
            if sup:
                o=await db.get(StylePreference,sup)
                if not o or o.project_id!=pid: raise HTTPException(400,"bad supersede target")
                o.supersedes_id=None
        r.status=st
        if st=="superseded":
            r.supersedes_id=p.get("supersede_with_id")
    for k in ("pattern","attribute","strength","preference_type","scope_type","scope_id"):
        if k in p: setattr(r,k,p[k])
    r.updated_at=_dt.utcnow().isoformat()
    await db.commit(); await db.refresh(r)
    return _out(r,await db.get(StyleProfile,r.style_profile_id))


@router.delete("/projects/{pid}/style-rules/{rid}")
async def delete_rule(pid:str,rid:str,db:AsyncSession=Depends(get_db)):
    r=await _rule(db,pid,rid)
    await db.delete(r); await db.commit(); return {"deleted":True}


@router.post("/projects/{pid}/style-rules/learn")
async def learn_rule(pid:str,p:dict=Body(...),db:AsyncSession=Depends(get_db)):
    """Học gu từ tác giả. Hai hình thức:

    - {instruction} — tác giả nói rõ sở thích → rule confirmed (không cần duyệt)
    - {original, revised, comment?} — diff sửa của tác giả → AI trích
      CANDIDATE rules (chờ duyệt; ≥2 ví dụ độc lập mới đáng nâng scope —
      tác giả quyết khi confirm).
    """
    await project_ok(db,pid)
    ins=(p.get("instruction") or "").strip()
    orig=(p.get("original") or "").strip()
    rev=(p.get("revised") or "").strip()
    if ins:
        r=await style_svc.add_explicit_rule(
            db,pid,ins,
            attribute=p.get("attribute") or None,
            strength=p.get("strength") or "PREFERRED",
            polarity=p.get("preference_type") or "prefer")
        return {"created":"confirmed","rules":[_out(r,await db.get(StyleProfile,r.style_profile_id))]}
    if not (orig and rev):
        raise HTTPException(400,"need instruction or original+revised")
    if orig==rev:
        raise HTTPException(400,"original and revised are identical")
    router=ModelRouter(db)
    t0=time.monotonic()
    async def call(system,prompt,task):
        res=await router.complete(ModelRequest(task=task,prompt=prompt,
                                               project_id=pid,system=system))
        db.add(AiTurn(project_id=pid,scope_id=p.get("scene_id") or pid,
                      task=task,prompt_excerpt=prompt[:4000],
                      reply_text=(res.text or "")[:20000],
                      provider=res.provider or "",model=res.model or "",
                      latency_ms=int((time.monotonic()-t0)*1000)))
        await db.commit()
        return res.text or ""
    try:
        made=await style_svc.learn_from_diff(
            db,pid,orig,rev,(p.get("comment") or "").strip() or None,call)
    except RuntimeError as e:
        raise HTTPException(503,str(e))
    profs={pp.id:pp for pp in (await db.scalars(select(StyleProfile).where(
        StyleProfile.project_id==pid))).all()}
    return {"created":"candidates","rules":[_out(r,profs.get(r.style_profile_id)) for r in made]}


# ---- Preset import: style-guide/preset văn bản → đề xuất profiles+rules+canon ----

@router.get("/projects/{pid}/style/presets")
async def list_presets(pid:str,db:AsyncSession=Depends(get_db)):
    """Preset đóng gói sẵn trong backend/presets/."""
    await project_ok(db,pid)
    out=[]
    if PRESET_DIR.is_dir():
        for f in sorted(PRESET_DIR.glob("*.md")):
            head=f.read_text(encoding="utf-8",errors="replace")[:400]
            title=head.splitlines()[0].lstrip("# ")[:120] if head else f.stem
            out.append({"name":f.stem,"title":title})
    return {"presets":out}


def _parse_json_obj(txt:str)->dict:
    m=re.search(r"\{.*\}",txt or "",re.DOTALL)
    if not m: return {}
    try: return json.loads(m.group())
    except Exception: return {}


@router.post("/projects/{pid}/style/import-preset")
async def import_preset(pid:str,p:dict=Body(...),db:AsyncSession=Depends(get_db)):
    """Preset text (hoặc preset đóng gói theo name) → AI trích ĐỀ XUẤT
    {profiles, rules, canon_facts}. KHÔNG ghi DB — tác giả duyệt qua
    POST apply-preset với phần đã chọn."""
    await project_ok(db,pid)
    text=(p.get("text") or "").strip()
    name=(p.get("preset_name") or "").strip()
    if not text and name:
        f=PRESET_DIR/f"{name}.md"
        if not f.is_file(): raise HTTPException(404,"preset not found")
        text=f.read_text(encoding="utf-8",errors="replace")
    if not text: raise HTTPException(400,"need text or preset_name")
    router=ModelRouter(db)
    t0=time.monotonic()
    try:
        res=await router.complete(ModelRequest(
            task="preset_import",
            prompt=f"=== PRESET ===\n{text[:24000]}\n\nTrích theo schema system.",
            project_id=pid,system=PRESET_IMPORT_SYSTEM))
    except RuntimeError as e:
        raise HTTPException(503,str(e))
    db.add(AiTurn(project_id=pid,scope_id=pid,task="preset_import",
                  prompt_excerpt=text[:4000],reply_text=(res.text or "")[:20000],
                  provider=res.provider or "",model=res.model or "",
                  latency_ms=int((time.monotonic()-t0)*1000)))
    data=_parse_json_obj(res.text or "")
    out={"profiles":[x for x in (data.get("profiles") or [])[:6] if isinstance(x,dict)],
         "rules":[x for x in (data.get("rules") or [])[:30] if isinstance(x,dict)],
         "canon_facts":[x for x in (data.get("canon_facts") or [])[:30] if isinstance(x,dict)],
         "provider":res.provider,"model":res.model}
    await db.commit()
    return out


@router.post("/projects/{pid}/style/apply-preset")
async def apply_preset(pid:str,p:dict=Body(...),db:AsyncSession=Depends(get_db)):
    """Ghi phần tác giả ĐÃ CHỌN từ import-preset. Profiles tạo mới (active),
    rules → confirmed nguồn 'preset' trong profile tương ứng (hoặc profile
    'AI tự học' nếu không chỉ định), canon_facts → CanonFact truth_status
    'CANON' với subject_type 'world'."""
    await project_ok(db,pid)
    made={"profiles":0,"rules":0,"canon_facts":0}
    # idempotent: profile trùng tên → tái dùng; rule trùng pattern → bỏ qua
    have_prof={ (x.name or "").strip().lower():x for x in (await db.scalars(
        select(StyleProfile).where(StyleProfile.project_id==pid))).all()}
    have_pat={ (x.pattern or "").strip().lower() for x in (await db.scalars(
        select(StylePreference).where(StylePreference.project_id==pid))).all()}
    prof_map:dict[int,StyleProfile]={}
    for i,d in enumerate(p.get("profiles") or []):
        nm=(d.get("name") or "").strip()
        if not nm: continue
        ex=have_prof.get(nm.lower())
        if ex:
            prof_map[i]=ex
            if (d.get("instructions") or "").strip() and not (ex.instructions or "").strip():
                ex.instructions=(d.get("instructions") or "")[:4000]
            continue
        pr=StyleProfile(project_id=pid,name=nm[:240],scope_type="global",
                        active=True,instructions=(d.get("instructions") or "")[:4000])
        db.add(pr); await db.flush()
        have_prof[nm.lower()]=pr
        prof_map[i]=pr; made["profiles"]+=1
    default_prof=None
    for d in p.get("rules") or []:
        pat=(d.get("pattern") or "").strip()
        if not pat or pat.lower() in have_pat: continue
        have_pat.add(pat.lower())
        pi=d.get("profile_index")
        prof=prof_map.get(pi) if isinstance(pi,int) else None
        if not prof:
            if not default_prof:
                default_prof=await style_svc._learning_profile(db,pid)
            prof=default_prof
        db.add(StylePreference(
            project_id=pid,style_profile_id=prof.id,
            preference_type=d.get("preference_type") if d.get("preference_type") in ("prefer","avoid") else "prefer",
            pattern=pat[:600],
            strength=d.get("strength") if d.get("strength") in ("HARD","PREFERRED","AVOID","OPEN") else "PREFERRED",
            status="confirmed",source="preset",
            attribute=(d.get("attribute") or "")[:80] or None,
            evidence=(d.get("evidence") or "")[:800] or None,
            updated_at=_dt.utcnow().isoformat()))
        made["rules"]+=1
    have_fact={ ((x.predicate or "").strip().lower(),(x.value_text or "").strip().lower())
                for x in (await db.scalars(select(CanonFact).where(
                    CanonFact.project_id==pid))).all()}
    for d in p.get("canon_facts") or []:
        pred=(d.get("predicate") or "").strip()
        val=(d.get("value_text") or "").strip()
        if not pred or not val or (pred.lower(),val.lower()) in have_fact: continue
        have_fact.add((pred.lower(),val.lower()))
        db.add(CanonFact(project_id=pid,subject_type="world",
                         predicate=pred[:240],value_text=val[:800],
                         truth_status="CANON"))
        made["canon_facts"]+=1
    await db.commit()
    return {"applied":made}
