"""Style memory — gu văn tác giả (port từ Novel Humanizer v3 STYLE_MEMORY).

Rule = StylePreference (profile chứa). Chỉ rule status=confirmed được inject
vào prompt; candidate là gợi ý AI suy ra chờ tác giả duyệt — anti-overfitting:
edit do AI tự sinh không tính feedback; ≥2 candidate cùng hướng mới đáng nâng
scope (tác giả quyết, không tự ép).
"""
import json
from datetime import datetime as _dt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.manuscript import Scene, Chapter
from app.models.story import StyleProfile, Character
from app.models.discussion import StylePreference

LEARNING_PROFILE_NAME = "AI tự học"

_SCOPE_ORDER = {"scene": 0, "scene_type": 0, "chapter": 1, "character": 1,
                "character_voice": 1, "arc": 2, "global": 3}


async def _learning_profile(db: AsyncSession, pid: str) -> StyleProfile:
    """Profile chứa rule AI học được — tạo lười khi cần."""
    p = (await db.scalars(select(StyleProfile).where(
        StyleProfile.project_id == pid,
        StyleProfile.name == LEARNING_PROFILE_NAME))).first()
    if not p:
        p = StyleProfile(project_id=pid, name=LEARNING_PROFILE_NAME,
                         scope_type="global", active=True,
                         instructions="Luật AI học từ phản hồi/chỉnh sửa của "
                                      "tác giả — mục riêng mỗi rule mới hiệu lực.")
        db.add(p)
        await db.flush()
    return p


def _rule_scope(rule: StylePreference, prof: StyleProfile) -> tuple[str, str | None]:
    """Scope hiệu lực của rule — override trên rule thắng scope profile."""
    st = rule.scope_type or prof.scope_type or "global"
    sid = rule.scope_id if rule.scope_type else (rule.scope_id or prof.scope_id)
    return st, sid


async def _scope_ctx(db: AsyncSession, pid: str, scene: Scene | None) -> dict:
    """ID không gian hiện tại để khớp scope: arc/chapter/scene/characters."""
    ctx = {"arc_id": None, "chapter_id": None, "scene_id": None,
           "scene_type": None, "character_ids": set()}
    if scene and scene.project_id == pid:
        ctx["scene_id"] = scene.id
        ctx["scene_type"] = scene.scene_type
        ch = await db.get(Chapter, scene.chapter_id) if scene.chapter_id else None
        if ch:
            ctx["chapter_id"] = ch.id
            ctx["arc_id"] = ch.arc_id
            if ch.cast_json:
                try:
                    cast = json.loads(ch.cast_json)
                    ctx["character_ids"] = set(cast.get("characters") or [])
                except Exception:
                    pass
        if scene.pov_character_id:
            ctx["character_ids"].add(scene.pov_character_id)
    return ctx


def _scope_match(st: str, sid: str | None, ctx: dict) -> bool:
    if st in ("global", "project"):
        return True
    if st == "arc":
        return bool(sid) and sid == ctx.get("arc_id")
    if st == "chapter":
        return bool(sid) and sid == ctx.get("chapter_id")
    if st in ("scene", "scene_type"):
        return bool(sid) and sid in (ctx.get("scene_id"), ctx.get("scene_type"))
    if st in ("character", "character_voice"):
        return bool(sid) and sid in ctx.get("character_ids", set())
    return False


def render_rule(r: StylePreference) -> str:
    """Một dòng luật cho prompt — ngắn gọn, có nhãn sức mạnh."""
    head = {"prefer": "", "avoid": "TRÁNH: "}.get(r.preference_type, "")
    attr = f"{r.attribute}: " if r.attribute else ""
    tag = {"HARD": " [BẮT BUỘC]", "AVOID": " [NÊN TRÁNH]",
           "OPEN": " [THAM KHẢO]"}.get(r.strength, "")
    return f"- {head}{attr}{r.pattern}{tag}"


async def render_style_block(db: AsyncSession, pid: str,
                             scene: Scene | None = None) -> tuple[str, int]:
    """Block 'Gu văn tác giả' cho prompt: profile đang active (khớp scope) +
    rule confirmed. Trả (text, số rule)."""
    profs = {p.id: p for p in (await db.scalars(
        select(StyleProfile).where(StyleProfile.project_id == pid,
                                   StyleProfile.active == True))).all()}  # noqa: E712
    rules = [r for r in (await db.scalars(
        select(StylePreference).where(StylePreference.project_id == pid,
                                      StylePreference.status == "confirmed"))).all()
             if r.style_profile_id in profs]
    if not profs and not rules:
        return "", 0
    ctx = await _scope_ctx(db, pid, scene)

    prof_lines, rule_lines = [], []
    for p in profs.values():
        if (p.instructions or "").strip() and _scope_match(
                p.scope_type, p.scope_id, ctx):
            prof_lines.append(f"[{p.name}] {(p.instructions or '').strip()[:700]}")
    for r in rules:
        st, sid = _rule_scope(r, profs[r.style_profile_id])
        if _scope_match(st, sid, ctx):
            rule_lines.append((_SCOPE_ORDER.get(st, 3), r))
    if not prof_lines and not rule_lines:
        return "", 0
    rule_lines.sort(key=lambda x: (x[0], x[1].id))
    n = 0
    out = ["Gu văn tác giả đã chốt (ưu tiên cao hơn mặc định — không được "
           "'làm mượt' trái ý):"]
    out += prof_lines[:4]
    for _, r in rule_lines[:16]:
        out.append(render_rule(r))
        n += 1
    return "\n".join(out), n


async def add_explicit_rule(db: AsyncSession, pid: str, pattern: str,
                            attribute: str | None = None,
                            strength: str = "PREFERRED",
                            polarity: str = "prefer",
                            scope_type: str | None = None,
                            scope_id: str | None = None,
                            evidence: str | None = None,
                            profile_id: str | None = None) -> StylePreference:
    """Luật tác giả chủ động nói → confirmed ngay, không hỏi lại."""
    prof = (await db.get(StyleProfile, profile_id) if profile_id
            else await _learning_profile(db, pid))
    if not prof or prof.project_id != pid:
        prof = await _learning_profile(db, pid)
    r = StylePreference(
        project_id=pid, style_profile_id=prof.id,
        preference_type=polarity if polarity in ("prefer", "avoid") else "prefer",
        pattern=pattern.strip(), strength=strength or "PREFERRED",
        status="confirmed", source="explicit",
        attribute=attribute, scope_type=scope_type, scope_id=scope_id,
        evidence=evidence, updated_at=_dt.utcnow().isoformat())
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return r


async def add_candidates(db: AsyncSession, pid: str, rules: list[dict],
                         source: str = "inferred") -> list[StylePreference]:
    """Rule AI suy ra → candidate chờ duyệt. Dedupe theo pattern chuẩn hoá."""
    prof = await _learning_profile(db, pid)
    have = {((r.pattern or "").strip().lower()) for r in (await db.scalars(
        select(StylePreference).where(StylePreference.project_id == pid))).all()}
    made = []
    for d in rules[:12]:
        pat = (d.get("pattern") or "").strip()
        if not pat or pat.lower() in have:
            continue
        have.add(pat.lower())
        r = StylePreference(
            project_id=pid, style_profile_id=prof.id,
            preference_type=d.get("preference_type") if d.get("preference_type") in ("prefer", "avoid") else "prefer",
            pattern=pat[:600],
            strength=d.get("strength") if d.get("strength") in ("HARD", "PREFERRED", "AVOID", "OPEN") else "PREFERRED",
            status="candidate", source=source,
            attribute=(d.get("attribute") or "")[:80] or None,
            scope_type=d.get("scope_type"), scope_id=d.get("scope_id"),
            evidence=(d.get("evidence") or "")[:800] or None,
            updated_at=_dt.utcnow().isoformat())
        db.add(r)
        made.append(r)
    await db.commit()
    for r in made:
        await db.refresh(r)
    return made


async def learn_from_diff(db: AsyncSession, pid: str, original: str,
                          revised: str, comment: str | None,
                          router_call) -> list[StylePreference]:
    """Diff sửa của tác giả → task style_learn → candidate rules.

    router_call = hàm async (system, prompt, task) -> text — route đưa
    ModelRouter vào để service không phụ thuộc layer AI."""
    from app.ai.compose import STYLE_LEARN_SYSTEM
    prompt = (
        f"=== ĐOẠN GỐC (bản AI/cũ) ===\n{original[:4000]}\n\n"
        f"=== ĐOẠN TÁC GIẢ SỬA ===\n{revised[:4000]}\n\n"
        + (f"=== LỜI TÁC GIẢ GIẢI THÍCH ===\n{comment[:800]}\n\n" if comment else "")
        + "Trích ra các QUY TẮC PHONG CÁCH mà lần sửa này cho thấy — chỉ "
        "những gì suy ra được từ diff, không bịa. JSON theo schema system.")
    txt = await router_call(STYLE_LEARN_SYSTEM, prompt, "style_learn")
    import re as _re
    m = _re.search(r"\[.*\]", txt or "", _re.DOTALL)
    data = []
    if m:
        try:
            data = json.loads(m.group())
        except Exception:
            data = []
    src = "approved_edit" if comment else "observed_edit"
    return await add_candidates(db, pid, data, source=src)


async def character_names(db: AsyncSession, pid: str) -> dict[str, str]:
    return {c.id: c.name for c in (await db.scalars(
        select(Character).where(Character.project_id == pid))).all()}
