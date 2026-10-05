"""Compose task prompts with story context from the DB.

build_story_prompt(db, pid, task, user_prompt, scene_id) -> (system, prompt)
Keeps output bounded (~token estimate via len//4) and never mutates anything.
"""

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Project, Chapter, Scene, Volume, Arc
from app.models.story import Character, Alias
from app.models.truth import CanonFact
from app.models.narrative import Thread
from app.models.memory import StorySummary, AiTurn
from app.services.constraints import build_constraints, render_constraints
from app.services.memory import ancestor_chain

MEMORY_TASKS = {"writing", "expand", "scene_expand", "revision", "skeleton"}

WRITING_SYSTEM = (
    "Bạn là trợ lý viết truyện. Nhiệm vụ duy nhất: viết/mở rộng VĂN XUÔI tiểu thuyết "
    "tiếng Việt theo đúng brief của tác giả. Không giải thích, không hỏi lại, không "
    "liệt kê gợi ý — chỉ xuất ra phần văn. Giữ đúng POV và tone của truyện; tôn trọng "
    "tuyệt đối Canon Facts; không tiết lộ điều brief cấm; không tự thêm tên/sự kiện "
    "mâu thuẫn dữ kiện đã cho. Nếu brief thiếu chi tiết, suy ra hợp lý từ ngữ cảnh "
    "thay vì hỏi."
)

REVISION_SYSTEM = (
    "Bạn là trợ lý biên tập văn xuôi tiểu thuyết. Tác giả gửi một đoạn văn đã viết kèm "
    "ghi chú cần sửa. Nhiệm vụ duy nhất: trả về TOÀN BỘ đoạn văn ĐÃ SỬA, giữ nguyên "
    "phần không được yêu cầu đổi, tôn trọng Canon Facts và POV. Không giải thích, không "
    "liệt kê thay đổi, không hỏi lại — chỉ xuất văn đã sửa."
)

DISCUSSION_SYSTEM = (
    "Bạn là cộng sự thảo luận cốt truyện của tác giả (plot doctor). Trả lời ngắn gọn, "
    "thực tế, bám sát dữ kiện truyện được cung cấp. Đề xuất rõ ràng khi cần, chỉ ra rủi "
    "ro mâu thuẫn Canon hoặc lộ knowledge nếu có. Không viết văn xuôi trừ khi được yêu cầu. "
    "Nếu yêu cầu của tác giả mơ hồ hoặc thiếu thông tin cần thiết, HỎI LẠI tác giả 1–2 câu "
    "ngắn gọn để làm rõ thay vì đoán bừa."
)

EXTRACTION_SYSTEM = (
    "Bạn là bộ trích xuất dữ kiện từ văn xuôi tiểu thuyết. Đọc đoạn văn và trả về "
    "DUY NHẤT một JSON object hợp lệ (không markdown, không giải thích) với schema:\n"
    '{"events":[{"summary":str,"event_type":str,"story_time":int|null}],'
    '"canon_facts":[{"predicate":str,"value_text":str,"subject_type":str}],'
    '"entities":[{"kind":"character"|"location"|"object"|"ability"|"item","name":str,"summary":str}],'
    '"story_states":[{"entity_name":str,"entity_kind":"character"|"location"|"item"|"ability"|"relationship",'
    '"key":"lifecycle"|"location"|"ownership"|"status","value":str,"story_time":int|null}],'
    '"knowledge":[{"knower_name":str,"predicate":str,"value_text":str,'
    '"state":"KNOWS"|"SUSPECTS"|"FALSE_BELIEF"|"DOES_NOT_KNOW","story_time":int|null}],'
    '"thread_touches":[{"thread_title":str,"beat_type":"setup"|"reinforcement"|"escalation"|'
    '"misdirection"|"payoff"|"considered","note":str}],'
    '"notes":str}\n'
    "story_states = thay đổi trạng thái thế giới trong cảnh (ai chết, ai đi đâu, vật đổi chủ, "
    "quan hệ đổi trạng thái, năng lực được mở khoá). "
    "knowledge = nhân vật/độc giả HỌC ĐƯỢC sự thật nào trong cảnh (knower_name='reader' cho độc giả). "
    "thread_touches = hố/tuyến đang mở nào được đụng tới trong cảnh này. "
    "Chỉ trích dữ kiện MỚI xuất hiện trong đoạn văn, chưa có trong Canon Facts đã cho. "
    "Không suy diễn ngoài văn. Không chắc thì bỏ qua."
)

SKELETON_SYSTEM = (
    "Bạn là trợ lý dàn ý cảnh cho tác giả viết tiểu thuyết. Nhiệm vụ duy nhất: trả về "
    "danh sách 5-9 beat cho cảnh, MỖI DÒNG một beat bắt đầu bằng '• ', tiếng Việt, "
    "ngắn gọn (mỗi beat ≤20 từ). Beats phải có nhịp: mở cảnh → xây dựng → cao trào/"
    "chuyển → kết/móc nối. Bám sát Canon Facts, tôn trọng các hố/tuyến đang mở được "
    "cung cấp (có thể gài hoặc trả một phần nếu hợp nhịp), đúng POV và địa điểm cảnh. "
    "KHÔNG viết văn xuôi, không tiêu đề, không giải thích — chỉ các dòng '• '."
)

CHAPTER_OUTLINE_SYSTEM = (
    "Bạn là trợ lý dàn ý chương cho tác giả viết tiểu thuyết. Nhiệm vụ duy nhất: đề xuất "
    "3-7 cảnh cho chương được giao. MỖI DÒNG một cảnh, đúng format: "
    "'Tên cảnh — beat ngắn' (tối đa 25 từ sau gạch). Tiếng Việt. Các cảnh phải tạo "
    "thành cung truyện của chương: mở → xây → xoay/kết có móc. Bám sát Canon Facts, "
    "premise, các hố/tuyến đang mở được cung cấp. Không viết văn xuôi, không lời dẫn, "
    "không giải thích — chỉ các dòng cảnh."
)

SUMMARIZE_SYSTEM = (
    "Bạn là trợ lý tóm tắt cho tác giả tiểu thuyết. Tóm tắt đoạn văn được gửi thành "
    "3-5 câu tiếng Việt: diễn biến chính, quyết định/lộ diện quan trọng, trạng thái "
    "thay đổi (nếu có). Chỉ dùng dữ kiện trong văn — không suy diễn, không bình luận."
)


def _est(text: str) -> int:
    return max(1, len(text) // 4)


def _clip(text: str | None, chars: int) -> str:
    t = (text or "").strip()
    return t if len(t) <= chars else t[:chars] + "…"


async def _story_context(db: AsyncSession, pid: str, scene_id: str | None,
                         user_prompt: str = "", task: str = "",
                         budget: int = 6000) -> tuple[str, list[str]]:
    """Return (context_text, manifest_lines). Sections ordered by priority."""
    sections: list[tuple[str, int, str]] = []  # (text, priority, label)
    proj = await db.get(Project, pid)
    sc = None
    pool_parts = [user_prompt or ""]

    # --- current scene first (most important)
    if scene_id:
        sc = await db.get(Scene, scene_id)
        if sc and sc.project_id == pid:
            ch = await db.get(Chapter, sc.chapter_id)
            parts = [f"Cảnh hiện tại: \"{_clip(sc.title, 120) or '(chưa đặt tên)'}\" "
                     f"— Chương \"{_clip(ch.title if ch else '?', 120)}\""]
            if sc.scene_type: parts.append(f"Loại cảnh: {sc.scene_type}")
            if sc.skeleton: parts.append(f"Xương cảnh (ghi chú tác giả):\n{_clip(sc.skeleton, 1500)}")
            if sc.brief_json:
                try: brief = json.loads(sc.brief_json)
                except Exception: brief = {}
                if brief: parts.append(f"Author Brief: {json.dumps(brief, ensure_ascii=False)[:1500]}")
            if sc.prose and sc.prose.strip():
                tail = sc.prose.strip()[-1200:]
                parts.append(f"Văn đã viết (đoạn cuối):\n…{tail}")
            sections.append(("\n".join(parts), 0, "scene"))
            pool_parts += [sc.title or "", sc.skeleton or "", sc.brief_json or "",
                           (sc.prose or "")[-2000:]]
        else:
            sc = None

    # --- session memory: recent AI turns for this scene
    if sc and task in MEMORY_TASKS:
        turns = list((await db.scalars(
            select(AiTurn).where(AiTurn.project_id == pid, AiTurn.scope_id == sc.id)
            .order_by(AiTurn.created_at.desc()).limit(3))).all())
        if turns:
            block = "Nháp AI gần đây cho cảnh này (tham khảo, không phải canon):\n" + "\n".join(
                f"- [{t.task}] {_clip(t.reply_text, 500)}" for t in reversed(turns))
            sections.append((block, 1, f"session-turns({len(turns)})"))

    if proj and proj.description:
        sections.append((f"Premise truyện: {_clip(proj.description, 800)}", 2, "premise"))

    # --- summaries of ancestor scopes (scene→chapter→arc/volume→story)
    if sc:
        chain = await ancestor_chain(db, pid, "scene", sc.id)
        summ_lines = []
        for st, sid in chain[1:]:
            s = (await db.scalars(select(StorySummary).where(
                StorySummary.project_id == pid, StorySummary.scope_type == st,
                StorySummary.scope_id == sid, StorySummary.stale == False)  # noqa: E712
                .order_by(StorySummary.narrative_end.desc()).limit(1))).first()
            if s:
                summ_lines.append(f"- [{st}] {_clip(s.summary, 700)}")
        if summ_lines:
            sections.append(("Tóm tắt phần trên:\n" + "\n".join(summ_lines), 3, "summaries"))

    pool = "\n".join(pool_parts).lower()

    chars = list((await db.scalars(select(Character).where(Character.project_id == pid))).all())
    if chars:
        alias_map: dict[str, list[str]] = {}
        for a in (await db.scalars(select(Alias).where(Alias.project_id == pid))).all():
            if a.character_id and a.alias:
                alias_map.setdefault(a.character_id, []).append(a.alias)
        def c_score(c):
            if not pool.strip(): return 0
            hits = sum(1 for n in [c.name, *alias_map.get(c.id, [])]
                       if n and n.lower() in pool)
            return hits
        ranked = sorted(chars, key=lambda c: (-c_score(c), c.sort_order or 0, c.name or ""))[:15]
        block = "Nhân vật:\n" + "\n".join(
            f"- {c.name} ({c.role or '?'})" + (f": {_clip(c.summary, 220)}" if c.summary else "")
            for c in ranked)
        sections.append((block, 4, f"characters(ranked {len(ranked)}/{len(chars)})"))

    facts = list((await db.scalars(select(CanonFact).where(
        CanonFact.project_id == pid, CanonFact.truth_status.in_(["CANON", "PLANNED"])))).all())
    if facts:
        char_names = {c.id: (c.name or "").lower() for c in chars}
        def f_score(f):
            if not pool.strip(): return 0
            s = 0
            if f.predicate and f.predicate.lower() in pool: s += 1
            subj = char_names.get(f.subject_id or "")
            if subj and subj in pool: s += 2
            words = [w for w in (f.predicate or "").split() if len(w) >= 4]
            s += sum(1 for w in words if w.lower() in pool)
            return s
        ranked_f = sorted(facts, key=lambda f: (-f_score(f), f.predicate or ""))[:15]
        block = "Canon Facts (không được vi phạm):\n" + "\n".join(
            f"- [{f.truth_status}] {f.predicate}: {_clip(f.value_text, 200)}" for f in ranked_f)
        sections.append((block, 5, f"canon(ranked {len(ranked_f)}/{len(facts)})"))

    used, out, manifest = 0, [], []
    for text, _, label in sorted(sections, key=lambda s: s[1]):
        cost = _est(text)
        if used + cost <= budget:
            out.append(text); used += cost
            manifest.append(f"included ~{cost}tok [{label}]: {text.splitlines()[0][:50]}")
        else:
            manifest.append(f"omitted (budget) [{label}]: {text.splitlines()[0][:50]}")
    return "\n\n---\n\n".join(out), manifest


async def _open_threads_block(db: AsyncSession, pid: str) -> tuple[str | None, int]:
    threads = list((await db.scalars(select(Thread).where(
        Thread.project_id == pid, Thread.status == "OPEN"))).all())
    if not threads:
        return None, 0
    block = "Hố/tuyến đang mở:\n" + "\n".join(
        f"- {th.title}" + (f" (payoff dự kiến ~mốc {th.planned_payoff_order})"
                           if th.planned_payoff_order else "")
        for th in threads[:10])
    return block, min(len(threads), 10)


async def build_story_prompt(db: AsyncSession, pid: str, task: str,
                             user_prompt: str, scene_id: str | None = None,
                             chapter_id: str | None = None
                             ) -> tuple[str | None, str, list[str]]:
    """Compose (system, prompt, context_manifest). Raw prompt for unknown tasks."""
    ctx, manifest = await _story_context(db, pid, scene_id, user_prompt, task)
    if task in {"writing", "expand", "scene_expand"}:
        constraints = ""
        if scene_id:
            sc = await db.get(Scene, scene_id)
            if sc and sc.project_id == pid:
                constraints = render_constraints(await build_constraints(db, pid, sc))
        if constraints:
            lines = constraints.splitlines()
            if len(lines) > 20:
                constraints = "\n".join(lines[:20]) + f"\n…(+{len(lines)-20} ràng buộc nữa)"
                manifest.append(f"constraints capped at 20/{len(lines)} lines")
            else:
                manifest.append(f"constraints: {len(lines)} lines")
            manifest.append("included constraints: ràng buộc từ StoryState/Knowledge/Thread")
            body = f"{constraints}\n\n{ctx}\n\n=== BRIEF CỦA TÁC GIẢ ===\n{user_prompt}" if ctx else f"{constraints}\n\n=== BRIEF CỦA TÁC GIẢ ===\n{user_prompt}"
        else:
            body = (f"{ctx}\n\n=== BRIEF CỦA TÁC GIẢ ===\n{user_prompt}"
                    if ctx else user_prompt)
        return WRITING_SYSTEM, body, manifest
    if task == "revision":
        constraints = ""
        if scene_id:
            sc = await db.get(Scene, scene_id)
            if sc and sc.project_id == pid:
                constraints = render_constraints(await build_constraints(db, pid, sc))
        if constraints:
            lines = constraints.splitlines()
            if len(lines) > 20:
                constraints = "\n".join(lines[:20]) + f"\n…(+{len(lines)-20} ràng buộc nữa)"
                manifest.append(f"constraints capped at 20/{len(lines)} lines")
            else:
                manifest.append(f"constraints: {len(lines)} lines")
        base = f"{constraints}\n\n{ctx}" if constraints and ctx else (constraints or ctx)
        body = (f"{base}\n\n=== YÊU CẦU SỬA ===\n{user_prompt}" if base else user_prompt)
        if constraints:
            manifest.append("included constraints: ràng buộc từ StoryState/Knowledge/Thread")
        return REVISION_SYSTEM, body, manifest
    if task == "extraction":
        body = (f"{ctx}\n\n=== VĂN CẦN TRÍCH ===\n{user_prompt}"
                if ctx else user_prompt)
        return EXTRACTION_SYSTEM, body, manifest
    if task == "skeleton":
        block, n = await _open_threads_block(db, pid)
        if block:
            ctx = f"{ctx}\n\n---\n\n{block}" if ctx else block
            manifest.append(f"included open threads: {n}")
        ask = user_prompt.strip() or "Dàn ý beats cho cảnh này."
        body = (f"{ctx}\n\n=== YÊU CẦU ===\n{ask}" if ctx else ask)
        return SKELETON_SYSTEM, body, manifest
    if task == "chapter_outline":
        extras = []
        if chapter_id:
            ch = await db.get(Chapter, chapter_id)
            if ch and ch.project_id == pid:
                lines = [f"Chương {ch.order_index}: \"{_clip(ch.title, 150)}\""]
                if ch.arc_id:
                    a = await db.get(Arc, ch.arc_id)
                    if a: lines.append(f"Hồi: {_clip(a.title, 120)}")
                if ch.volume_id:
                    v = await db.get(Volume, ch.volume_id)
                    if v: lines.append(f"Quyển: {_clip(v.title, 120)}")
                sibs = list((await db.scalars(select(Scene).where(
                    Scene.chapter_id == ch.id).order_by(Scene.order_index))).all())
                if sibs:
                    lines.append("Cảnh đã có: " + "; ".join(
                        (s.title or "?") for s in sibs[:20]))
                extras.append("Chương cần dàn ý:\n" + "\n".join(lines))
                manifest.append("included chapter-info")
        block, n = await _open_threads_block(db, pid)
        if block:
            extras.append(block)
            manifest.append(f"included open threads: {n}")
        parts = [p for p in [ctx, *extras] if p]
        ask = user_prompt.strip() or "Đề xuất 3-7 cảnh cho chương này."
        parts.append(f"=== YÊU CẦU ===\n{ask}")
        return CHAPTER_OUTLINE_SYSTEM, "\n\n---\n\n".join(parts), manifest
    if task == "summarization":
        return SUMMARIZE_SYSTEM, user_prompt, manifest
    if task in {"discussion", "chat", "brainstorm"}:
        return None, user_prompt, manifest
    return None, user_prompt, manifest
