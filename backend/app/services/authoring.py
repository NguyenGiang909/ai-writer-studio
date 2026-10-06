"""AI Authoring engine — deterministic pipeline, học từ ainovel-cli.

Nguyên tắc: toàn bộ tiến độ trong DB (authoring_runs + authoring_steps),
engine stateless → next_step(run, facts) là hàm thuần quyết định bước kế.
Crash/restart → đọc lại DB là tiếp tục được.

Phases: premise → cast → world → outline → writing → complete.
Hết mỗi phase → status=awaiting_review (checkpoint chờ tác giả duyệt).
Trong phase chạy hết (auto-run); pause = dừng giữa các step.
"""
import asyncio
import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal
from app.models import (
    Project, Volume, Arc, Chapter, Scene,
    Character, Alias, Location, Faction, Item, Ability, WorldEntity,
    Relationship, StyleProfile,
)
from app.models.authoring import AuthoringRun, AuthoringStep, EntityProvenance
from app.models.truth import StoryEvent, StoryState, CanonFact
from app.models.narrative import Thread, ThreadBeat
from app.models.memory import AiTurn
from app.ai.router import ModelRouter, ModelRequest
from app.ai.compose import build_story_prompt

PHASES = ["premise", "cast", "world", "outline", "writing"]

# prefix step_key thuộc từng phase — dùng check "phase này có làm việc không"
_PHASE_STEP_PREFIX = {
    "premise": "premise.",
    "cast": "cast.",
    "world": "world.",
    "outline": ("outline.", "chapter_scenes."),
    "writing": ("scene_write.", "chapter_facts."),
}


@dataclass
class Step:
    key: str            # vd "premise.generate", "chapter_facts.<chapter_id>"
    task: str           # ai task name cho ModelRouter
    detail: str         # mô tả người đọc
    ref_id: str | None = None   # chapter_id/scene_id nếu có


@dataclass
class Facts:
    done: set[str] = field(default_factory=set)        # step_keys đã xong (toàn project, idempotent xuyên run)
    run_done: set[str] = field(default_factory=set)    # step_keys xong trong run này (checkpoint detection)
    failed: dict[str, int] = field(default_factory=dict)  # step_key → số lần fail (run này)
    chapters: list = field(default_factory=list)       # ordered
    scenes_by_chapter: dict = field(default_factory=dict)
    has_premise: bool = False
    has_cast: bool = False
    has_world: bool = False


async def load_facts(db: AsyncSession, run: AuthoringRun) -> Facts:
    """IO boundary — đọc hết facts route cần. next_step giữ thuần.

    done/project_id: step đã xong ở BẤT KỲ run nào của project → không làm lại
    (chapter_facts tránh trích trùng, scene_write/chapter_scenes tự idempotent
    qua trạng thái entity). failed/run_id: chỉ đếm lỗi của run hiện tại."""
    steps = (await db.scalars(select(AuthoringStep).where(
        AuthoringStep.project_id == run.project_id))).all()
    chapters = list((await db.scalars(select(Chapter).where(
        Chapter.project_id == run.project_id).order_by(Chapter.order_index))).all())
    scenes = list((await db.scalars(select(Scene).where(
        Scene.project_id == run.project_id).order_by(Scene.order_index))).all())
    by_ch: dict[str, list] = {}
    for sc in scenes:
        by_ch.setdefault(sc.chapter_id, []).append(sc)
    proj = await db.get(Project, run.project_id)
    n_chars = await db.scalar(select(func.count(Character.id)).where(
        Character.project_id == run.project_id))
    n_world = 0
    for m in (Location, Faction, Item, Ability, WorldEntity):
        n_world += await db.scalar(select(func.count(m.id)).where(
            m.project_id == run.project_id)) or 0
    failed: dict[str, int] = {}
    for s in steps:
        if s.status == "failed" and s.run_id == run.id:
            failed[s.step_key] = failed.get(s.step_key, 0) + 1
    return Facts(done={s.step_key for s in steps if s.status == "done"},
                 run_done={s.step_key for s in steps
                           if s.status == "done" and s.run_id == run.id},
                 failed=failed, chapters=chapters, scenes_by_chapter=by_ch,
                 has_premise=bool((proj.description or "").strip()) if proj else False,
                 has_cast=bool(n_chars), has_world=n_world > 0)


def next_step(run: AuthoringRun, f: Facts) -> Step | None:
    """Pure route — trả None khi phase hiện tại đã hết việc (checkpoint/complete).

    Continue-mode: stage đã có dữ liệu sẵn (tác giả viết tay / run trước) → bỏ qua,
    chỉ làm phần còn thiếu."""
    ph = run.phase
    if ph == "premise":
        if not f.has_premise and "premise.generate" not in f.done:
            return Step("premise.generate", "premise", "Sinh premise + thể loại + tone")
        return None
    if ph == "cast":
        if not f.has_cast and "cast.generate" not in f.done:
            return Step("cast.generate", "cast_gen", "Sinh nhân vật + quan hệ")
        return None
    if ph == "world":
        if not f.has_world and "world.generate" not in f.done:
            return Step("world.generate", "world_gen", "Sinh địa điểm + thế lực + vật/lore")
        return None
    if ph == "outline":
        if not f.chapters and "outline.generate" not in f.done:
            return Step("outline.generate", "book_outline", "Sinh khung Quyển/Hồi/Chương")
        for ch in f.chapters:
            if not f.scenes_by_chapter.get(ch.id) and f"chapter_scenes.{ch.id}" not in f.done:
                return Step(f"chapter_scenes.{ch.id}", "chapter_outline",
                            f"Dàn cảnh cho chương {ch.order_index}: {ch.title}", ch.id)
        return None
    if ph == "writing":
        for ch in f.chapters:
            scenes = f.scenes_by_chapter.get(ch.id, [])
            for sc in scenes:
                if not (sc.prose or "").strip() and f"scene_write.{sc.id}" not in f.done:
                    return Step(f"scene_write.{sc.id}", "scene_expand",
                                f"Viết cảnh “{sc.title or '?'}” (chương {ch.order_index})", sc.id)
            if scenes and f"chapter_facts.{ch.id}" not in f.done:
                return Step(f"chapter_facts.{ch.id}", "chapter_facts",
                            f"Trích facts chương {ch.order_index}", ch.id)
        return None
    return None


async def mark_done(db, run, step: Step, output: dict | None = None):
    db.add(AuthoringStep(run_id=run.id, project_id=run.project_id,
                         step_key=step.key, status="done",
                         output_json=json.dumps(output, ensure_ascii=False) if output else None,
                         finished_at=datetime.utcnow()))


async def mark_failed(db, run, step: Step, err: str):
    db.add(AuthoringStep(run_id=run.id, project_id=run.project_id,
                         step_key=step.key, status="failed", error=err[:2000],
                         finished_at=datetime.utcnow()))


def provenance(db, run, entity_type: str, entity_id: str):
    db.add(EntityProvenance(project_id=run.project_id, entity_type=entity_type,
                            entity_id=entity_id, run_id=run.id, origin="ai"))


async def ai_call(db, run, task: str, prompt: str, system=None, scene_id=None,
                  chapter_id=None) -> tuple[dict | str, str]:
    """Gọi model qua router + ghi AiTurn. Trả (text|json, provider).

    run.prompt = định hướng tác giả cho cả run → prepend vào mọi task
    (premise tự đưa prompt vào input rồi, khỏi lặp)."""
    sys_prompt, body, _ = await build_story_prompt(db, run.project_id, task, prompt,
                                                 scene_id=scene_id, chapter_id=chapter_id)
    if task != "premise" and (run.prompt or "").strip():
        body = f"=== ĐỊNH HƯỚNG CỦA TÁC GIẢ ===\n{run.prompt.strip()}\n\n{body}"
    result = await ModelRouter(db).complete(ModelRequest(
        task=task, prompt=body, project_id=run.project_id,
        system=system or sys_prompt))
    db.add(AiTurn(project_id=run.project_id, scope_id=run.id, task=task,
                  prompt_excerpt=body[:1500], reply_text=(result.text or "")[:4000],
                  provider=result.provider or "", model=result.model or ""))
    return result.text or "", result.provider or ""


def parse_json(text: str) -> dict:
    t = (text or "").strip()
    if "```" in t:
        t = t.split("```", 2)[1]
        if t.startswith("json"):
            t = t[4:]
        t = t.split("```")[0]
    try:
        return json.loads(t)
    except Exception:
        a, b = t.find("{"), t.rfind("}")
        try:
            return json.loads(t[a:b + 1]) if a >= 0 and b > a else {}
        except Exception:
            return {}


def _clip(s: str | None, n: int) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[:n] + "…"


# ---------- handlers ----------

async def h_premise(db, run, step):
    p = await db.get(Project, run.project_id)
    text, _prov = await ai_call(db, run, "premise",
        f"Ý tưởng của tác giả: {run.prompt}\n\nSinh premise đầy đủ theo schema.")
    data = parse_json(text)
    if not data:
        raise ValueError("model không trả JSON premise hợp lệ")
    if data.get("title") and p and not p.description:
        # chỉ đặt tên khi project còn rỗng — không ghi đè tên tác giả đặt
        if (p.name or "").startswith("Truyện mới"):
            p.name = _clip(data["title"], 240)
    if p:
        p.description = _clip(data.get("premise") or data.get("logline"), 2000)
    run.stage_payload_json = json.dumps(data, ensure_ascii=False)
    # premise là context bền cho mọi stage sau — giữ riêng trong cursor_json
    # vì stage_payload_json bị stage kế ghi đè
    run.cursor_json = run.stage_payload_json
    return {"title": data.get("title"), "genre": data.get("genre")}


def _premise_ctx(run) -> dict:
    """Premise JSON bền — cursor_json trước, fallback stage_payload (run cũ)."""
    return json.loads(run.cursor_json or run.stage_payload_json or "{}")


async def h_cast(db, run, step):
    premise = _premise_ctx(run)
    existing = [c.name for c in (await db.scalars(select(Character).where(
        Character.project_id == run.project_id))).all()]
    prompt = (f"=== PREMISE ===\n{json.dumps(premise, ensure_ascii=False)}\n\n"
              f"=== NHÂN VẬT ĐÃ CÓ (không tạo lại) ===\n" + (", ".join(existing) or "(chưa có)")
              + "\n\nSinh dàn nhân vật theo schema.")
    text, _ = await ai_call(db, run, "cast_gen", prompt)
    data = parse_json(text)
    if not data.get("characters"):
        raise ValueError("model không trả danh sách nhân vật hợp lệ")
    created = {}
    for c in (data.get("characters") or [])[:20]:
        name = (c.get("name") or "").strip()
        if not name or name in created or name in existing:
            continue
        imp = c.get("importance")
        # app bucket 0-3 (0=quan trọng nhất); model hay trả 1-5 → map về 0-3
        if isinstance(imp, int):
            imp = min(3, max(0, round((5 - imp) * 3 / 4))) if imp > 3 else imp
        else:
            imp = None
        ch = Character(project_id=run.project_id, name=name, role=_clip(c.get("role"), 64),
                       summary=c.get("summary"), voice_notes=c.get("voice_notes"),
                       status=c.get("status") or "active",
                       importance=imp, sort_order=len(created))
        db.add(ch); await db.flush()
        provenance(db, run, "character", ch.id)
        for a in (c.get("aliases") or [])[:5]:
            a = (a or "").strip()
            if a:
                al = Alias(project_id=run.project_id, character_id=ch.id, alias=a)
                db.add(al); await db.flush()
                provenance(db, run, "alias", al.id)
        created[name] = ch
    for r in (data.get("relationships") or [])[:30]:
        a = created.get((r.get("a") or "").strip())
        b = created.get((r.get("b") or "").strip())
        if not a or not b or a.id == b.id:
            continue
        rel = Relationship(project_id=run.project_id, source_character_id=a.id,
                           target_character_id=b.id,
                           relationship_type=_clip(r.get("type"), 64) or "liên quan",
                           notes=r.get("notes"))
        db.add(rel); await db.flush()
        provenance(db, run, "relationship", rel.id)
    run.stage_payload_json = json.dumps({"characters": list(created)}, ensure_ascii=False)
    return {"characters": len(created)}


async def h_world(db, run, step):
    premise = _premise_ctx(run)
    chars = [c.name for c in (await db.scalars(select(Character).where(
        Character.project_id == run.project_id))).all()]
    prompt = (f"=== PREMISE ===\n{json.dumps(premise, ensure_ascii=False)}\n\n"
              f"=== NHÂN VẬT ===\n" + ", ".join(chars[:20])
              + "\n\nSinh thế giới theo schema.")
    text, _ = await ai_call(db, run, "world_gen", prompt)
    data = parse_json(text)
    n = 0
    for loc in (data.get("locations") or [])[:20]:
        name = (loc.get("name") or "").strip()
        if not name:
            continue
        lo = Location(project_id=run.project_id, name=name, description=loc.get("description"))
        db.add(lo); await db.flush(); provenance(db, run, "location", lo.id); n += 1
    for fct in (data.get("factions") or [])[:15]:
        name = (fct.get("name") or "").strip()
        if not name:
            continue
        fa = Faction(project_id=run.project_id, name=name, description=fct.get("description"))
        db.add(fa); await db.flush(); provenance(db, run, "faction", fa.id); n += 1
    for it in (data.get("items") or [])[:15]:
        name = (it.get("name") or "").strip()
        if not name:
            continue
        io_ = Item(project_id=run.project_id, name=name, description=it.get("description"))
        db.add(io_); await db.flush(); provenance(db, run, "item", io_.id); n += 1
    for ab in (data.get("abilities") or [])[:15]:
        name = (ab.get("name") or "").strip()
        if not name:
            continue
        abo = Ability(project_id=run.project_id, name=name,
                      ability_type=_clip(ab.get("type"), 64), can_do=ab.get("can_do"),
                      cannot_do=ab.get("cannot_do"), limits=ab.get("limits"),
                      cost=ab.get("cost"), conditions=ab.get("conditions"))
        db.add(abo); await db.flush(); provenance(db, run, "ability", abo.id); n += 1
    for we in (data.get("lore") or [])[:15]:
        name = (we.get("name") or "").strip()
        if not name:
            continue
        w = WorldEntity(project_id=run.project_id, name=name,
                        entity_type=_clip(we.get("type"), 64) or "lore",
                        description=we.get("description"))
        db.add(w); await db.flush(); provenance(db, run, "world_entity", w.id); n += 1
    if data.get("style"):
        sp = StyleProfile(project_id=run.project_id, name="AI default",
                          scope_type="global", instructions=_clip(json.dumps(
                              data["style"], ensure_ascii=False), 2000))
        db.add(sp); await db.flush(); provenance(db, run, "style_profile", sp.id)
    run.stage_payload_json = json.dumps(
        {"locations": len(data.get("locations") or []),
         "factions": len(data.get("factions") or []), "created": n}, ensure_ascii=False)
    return {"created": n}


async def h_outline(db, run, step):
    premise = _premise_ctx(run)
    chars = [c.name for c in (await db.scalars(select(Character).where(
        Character.project_id == run.project_id))).all()]
    goal = (f"\n\n=== MỤC TIÊU ===\nTổng số chương mong muốn: ~{run.target_chapters}. "
            f"Dàn quyển/hồi/chương sát mục tiêu này (được lệch nếu cốt truyện cần)."
            if run.target_chapters else "")
    prompt = (f"=== PREMISE ===\n{json.dumps(premise, ensure_ascii=False)}\n\n"
              f"=== NHÂN VẬT ===\n" + ", ".join(chars[:20])
              + goal + "\n\nSinh khung truyện theo schema.")
    text, _ = await ai_call(db, run, "book_outline", prompt)
    data = parse_json(text)
    vols = data.get("volumes") or []
    if not vols:
        raise ValueError("model không trả outline hợp lệ")
    n_ch = 0
    ch_order = 0
    for vi, v in enumerate(vols[:10], start=1):
        vol = Volume(project_id=run.project_id, title=_clip(v.get("title"), 240) or f"Quyển {vi}",
                     order_index=vi)
        db.add(vol); await db.flush(); provenance(db, run, "volume", vol.id)
        for ai_, a in enumerate((v.get("arcs") or [])[:10], start=1):
            arc = Arc(project_id=run.project_id, volume_id=vol.id,
                      title=_clip(a.get("title"), 240) or f"Hồi {ai_}", order_index=ai_)
            db.add(arc); await db.flush(); provenance(db, run, "arc", arc.id)
            for c in (a.get("chapters") or [])[:40]:
                ch_order += 1
                ch = Chapter(project_id=run.project_id, volume_id=vol.id, arc_id=arc.id,
                             title=_clip(c.get("title"), 240) or f"Chương {ch_order}",
                             order_index=ch_order, status="draft")
                db.add(ch); await db.flush(); provenance(db, run, "chapter", ch.id)
                if c.get("beat"):
                    # giữ beat trong skeleton của chương-level? Chapter không có field —
                    # để vào chapter title không; beat dùng khi dàn cảnh (chapter_scenes step)
                    pass
                n_ch += 1
    run.stage_payload_json = json.dumps(
        {"volumes": len(vols), "chapters": n_ch}, ensure_ascii=False)
    return {"volumes": len(vols), "chapters": n_ch}


async def h_chapter_scenes(db, run, step):
    ch = await db.get(Chapter, step.ref_id)
    if not ch:
        raise ValueError("chapter không tồn tại")
    text, _ = await ai_call(db, run, "chapter_outline", "", chapter_id=ch.id)
    created = []
    existing = (await db.scalars(select(Scene).where(
        Scene.chapter_id == ch.id).order_by(Scene.order_index))).all()
    max_o = max((s.order_index for s in existing), default=-1)
    for line in (text or "").splitlines():
        line = line.strip().lstrip("-•*0123456789. ").strip()
        if not line:
            continue
        title, _, beat = line.partition("—")
        if not beat:
            title, _, beat = line.partition("-")
        max_o += 1
        sc = Scene(project_id=run.project_id, chapter_id=ch.id,
                   title=_clip(title.strip(), 240) or f"Cảnh {max_o + 1}",
                   order_index=max_o, skeleton=beat.strip() or None)
        db.add(sc); await db.flush(); provenance(db, run, "scene", sc.id)
        created.append(sc.title)
    run.stage_payload_json = json.dumps({"chapter": ch.order_index, "scenes": created},
                                        ensure_ascii=False)
    return {"scenes": len(created)}


async def h_scene_write(db, run, step):
    sc = await db.get(Scene, step.ref_id)
    if not sc:
        raise ValueError("scene không tồn tại")
    brief = sc.skeleton or sc.title or "Viết cảnh này."
    w = run.words_per_scene or 900
    prompt = (f"Viết cảnh “{sc.title or 'Cảnh'}”.\nXương cảnh/beat: {brief}\n"
              f"Độ dài mục tiêu ~{w} chữ. Xuất DUY NHẤT văn xuôi.")
    text, _ = await ai_call(db, run, "scene_expand", prompt, scene_id=sc.id)
    text = (text or "").strip()
    if len(text) < 40:
        raise ValueError("prose sinh ra quá ngắn")
    sc.prose = text
    return {"chars": len(text)}


async def h_chapter_facts(db, run, step):
    """Commit ritual — trích facts từ prose chương vào story tables (như ainovel ChapterFacts)."""
    ch = await db.get(Chapter, step.ref_id)
    scenes = [s for s in (await db.scalars(select(Scene).where(
        Scene.chapter_id == ch.id).order_by(Scene.order_index))).all()]
    prose = "\n\n".join(s.prose for s in scenes if s.prose)[:16000]
    if not prose.strip():
        raise ValueError("chapter chưa có prose")
    chars = {c.name: c for c in (await db.scalars(select(Character).where(
        Character.project_id == run.project_id))).all()}
    locs = {l.name: l for l in (await db.scalars(select(Location).where(
        Location.project_id == run.project_id))).all()}
    threads = {t.title: t for t in (await db.scalars(select(Thread).where(
        Thread.project_id == run.project_id))).all()}
    prompt = (f"=== CHƯƠNG {ch.order_index}: {ch.title} ===\n{prose}\n\n"
              f"=== NHÂN VẬT ĐÃ BIẾT ===\n" + ", ".join(chars)[:800] + "\n\n"
              f"=== THREAD ĐANG MỞ ===\n" + ", ".join(threads)[:400] + "\n\n"
              "Trích facts theo schema chapter_facts.")
    text, _ = await ai_call(db, run, "chapter_facts", prompt)
    data = parse_json(text)
    n = 0
    narr = ch.order_index
    for e in (data.get("timeline_events") or [])[:15]:
        ev = StoryEvent(project_id=run.project_id, scene_id=scenes[0].id if scenes else None,
                        event_type=_clip(e.get("event_type"), 64) or "event",
                        summary=_clip(e.get("event") or e.get("summary"), 500) or "?",
                        story_time=e.get("story_time"), narrative_order=narr)
        db.add(ev); await db.flush(); provenance(db, run, "story_event", ev.id); n += 1
    for s_ in (data.get("state_changes") or [])[:20]:
        ent_name = (s_.get("entity") or "").strip()
        ent = chars.get(ent_name) or locs.get(ent_name)
        etype = "character" if ent_name in chars else ("location" if ent_name in locs else "other")
        st = StoryState(project_id=run.project_id, entity_type=etype,
                        entity_id=ent.id if ent else uuid.uuid4().hex,
                        key=_clip(s_.get("field") or s_.get("key"), 120) or "state",
                        value_text=_clip(s_.get("new_value") or s_.get("value"), 400) or "?",
                        story_time=s_.get("story_time"), narrative_order=narr)
        db.add(st); await db.flush(); provenance(db, run, "story_state", st.id); n += 1
    for t_ in (data.get("thread_touches") or data.get("foreshadow_updates") or [])[:15]:
        title = (t_.get("thread") or t_.get("thread_title") or t_.get("id") or "").strip()
        if not title:
            continue
        th = threads.get(title)
        if not th:
            th = Thread(project_id=run.project_id, title=title,
                        thread_type=_clip(t_.get("thread_type"), 32) or "mystery",
                        status="OPEN", description=t_.get("description"))
            db.add(th); await db.flush(); threads[title] = th
            provenance(db, run, "thread", th.id)
        beat = ThreadBeat(project_id=run.project_id, thread_id=th.id,
                          scene_id=scenes[0].id if scenes else None,
                          beat_type=_clip(t_.get("action") or t_.get("beat_type"), 24) or "reinforcement",
                          narrative_order=narr, notes=_clip(t_.get("description") or t_.get("note"), 300))
        db.add(beat); await db.flush(); provenance(db, run, "thread_beat", beat.id); n += 1
    for f_ in (data.get("canon_facts") or [])[:15]:
        cf = CanonFact(project_id=run.project_id,
                       subject_type=_clip(f_.get("subject_type"), 64) or "story",
                       predicate=_clip(f_.get("predicate"), 120) or "fact",
                       value_text=_clip(f_.get("value_text"), 500) or "?",
                       truth_status="CANON",
                       source_scene_id=scenes[0].id if scenes else None)
        db.add(cf); await db.flush(); provenance(db, run, "canon_fact", cf.id); n += 1
    return {"facts": n}


HANDLERS = {
    "premise": h_premise, "cast_gen": h_cast, "world_gen": h_world,
    "book_outline": h_outline, "chapter_outline": h_chapter_scenes,
    "scene_expand": h_scene_write, "chapter_facts": h_chapter_facts,
}

# ---------- runner ----------

_live: dict[str, asyncio.Task] = {}


async def tick(run_id: str) -> str:
    """Một vòng: load run → check status → route → execute → commit.
    Trả 'step' | 'checkpoint' | 'complete' | 'stopped'."""
    async with SessionLocal() as db:
        run = await db.get(AuthoringRun, run_id)
        if not run or run.status != "running":
            return "stopped"
        facts = await load_facts(db, run)
        step = next_step(run, facts)
        if step is not None and facts.failed.get(step.key, 0) >= 2:
            run.status = "failed"
            run.last_error = f"{step.key}: fail quá 2 lần — cần sửa rồi resume"
            await db.commit()
            return "stopped"
        if step is None:
            # phase không sinh step nào trong run này (= dữ liệu có sẵn, skip)
            # → tự sang phase kế, không bắt tác giả duyệt checkpoint rỗng
            produced = any(k.startswith(_PHASE_STEP_PREFIX[run.phase])
                           for k in facts.run_done)
            idx = PHASES.index(run.phase)
            if idx >= len(PHASES) - 1:
                run.status = "complete"
            elif not produced:
                run.phase = PHASES[idx + 1]
            else:
                run.status = "awaiting_review"
            await db.commit()
            if run.status == "running":
                return "step"  # loop tiếp trong phase mới
            return "complete" if run.status == "complete" else "checkpoint"
        try:
            out = await HANDLERS[step.task](db, run, step)
            await mark_done(db, run, step, out)
            run.last_error = None
        except Exception as e:  # noqa: BLE001 — step fail không giết run
            await mark_failed(db, run, step, str(e))
            run.last_error = f"{step.key}: {e}"
        await db.commit()
        return "step"


async def _loop(run_id: str):
    try:
        while True:
            r = await tick(run_id)
            if r != "step":
                return
            await asyncio.sleep(0)  # nhường event loop
    finally:
        _live.pop(run_id, None)


def spawn(run_id: str):
    """Khởi động/tiếp tục background loop. Idempotent — không spawn trùng."""
    t = _live.get(run_id)
    if t is None or t.done():
        _live[run_id] = asyncio.create_task(_loop(run_id))


# ---------- regenerate ----------

# entity con xoá trước cha (FK); writing KHÔNG regenerate được (phá prose + facts)
_REGEN_TYPES = {
    "premise": [],
    "cast": ["relationship", "alias", "character"],
    "world": ["location", "faction", "item", "ability", "world_entity", "style_profile"],
    "outline": ["scene", "chapter", "arc", "volume"],
}
_REGEN_STEPS = {
    "premise": ["premise.generate"],
    "cast": ["cast.generate"],
    "world": ["world.generate"],
    "outline": ["outline.generate", "chapter_scenes."],
}
_ENTITY_MODEL = {
    "character": Character, "alias": Alias, "relationship": Relationship,
    "location": Location, "faction": Faction, "item": Item,
    "ability": Ability, "world_entity": WorldEntity, "style_profile": StyleProfile,
    "scene": Scene, "chapter": Chapter, "arc": Arc, "volume": Volume,
}


async def regenerate(db: AsyncSession, run: AuthoringRun, hint: str | None = None):
    """Tạo lại stage hiện tại khi đang checkpoint — xoá entity AI của stage,
    xoá step đã xong, đưa hint vào premise context, rồi chạy lại."""
    phase = run.phase
    if phase not in _REGEN_TYPES:
        raise ValueError("không thể tạo lại stage writing — prose/facts đã ghi")
    for et in _REGEN_TYPES[phase]:
        model = _ENTITY_MODEL[et]
        ids = list((await db.scalars(select(EntityProvenance.entity_id).where(
            EntityProvenance.run_id == run.id,
            EntityProvenance.entity_type == et))).all())
        if not ids:
            continue
        if et == "scene":
            from app.models.manuscript import SceneVersion
            await db.execute(delete(SceneVersion).where(SceneVersion.scene_id.in_(ids)))
        await db.execute(delete(model).where(model.id.in_(ids)))
        await db.execute(delete(EntityProvenance).where(
            EntityProvenance.run_id == run.id, EntityProvenance.entity_type == et))
    for prefix in _REGEN_STEPS[phase]:
        await db.execute(delete(AuthoringStep).where(
            AuthoringStep.run_id == run.id,
            AuthoringStep.step_key.like(f"{prefix}%")))
    if hint and phase != "premise":
        ctx = _premise_ctx(run)
        ctx["author_hint"] = hint
        run.cursor_json = json.dumps(ctx, ensure_ascii=False)
    elif hint:
        run.prompt = f"{run.prompt}\n[Gợi ý chỉnh: {hint}]"
    run.stage_payload_json = None
    run.status = "running"
    run.last_error = None


def is_live(run_id: str) -> bool:
    t = _live.get(run_id)
    return t is not None and not t.done()
