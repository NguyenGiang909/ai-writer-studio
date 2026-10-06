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

from sqlalchemy import select, func, delete, update
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
from app.ai.compose import (
    build_story_prompt, WORLD_GEN_SYSTEM,
    WORLD_PLACES_SYSTEM, WORLD_RULES_SYSTEM, WORLD_LORE_SYSTEM,
    OUTLINE_SKELETON_SYSTEM, OUTLINE_ARC_SYSTEM,
)

PHASES = ["premise", "cast", "world", "outline", "writing"]
_PHASES_ROLLING = ["premise", "cast", "world", "build"]


def phases_for(run) -> list[str]:
    """Phase list theo flow của run. rolling: sau world là 1 phase 'build'
    chạy sóng theo hồi (dàn → viết → facts) thay vì outline→writing riêng."""
    return _PHASES_ROLLING if getattr(run, "flow", "batch") == "rolling" else PHASES


# prefix step_key thuộc từng phase — dùng check "phase này có làm việc không"
_PHASE_STEP_PREFIX = {
    "premise": "premise.",
    "cast": "cast.",
    "world": "world.",
    "outline": ("outline.", "chapter_scenes."),
    "writing": ("scene_write.", "chapter_facts."),
    "build": ("outline.", "chapter_scenes.", "scene_write.", "chapter_facts."),
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
    arcs: list = field(default_factory=list)           # ordered
    chapters_by_arc: dict = field(default_factory=dict)
    scenes_by_chapter: dict = field(default_factory=dict)
    has_premise: bool = False
    has_cast: bool = False
    world_parts: set[str] = field(default_factory=set)  # loại world entity đã có


async def load_facts(db: AsyncSession, run: AuthoringRun) -> Facts:
    """IO boundary — đọc hết facts route cần. next_step giữ thuần.

    done/project_id: step đã xong ở BẤT KỲ run nào của project → không làm lại
    (chapter_facts tránh trích trùng, scene_write/chapter_scenes tự idempotent
    qua trạng thái entity). failed/run_id: chỉ đếm lỗi của run hiện tại."""
    steps = (await db.scalars(select(AuthoringStep).where(
        AuthoringStep.project_id == run.project_id))).all()
    chapters = list((await db.scalars(select(Chapter).where(
        Chapter.project_id == run.project_id).order_by(Chapter.order_index))).all())
    arcs = list((await db.scalars(select(Arc).where(
        Arc.project_id == run.project_id).order_by(Arc.order_index))).all())
    by_arc: dict[str, list] = {}
    for ch in chapters:
        if ch.arc_id:
            by_arc.setdefault(ch.arc_id, []).append(ch)
    scenes = list((await db.scalars(select(Scene).where(
        Scene.project_id == run.project_id).order_by(Scene.order_index))).all())
    by_ch: dict[str, list] = {}
    for sc in scenes:
        by_ch.setdefault(sc.chapter_id, []).append(sc)
    proj = await db.get(Project, run.project_id)
    n_chars = await db.scalar(select(func.count(Character.id)).where(
        Character.project_id == run.project_id))
    world_parts: set[str] = set()
    for wname, m in (("location", Location), ("faction", Faction), ("item", Item),
                     ("ability", Ability), ("world_entity", WorldEntity),
                     ("style_profile", StyleProfile)):
        if await db.scalar(select(func.count(m.id)).where(
                m.project_id == run.project_id)):
            world_parts.add(wname)
    failed: dict[str, int] = {}
    for s in steps:
        if s.status == "failed" and s.run_id == run.id:
            failed[s.step_key] = failed.get(s.step_key, 0) + 1
    return Facts(done={s.step_key for s in steps if s.status == "done"},
                 run_done={s.step_key for s in steps
                           if s.status == "done" and s.run_id == run.id},
                 failed=failed, chapters=chapters, arcs=arcs,
                 chapters_by_arc=by_arc, scenes_by_chapter=by_ch,
                 has_premise=bool((proj.description or "").strip()) if proj else False,
                 has_cast=bool(n_chars), world_parts=world_parts)


# world tách 3 sub-step tuần tự — call sau nhìn kết quả call trước (liền mạch)
# (step_key, loại entity step phủ, mô tả)
_WORLD_PLAN = (
    ("world.places", {"location", "faction"}, "Sinh địa danh + thế lực"),
    ("world.rules", {"item", "ability"}, "Sinh vật phẩm + luật sức mạnh"),
    ("world.lore", {"world_entity", "style_profile"}, "Sinh lore + phong cách truyện"),
)


def _ch_step(f: Facts, ch) -> Step | None:
    """Đơn vị thiếu đầu tiên TRONG một chương: dàn cảnh → viết từng cảnh → facts."""
    scenes = f.scenes_by_chapter.get(ch.id, [])
    if not scenes and f"chapter_scenes.{ch.id}" not in f.done:
        return Step(f"chapter_scenes.{ch.id}", "chapter_outline",
                    f"Dàn cảnh cho chương {ch.order_index}: {ch.title}", ch.id)
    for sc in scenes:
        if not (sc.prose or "").strip() and f"scene_write.{sc.id}" not in f.done:
            return Step(f"scene_write.{sc.id}", "scene_expand",
                        f"Viết cảnh “{sc.title or '?'}” (chương {ch.order_index})", sc.id)
    if scenes and f"chapter_facts.{ch.id}" not in f.done:
        return Step(f"chapter_facts.{ch.id}", "chapter_facts",
                    f"Trích facts chương {ch.order_index}", ch.id)
    return None


def _arc_step(run: AuthoringRun, f: Facts, arc) -> Step | None:
    """Đơn vị thiếu đầu tiên TRONG một hồi — đúng thứ tự người viết:
    dàn chương → per chương [dàn cảnh → viết từng cảnh → trích facts]."""
    chs = f.chapters_by_arc.get(arc.id, [])
    if not chs and f"outline.chapters.{arc.id}" not in f.done:
        return Step(f"outline.chapters.{arc.id}", "arc_chapters",
                    f"Dàn chương hồi “{arc.title}”", arc.id)
    for ch in chs:
        s = _ch_step(f, ch)
        if s:
            return s
    return None


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
        # fast (API mạnh): 1 call gộp — chỉ khi world còn trống; thiếu lẻ vẫn granular
        if run.call_mode == "fast" and not f.world_parts \
                and "world.generate" not in f.done:
            return Step("world.generate", "world_gen",
                        "Sinh toàn bộ thế giới (1 call)")
        # tách 3 call nhỏ, mỗi call chỉ sinh mảng còn thiếu (covers - world_parts)
        # → chống gateway timeout + continue-mode bù đúng loại thiếu, không gọi lại
        for key, covers, detail in _WORLD_PLAN:
            if key not in f.done and covers - f.world_parts:
                return Step(key, "world_gen", detail)
        return None
    if ph == "outline":
        # fast: 1 call toàn bộ khung — chỉ khi chưa có gì; còn lại vẫn granular
        if run.call_mode == "fast" and not f.chapters and not f.arcs \
                and "outline.generate" not in f.done:
            return Step("outline.generate", "book_outline",
                        "Sinh toàn bộ khung truyện (1 call)")
        # tách 2 tầng chống timeout: skeleton quyển/hồi → dàn chương từng hồi
        if not f.chapters and not f.arcs and "outline.skeleton" not in f.done:
            return Step("outline.skeleton", "book_outline", "Sinh khung Quyển/Hồi")
        for arc in f.arcs:
            if not f.chapters_by_arc.get(arc.id) \
                    and f"outline.chapters.{arc.id}" not in f.done:
                return Step(f"outline.chapters.{arc.id}", "arc_chapters",
                            f"Dàn chương hồi “{arc.title}”", arc.id)
        for ch in f.chapters:
            if not f.scenes_by_chapter.get(ch.id) and f"chapter_scenes.{ch.id}" not in f.done:
                return Step(f"chapter_scenes.{ch.id}", "chapter_outline",
                            f"Dàn cảnh cho chương {ch.order_index}: {ch.title}", ch.id)
        return None
    if ph == "build":
        # rolling: skeleton 1 lần làm bản đồ đường, rồi sóng theo hồi —
        # hồi sau được dàn SAU KHI hồi trước viết xong → prompt thấy facts thật
        if not f.chapters and not f.arcs and "outline.skeleton" not in f.done:
            return Step("outline.skeleton", "book_outline", "Sinh khung Quyển/Hồi")
        ctx = _premise_ctx(run)
        cur = ctx.get("wave_arc")
        target = next((a for a in f.arcs if _arc_step(run, f, a) is not None), None)
        if target is None:
            # hết hồi → chương mồ côi (tác giả tự thêm ngoài hồi) vẫn được build
            och = next((c for c in f.chapters
                        if not c.arc_id and _ch_step(f, c) is not None), None)
            return _ch_step(f, och) if och else None
        if cur != target.id:
            if run.pause_after_wave and cur:
                # sentinel — tick đổi thành checkpoint + cờ 1 lần xoá tại đó
                # (build là phase cuối nên return None = complete, không phải pause)
                return Step("__wave_pause__", "noop",
                            "Dừng ở ranh giới sóng theo yêu cầu")
            ctx["wave_arc"] = target.id
            run.cursor_json = json.dumps(ctx, ensure_ascii=False)
        return _arc_step(run, f, target)
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


async def _cast_names(db, run) -> list[str]:
    return [c.name for c in (await db.scalars(select(Character).where(
        Character.project_id == run.project_id))).all()]


async def _existing_names(db, model, run) -> set[str]:
    return set((await db.scalars(select(model.name).where(
        model.project_id == run.project_id))).all())


async def _world_ctx(db, run) -> str:
    """Thế giới tích lũy (có sẵn + vừa sinh) — context liền mạch cho call sau:
    call sau tham chiếu đúng tên, không trùng/mâu thuẫn thực thể đã có."""
    lines = []
    for label, model, render in (
        ("Địa danh", Location, lambda r: _clip(r.description, 100)),
        ("Thế lực", Faction, lambda r: _clip(r.description, 100)),
        ("Vật phẩm", Item, lambda r: _clip(r.description, 100)),
        ("Sức mạnh", Ability, lambda r: f"{r.ability_type or '?'}: {_clip(r.can_do, 80)}"),
        ("Lore", WorldEntity, lambda r: f"{r.entity_type or 'lore'}: {_clip(r.description, 80)}"),
    ):
        rows = (await db.scalars(select(model).where(
            model.project_id == run.project_id))).all()
        if rows:
            lines.append(f"[{label}] " + "; ".join(
                f"{r.name} ({render(r)})" if render(r) else r.name for r in rows[:15]))
    return "\n".join(lines) or "(chưa có)"


def _world_prompt(run, premise, world_ctx: str, chars: list[str], want: str) -> str:
    return (f"=== PREMISE ===\n{json.dumps(premise, ensure_ascii=False)}\n\n"
            f"=== NHÂN VẬT ===\n" + ", ".join(chars[:20]) + "\n\n"
            f"=== THẾ GIỚI ĐÃ CÓ (phải khớp, tham chiếu đúng tên, không tạo trùng) ===\n"
            f"{world_ctx}\n\n"
            f"NHIỆM VỤ: chỉ trả các mảng {want}.")


async def _write_world_rows(db, run, model, etype, rows, build, cap):
    existing = await _existing_names(db, model, run)
    n = 0
    for r in (rows or [])[:cap]:
        name = (r.get("name") or "").strip()
        if not name or name in existing:
            continue
        obj = build(r, name)
        db.add(obj); await db.flush(); provenance(db, run, etype, obj.id)
        existing.add(name); n += 1
    return n


async def h_world_places(db, run, step):
    parts = await _facts_parts(db, run)
    need_loc = "location" not in parts
    need_fct = "faction" not in parts
    if not (need_loc or need_fct):
        return {"skipped": "địa danh/thế lực đã có"}
    want = ", ".join(k for k, n in
                     (("locations", need_loc), ("factions", need_fct)) if n)
    prompt = _world_prompt(run, _premise_ctx(run), await _world_ctx(db, run),
                           await _cast_names(db, run), want)
    text, _ = await ai_call(db, run, "world_gen", prompt,
                            system=WORLD_PLACES_SYSTEM)
    data = parse_json(text)
    n = 0
    if need_loc:
        n += await _write_world_rows(db, run, Location, "location",
            data.get("locations"),
            lambda r, name: Location(project_id=run.project_id, name=name,
                                     description=r.get("description")), 20)
    if need_fct:
        n += await _write_world_rows(db, run, Faction, "faction",
            data.get("factions"),
            lambda r, name: Faction(project_id=run.project_id, name=name,
                                    description=r.get("description")), 15)
    run.stage_payload_json = json.dumps({"created": n}, ensure_ascii=False)
    return {"created": n}


async def h_world_rules(db, run, step):
    parts = await _facts_parts(db, run)
    need_it = "item" not in parts
    need_ab = "ability" not in parts
    if not (need_it or need_ab):
        return {"skipped": "vật phẩm/sức mạnh đã có"}
    want = ", ".join(k for k, n in
                     (("items", need_it), ("abilities", need_ab)) if n)
    prompt = _world_prompt(run, _premise_ctx(run), await _world_ctx(db, run),
                           await _cast_names(db, run), want)
    text, _ = await ai_call(db, run, "world_gen", prompt,
                            system=WORLD_RULES_SYSTEM)
    data = parse_json(text)
    n = 0
    if need_it:
        n += await _write_world_rows(db, run, Item, "item",
            data.get("items"),
            lambda r, name: Item(project_id=run.project_id, name=name,
                                 description=r.get("description")), 15)
    if need_ab:
        n += await _write_world_rows(db, run, Ability, "ability",
            data.get("abilities"),
            lambda r, name: Ability(project_id=run.project_id, name=name,
                                    ability_type=_clip(r.get("type"), 64),
                                    can_do=r.get("can_do"), cannot_do=r.get("cannot_do"),
                                    limits=r.get("limits"), cost=r.get("cost"),
                                    conditions=r.get("conditions")), 15)
    run.stage_payload_json = json.dumps({"created": n}, ensure_ascii=False)
    return {"created": n}


async def h_world_lore(db, run, step):
    parts = await _facts_parts(db, run)
    need_we = "world_entity" not in parts
    need_sp = "style_profile" not in parts
    if not (need_we or need_sp):
        return {"skipped": "lore/style đã có"}
    want = ", ".join(k for k, n in
                     (("lore", need_we), ("style", need_sp)) if n)
    prompt = _world_prompt(run, _premise_ctx(run), await _world_ctx(db, run),
                           await _cast_names(db, run), want)
    text, _ = await ai_call(db, run, "world_gen", prompt,
                            system=WORLD_LORE_SYSTEM)
    data = parse_json(text)
    n = 0
    if need_we:
        n += await _write_world_rows(db, run, WorldEntity, "world_entity",
            data.get("lore"),
            lambda r, name: WorldEntity(project_id=run.project_id, name=name,
                                        entity_type=_clip(r.get("type"), 64) or "lore",
                                        description=r.get("description")), 15)
    if need_sp and data.get("style"):
        sp = StyleProfile(project_id=run.project_id, name="AI default",
                          scope_type="global", instructions=_clip(json.dumps(
                              data["style"], ensure_ascii=False), 2000))
        db.add(sp); await db.flush(); provenance(db, run, "style_profile", sp.id)
        n += 1
    run.stage_payload_json = json.dumps({"created": n}, ensure_ascii=False)
    return {"created": n}


async def _facts_parts(db, run) -> set[str]:
    """Loại world entity đã có — check lại ở handler (facts load đã cũ khi
    step trước trong cùng phase vừa ghi entity mới)."""
    parts = set()
    for wname, m in (("location", Location), ("faction", Faction), ("item", Item),
                     ("ability", Ability), ("world_entity", WorldEntity),
                     ("style_profile", StyleProfile)):
        if await db.scalar(select(func.count(m.id)).where(
                m.project_id == run.project_id)):
            parts.add(wname)
    return parts


async def h_world_all(db, run, step):
    """Fast mode: 1 call toàn bộ world — chỉ route tới khi world còn trống."""
    prompt = _world_prompt(run, _premise_ctx(run), await _world_ctx(db, run),
                           await _cast_names(db, run),
                           "locations, factions, items, abilities, lore, style")
    text, _ = await ai_call(db, run, "world_gen", prompt, system=WORLD_GEN_SYSTEM)
    data = parse_json(text)
    n = 0
    n += await _write_world_rows(db, run, Location, "location",
        data.get("locations"),
        lambda r, name: Location(project_id=run.project_id, name=name,
                                 description=r.get("description")), 20)
    n += await _write_world_rows(db, run, Faction, "faction",
        data.get("factions"),
        lambda r, name: Faction(project_id=run.project_id, name=name,
                                description=r.get("description")), 15)
    n += await _write_world_rows(db, run, Item, "item",
        data.get("items"),
        lambda r, name: Item(project_id=run.project_id, name=name,
                             description=r.get("description")), 15)
    n += await _write_world_rows(db, run, Ability, "ability",
        data.get("abilities"),
        lambda r, name: Ability(project_id=run.project_id, name=name,
                                ability_type=_clip(r.get("type"), 64),
                                can_do=r.get("can_do"), cannot_do=r.get("cannot_do"),
                                limits=r.get("limits"), cost=r.get("cost"),
                                conditions=r.get("conditions")), 15)
    n += await _write_world_rows(db, run, WorldEntity, "world_entity",
        data.get("lore"),
        lambda r, name: WorldEntity(project_id=run.project_id, name=name,
                                    entity_type=_clip(r.get("type"), 64) or "lore",
                                    description=r.get("description")), 15)
    if data.get("style"):
        sp = StyleProfile(project_id=run.project_id, name="AI default",
                          scope_type="global", instructions=_clip(json.dumps(
                              data["style"], ensure_ascii=False), 2000))
        db.add(sp); await db.flush(); provenance(db, run, "style_profile", sp.id)
        n += 1
    run.stage_payload_json = json.dumps({"created": n}, ensure_ascii=False)
    return {"created": n}


async def h_outline_all(db, run, step):
    """Fast mode: 1 call toàn bộ khung quyển/hồi/chương — chỉ khi chưa có gì."""
    premise = _premise_ctx(run)
    chars = await _cast_names(db, run)
    goal = (f"\n\n=== MỤC TIÊU ===\nTổng số chương mong muốn: ~{run.target_chapters}. "
            f"Dàn quyển/hồi/chương sát mục tiêu này (được lệch nếu cốt truyện cần)."
            if run.target_chapters else "")
    prompt = (f"=== PREMISE ===\n{json.dumps(premise, ensure_ascii=False)}\n\n"
              f"=== NHÂN VẬT ===\n" + ", ".join(chars[:20])
              + goal + "\n\nSinh khung truyện đầy đủ theo schema.")
    text, _ = await ai_call(db, run, "book_outline", prompt)
    data = parse_json(text)
    vols = data.get("volumes") or []
    if not vols:
        raise ValueError("model không trả outline hợp lệ")
    vol_order = max((v.order_index for v in (await db.scalars(select(Volume).where(
        Volume.project_id == run.project_id))).all()), default=0)
    arc_order = max((a.order_index for a in (await db.scalars(select(Arc).where(
        Arc.project_id == run.project_id))).all()), default=0)
    ch_order = max((c.order_index for c in (await db.scalars(select(Chapter).where(
        Chapter.project_id == run.project_id))).all()), default=0)
    ctx = _premise_ctx(run)
    beats = ctx.get("beats") or {}
    n_ch = 0
    for vi, v in enumerate(vols[:10], start=1):
        vol = Volume(project_id=run.project_id, title=_clip(v.get("title"), 240) or f"Quyển {vi}",
                     order_index=vol_order + vi)
        db.add(vol); await db.flush(); provenance(db, run, "volume", vol.id)
        for a in (v.get("arcs") or [])[:10]:
            arc_order += 1
            arc = Arc(project_id=run.project_id, volume_id=vol.id,
                      title=_clip(a.get("title"), 240) or f"Hồi {arc_order}",
                      order_index=arc_order)
            db.add(arc); await db.flush(); provenance(db, run, "arc", arc.id)
            for c in (a.get("chapters") or [])[:40]:
                ch_order += 1
                ch = Chapter(project_id=run.project_id, volume_id=vol.id, arc_id=arc.id,
                             title=_clip(c.get("title"), 240) or f"Chương {ch_order}",
                             order_index=ch_order, status="draft")
                db.add(ch); await db.flush(); provenance(db, run, "chapter", ch.id)
                if c.get("beat"):
                    beats[ch.id] = c["beat"]
                n_ch += 1
    ctx["beats"] = beats
    run.cursor_json = json.dumps(ctx, ensure_ascii=False)
    run.stage_payload_json = json.dumps(
        {"volumes": len(vols), "chapters": n_ch}, ensure_ascii=False)
    return {"volumes": len(vols), "chapters": n_ch}


async def h_outline_skeleton(db, run, step):
    premise = _premise_ctx(run)
    chars = await _cast_names(db, run)
    goal = (f"\n\n=== MỤC TIÊU ===\nTổng số chương mong muốn: ~{run.target_chapters}. "
            f"Dàn quyển/hồi sát mục tiêu này (được lệch nếu cốt truyện cần)."
            if run.target_chapters else "")
    prompt = (f"=== PREMISE ===\n{json.dumps(premise, ensure_ascii=False)}\n\n"
              f"=== NHÂN VẬT ===\n" + ", ".join(chars[:20])
              + goal + "\n\nSinh khung Quyển/Hồi theo schema (chưa dàn chương).")
    text, _ = await ai_call(db, run, "book_outline", prompt,
                            system=OUTLINE_SKELETON_SYSTEM)
    data = parse_json(text)
    vols = data.get("volumes") or []
    if not vols:
        raise ValueError("model không trả khung quyển/hồi hợp lệ")
    # order_index unique (project_id, order_index) toàn cục — đếm tiếp từ max
    # hiện có, KHÔNG reset theo quyển (resume/tiếp nối cũng đúng)
    vol_order = max((v.order_index for v in (await db.scalars(select(Volume).where(
        Volume.project_id == run.project_id))).all()), default=0)
    arc_order = max((a.order_index for a in (await db.scalars(select(Arc).where(
        Arc.project_id == run.project_id))).all()), default=0)
    n_arcs = 0
    for vi, v in enumerate(vols[:10], start=1):
        vol = Volume(project_id=run.project_id, title=_clip(v.get("title"), 240) or f"Quyển {vi}",
                     order_index=vol_order + vi)
        db.add(vol); await db.flush(); provenance(db, run, "volume", vol.id)
        for a in (v.get("arcs") or [])[:10]:
            arc_order += 1
            arc = Arc(project_id=run.project_id, volume_id=vol.id,
                      title=_clip(a.get("title"), 240) or f"Hồi {arc_order}",
                      order_index=arc_order)
            db.add(arc); await db.flush(); provenance(db, run, "arc", arc.id)
            a["_arc_id"] = arc.id  # map goal/count về arc id cho call dàn chương
            n_arcs += 1
    # skeleton bền trong cursor_json — call dàn chương đọc goal từng hồi
    ctx = _premise_ctx(run)
    ctx["skeleton"] = data
    run.cursor_json = json.dumps(ctx, ensure_ascii=False)
    run.stage_payload_json = json.dumps(
        {"volumes": len(vols), "arcs": n_arcs}, ensure_ascii=False)
    return {"volumes": len(vols), "arcs": n_arcs}


async def _written_ctx(db, run) -> str:
    """Diễn biến truyện ĐÃ VIẾT — events/states/threads mới nhất.

    Sống nhờ rolling: hồi sau được dàn khi hồi trước đã có prose + facts,
    nên prompt thấy truyện thật (ai chết, tuyến nào vừa khép/mở) thay vì
    chỉ thấy title chương — khung khỏi lệch thực tế."""
    evs = list((await db.scalars(select(StoryEvent).where(
        StoryEvent.project_id == run.project_id).order_by(
        StoryEvent.narrative_order.desc(), StoryEvent.id.desc()))).all()[:15])
    if not evs:
        return ""
    lines = ["SỰ KIỆN GẦN NHẤT (đã viết):"]
    for e in reversed(evs):
        lines.append(f"- {e.summary}")
    sts = list((await db.scalars(select(StoryState).where(
        StoryState.project_id == run.project_id).order_by(
        StoryState.narrative_order.desc(), StoryState.id.desc()))).all()[:12])
    if sts:
        lines.append("TRẠNG THÁI MỚI NHẤT:")
        for s in reversed(sts):
            lines.append(f"- {s.entity_type} {s.key}: {s.value_text}")
    ths = list((await db.scalars(select(Thread).where(
        Thread.project_id == run.project_id, Thread.status == "OPEN"))).all()[:12])
    if ths:
        lines.append("THREAD ĐANG MỞ: " + ", ".join(t.title for t in ths))
    return "\n".join(lines)[:2400]


async def h_arc_chapters(db, run, step):
    arc = await db.get(Arc, step.ref_id)
    if not arc:
        raise ValueError("arc không tồn tại")
    ctx = _premise_ctx(run)
    skeleton = ctx.get("skeleton") or {}
    arc_meta = next((a for v in (skeleton.get("volumes") or [])
                     for a in (v.get("arcs") or []) if a.get("_arc_id") == arc.id), {})
    chars = await _cast_names(db, run)
    existing = [c.title for c in (await db.scalars(select(Chapter).where(
        Chapter.project_id == run.project_id).order_by(Chapter.order_index))).all()]
    want = arc_meta.get("chapter_count")
    # truyện dài: chỉ cần ~30 chương gần nhất để nối mạch — tránh prompt phình
    recent = existing[-30:]
    written = await _written_ctx(db, run)
    prompt = (f"=== PREMISE ===\n{json.dumps({k: v for k, v in ctx.items() if k != 'skeleton'}, ensure_ascii=False)}\n\n"
              f"=== KHUNG TRUYỆN ===\n{json.dumps(skeleton, ensure_ascii=False)[:3000]}\n\n"
              f"=== NHÂN VẬT ===\n" + ", ".join(chars[:20]) + "\n\n"
              f"=== DANH SÁCH CHƯƠNG ĐÃ DÀN (gần nhất) ===\n"
              + ("\n".join(recent) or "(chưa có)")
              + (f"\n\n=== DIỄN BIẾN ĐÃ VIẾT ===\n{written}" if written else "")
              + f"\n\n=== HỒI CẦN DÀN ===\n{arc.title}"
              + (f" — goal: {arc_meta.get('goal')}" if arc_meta.get("goal") else "")
              + (f" — ~{want} chương" if want else "")
              + "\n\nDàn chương cho hồi này theo schema.")
    text, _ = await ai_call(db, run, "arc_chapters", prompt,
                            system=OUTLINE_ARC_SYSTEM)
    data = parse_json(text)
    chs = data.get("chapters") or []
    if not chs:
        raise ValueError("model không trả chương hợp lệ")
    order = max((c.order_index for c in (await db.scalars(select(Chapter).where(
        Chapter.project_id == run.project_id))).all()), default=0)
    beats = ctx.get("beats") or {}
    n = 0
    for c in chs[:40]:
        order += 1
        ch = Chapter(project_id=run.project_id, volume_id=arc.volume_id, arc_id=arc.id,
                     title=_clip(c.get("title"), 240) or f"Chương {order}",
                     order_index=order, status="draft")
        db.add(ch); await db.flush(); provenance(db, run, "chapter", ch.id)
        if c.get("beat"):
            beats[ch.id] = c["beat"]  # giữ beat — dàn cảnh dùng lại
        n += 1
    ctx["beats"] = beats
    run.cursor_json = json.dumps(ctx, ensure_ascii=False)
    run.stage_payload_json = json.dumps({"arc": arc.title, "chapters": n}, ensure_ascii=False)
    return {"chapters": n}


async def h_chapter_scenes(db, run, step):
    ch = await db.get(Chapter, step.ref_id)
    if not ch:
        raise ValueError("chapter không tồn tại")
    beat = (_premise_ctx(run).get("beats") or {}).get(ch.id)
    text, _ = await ai_call(db, run, "chapter_outline",
                          f"Beat chương: {beat}" if beat else "", chapter_id=ch.id)
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
    "premise": h_premise, "cast_gen": h_cast,
    "world.places": h_world_places, "world.rules": h_world_rules,
    "world.lore": h_world_lore, "world.generate": h_world_all,
    "outline.skeleton": h_outline_skeleton, "outline.generate": h_outline_all,
    "arc_chapters": h_arc_chapters,
    "chapter_outline": h_chapter_scenes,
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
        # step "running" sót lại từ process chết trước = gián đoạn → "interrupted"
        # (không tính failed → retry sạch, không nuốt quota 2-lần-fail)
        await db.execute(
            update(AuthoringStep).where(
                AuthoringStep.run_id == run_id,
                AuthoringStep.status == "running")
            .values(status="interrupted", error="process restart/crash",
                    finished_at=datetime.utcnow()))
        facts = await load_facts(db, run)
        step = next_step(run, facts)
        if step is not None and step.key == "__wave_pause__":
            # cờ 1-lần pause_after_wave vừa bắn — checkpoint để tác giả chen vào
            run.pause_after_wave = False
            run.status = "awaiting_review"
            await db.commit()
            return "checkpoint"
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
            phs = phases_for(run)
            idx = phs.index(run.phase)
            if idx >= len(phs) - 1:
                run.status = "complete"
            elif not produced:
                run.phase = phs[idx + 1]
            else:
                run.status = "awaiting_review"
            await db.commit()
            if run.status == "running":
                return "step"  # loop tiếp trong phase mới
            return "complete" if run.status == "complete" else "checkpoint"
        # step-row "running" COMMIT RIÊNG (txn ngắn) — không giữ write lock
        # trong suốt model call ~1 phút, writer khác (tác giả sửa tay) vẫn vào được
        srow = AuthoringStep(run_id=run.id, project_id=run.project_id,
                             step_key=step.key, status="running")
        db.add(srow)
        await db.commit()
        sid = srow.id
        try:
            out = await (HANDLERS.get(step.key) or HANDLERS[step.task])(db, run, step)
            srow = await db.get(AuthoringStep, sid)
            srow.status = "done"
            srow.finished_at = datetime.utcnow()
            srow.output_json = json.dumps(out, ensure_ascii=False) if out else None
            run = await db.get(AuthoringRun, run_id)
            run.last_error = None
        except Exception as e:  # noqa: BLE001 — step fail không giết run
            await db.rollback()  # step atomic — entity ghi dở không được lọt vào DB
            run = await db.get(AuthoringRun, run_id)  # rollback expire object → re-fetch
            if run is None:
                return "stopped"
            srow = await db.get(AuthoringStep, sid)
            if srow:
                srow.status = "failed"
                srow.error = str(e)[:2000]
                srow.finished_at = datetime.utcnow()
            else:  # edge: row mất → ghi failed mới như cũ
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
    "world": ["world."],
    "outline": ["outline.", "chapter_scenes."],
}
_ENTITY_MODEL = {
    "character": Character, "alias": Alias, "relationship": Relationship,
    "location": Location, "faction": Faction, "item": Item,
    "ability": Ability, "world_entity": WorldEntity, "style_profile": StyleProfile,
    "scene": Scene, "chapter": Chapter, "arc": Arc, "volume": Volume,
}


async def _regen_wave(db, run, hint):
    """Tạo lại HỒI ĐANG SÓNG (build checkpoint) — xoá chapters/scenes/facts
    AI tạo trong hồi đó, reset wave cursor về hồi này, chạy lại.
    Không đụng hồi trước — facts đã viết là ground truth."""
    ctx = _premise_ctx(run)
    arc_id = ctx.get("wave_arc")
    if not arc_id:
        raise ValueError("không xác định được hồi đang sóng để tạo lại")
    arc = await db.get(Arc, arc_id)
    if not arc:
        raise ValueError("hồi đang sóng không còn tồn tại")
    # chỉ entity do RUN này tạo — chương/cảnh tác giả tự thêm không bị xoá
    async def prov_ids(et):
        return set((await db.scalars(select(EntityProvenance.entity_id).where(
            EntityProvenance.run_id == run.id,
            EntityProvenance.entity_type == et))).all())
    ch_prov = await prov_ids("chapter")
    chs = [c for c in (await db.scalars(select(Chapter).where(
        Chapter.arc_id == arc_id))).all() if c.id in ch_prov]
    ch_ids = [c.id for c in chs]
    ch_orders = [c.order_index for c in chs]
    sc_prov = await prov_ids("scene")
    sc_ids = [s for s in (await db.scalars(select(Scene.id).where(
        Scene.chapter_id.in_(ch_ids)))).all() if s in sc_prov] if ch_ids else []
    if sc_ids:
        from app.models.manuscript import SceneVersion
        await db.execute(delete(SceneVersion).where(SceneVersion.scene_id.in_(sc_ids)))
        # facts gắn scene của hồi này — event/beat/canon theo scene_id,
        # state theo narrative_order của chương (StoryState không có scene_id)
        await db.execute(delete(StoryEvent).where(StoryEvent.scene_id.in_(sc_ids)))
        await db.execute(delete(ThreadBeat).where(ThreadBeat.scene_id.in_(sc_ids)))
        await db.execute(delete(CanonFact).where(CanonFact.source_scene_id.in_(sc_ids)))
        await db.execute(delete(Scene).where(Scene.id.in_(sc_ids)))
    if ch_orders:
        await db.execute(delete(StoryState).where(
            StoryState.project_id == run.project_id,
            StoryState.narrative_order.in_(ch_orders)))
    if ch_ids:
        await db.execute(delete(Chapter).where(Chapter.id.in_(ch_ids)))
    for et, ids in (("scene", sc_ids), ("chapter", ch_ids)):
        if ids:
            await db.execute(delete(EntityProvenance).where(
                EntityProvenance.run_id == run.id,
                EntityProvenance.entity_id.in_(ids)))
    # facts' provenance rows — entity_id là id row fact (đã xoá); dọn mồ côi
    for et in ("story_event", "story_state", "thread_beat", "canon_fact"):
        model = {"story_event": StoryEvent, "story_state": StoryState,
                 "thread_beat": ThreadBeat, "canon_fact": CanonFact}[et]
        orphans = (await db.scalars(select(EntityProvenance.entity_id).where(
            EntityProvenance.run_id == run.id,
            EntityProvenance.entity_type == et))).all()
        gone = [i for i in orphans if not await db.get(model, i)]
        if gone:
            await db.execute(delete(EntityProvenance).where(
                EntityProvenance.entity_id.in_(gone)))
    keys = [f"outline.chapters.{arc_id}"]
    keys += [f"chapter_scenes.{c}" for c in ch_ids]
    keys += [f"chapter_facts.{c}" for c in ch_ids]
    keys += [f"scene_write.{s}" for s in sc_ids]
    if keys:
        await db.execute(delete(AuthoringStep).where(
            AuthoringStep.run_id == run.id, AuthoringStep.step_key.in_(keys)))
    ctx["wave_arc"] = arc_id
    if hint:
        ctx["author_hint"] = hint
    run.cursor_json = json.dumps(ctx, ensure_ascii=False)


async def regenerate(db: AsyncSession, run: AuthoringRun, hint: str | None = None):
    """Tạo lại stage hiện tại khi đang checkpoint — xoá entity AI của stage,
    xoá step đã xong, đưa hint vào premise context, rồi chạy lại."""
    phase = run.phase
    if phase == "build":
        await _regen_wave(db, run, hint)
    elif phase not in _REGEN_TYPES:
        raise ValueError("không thể tạo lại stage writing — prose/facts đã ghi")
    else:
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
    if hint and phase not in {"premise", "build"}:
        ctx = _premise_ctx(run)
        ctx["author_hint"] = hint
        run.cursor_json = json.dumps(ctx, ensure_ascii=False)
    elif hint and phase == "premise":
        run.prompt = f"{run.prompt}\n[Gợi ý chỉnh: {hint}]"
    run.stage_payload_json = None
    run.status = "running"
    run.last_error = None


def is_live(run_id: str) -> bool:
    t = _live.get(run_id)
    return t is not None and not t.done()
