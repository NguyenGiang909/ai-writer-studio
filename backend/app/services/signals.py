"""GĐ9 long-novel health signals — pure functions over loaded rows.

Three signals:
- cast dormancy: characters whose names stopped appearing in prose
- thread health: open threads by beats / last touched / payoff window
- repetition: sentences repeated across scenes (motif or accidental reuse)
"""
import re
from dataclasses import dataclass

DORMANT_GAP = 10
STALE_GAP = 15
_SENT_SPLIT = re.compile(r"[.!?…\n]+")
_WS = re.compile(r"\s+")


def scene_order(scene, chapter_order: int | None = None) -> int | None:
    return scene.narrative_order if scene.narrative_order is not None else chapter_order


def character_terms(character, aliases) -> list[str]:
    """Name + aliases + standalone tokens (>=4 chars) used for prose matching."""
    ts = [character.name] if character.name else []
    ts += [a.alias for a in aliases if a.character_id == character.id and a.alias]
    ts += [w for w in re.split(r"\s+", character.name or "") if len(w) >= 4]
    return [t for t in dict.fromkeys(ts) if t]


def name_in_prose(term: str, prose: str) -> bool:
    if " " in term:
        return bool(re.search(r"\b" + re.escape(term) + r"\b", prose, re.IGNORECASE))
    return bool(re.search(r"\b" + re.escape(term) + r"\b", prose))


def cast_dormancy(scenes, characters, aliases, life_states=None,
                  gone_values=("DEAD", "EXITED"), gap: int = DORMANT_GAP) -> list[dict]:
    """Characters absent from prose for >= gap narrative positions.

    life_states: StoryState rows (entity_type=character, key=lifecycle) used to
    mark characters written out of the story (DEAD/EXITED) as "gone" instead
    of "dormant" — absence is intentional for them.
    """
    terms = {c.id: character_terms(c, aliases) for c in characters}
    life: dict[str, str] = {}
    for st in (life_states or []):
        cur = life.get(st.entity_id)
        if cur is None or (st.story_time or -1) >= (cur[1] or -1):
            life[st.entity_id] = (st.value_text, st.story_time)
    gone = {cid for cid, (v, _t) in life.items()
            if (v or "").upper() in gone_values}
    last_seen: dict[str, int] = {}
    orders = []
    for sc in scenes:
        o = sc.narrative_order
        if o is None:
            continue
        orders.append(o)
        if not sc.prose:
            continue
        for c in characters:
            if any(name_in_prose(t, sc.prose) for t in terms.get(c.id, [])):
                last_seen[c.id] = max(last_seen.get(c.id, 0), o)
    current = max(orders) if orders else None
    out = []
    for c in characters:
        seen = last_seen.get(c.id)
        g = (current - seen) if (seen is not None and current is not None) else None
        if c.id in gone:
            flag = "gone"
        elif seen is None:
            flag = "never"
        elif g is not None and g >= gap:
            flag = "dormant"
        else:
            flag = "ok"
        out.append({"character_id": c.id, "name": c.name, "last_seen_order": seen,
                    "gap": g, "flag": flag})
    rank = {"dormant": 0, "never": 1, "ok": 2, "gone": 3}
    out.sort(key=lambda r: (rank.get(r["flag"], 9), -(r["gap"] or 10 ** 9)))
    return out


def thread_health(threads, beats, current_order: int | None,
                  gap: int = STALE_GAP) -> list[dict]:
    last, count = {}, {}
    for b in beats:
        count[b.thread_id] = count.get(b.thread_id, 0) + 1
        if b.narrative_order is not None:
            last[b.thread_id] = max(last.get(b.thread_id, 0), b.narrative_order)
    out = []
    for th in threads:
        lo = last.get(th.id)
        g = (current_order - lo) if (lo is not None and current_order is not None) else None
        if th.status != "OPEN":
            flag = "closed"
        elif th.planned_payoff_order is not None and current_order is not None \
                and current_order > th.planned_payoff_order:
            flag = "overdue"
        elif g is not None and g >= gap:
            flag = "stale"
        elif lo is None:
            flag = "untouched"
        else:
            flag = "ok"
        out.append({"thread_id": th.id, "title": th.title, "status": th.status,
                    "beats": count.get(th.id, 0), "last_order": lo, "gap": g,
                    "planned_payoff_order": th.planned_payoff_order, "flag": flag})
    rank = {"overdue": 0, "stale": 1, "untouched": 2, "ok": 3, "closed": 4}
    out.sort(key=lambda r: (rank.get(r["flag"], 9), -(r["gap"] or 0)))
    return out


def repetition_candidates(scenes, min_words: int = 6, min_scenes: int = 2,
                          limit: int = 30) -> list[dict]:
    """Sentences repeated across scenes — motif (fine) or accidental reuse."""
    seen: dict[str, dict] = {}
    for sc in scenes:
        if not sc.prose:
            continue
        local = set()
        for s in _SENT_SPLIT.split(sc.prose):
            n = _WS.sub(" ", s.strip()).lower()
            if len(n.split()) >= min_words:
                local.add(n)
        for n in local:
            e = seen.setdefault(n, {"text": n, "count": 0, "scene_ids": []})
            e["count"] += 1
            e["scene_ids"].append(sc.id)
    out = [e for e in seen.values() if e["count"] >= min_scenes]
    out.sort(key=lambda e: -e["count"])
    return out[:limit]
