
from dataclasses import dataclass
@dataclass
class Issue:
    code:str; category:str; severity:str; message:str; evidence:dict
def dedupe(issues:list[Issue]):
    out={}; rank={"info":0,"warning":1,"error":2}
    for i in issues:
        key=(i.code,tuple(sorted((str(k),str(v)) for k,v in (i.evidence or {}).items())))
        if key not in out or rank.get(i.severity,0)>rank.get(out[key].severity,0): out[key]=i
    return list(out.values())
def knowledge_leak(known_narrative_order:int|None,scene_narrative_order:int|None):
    if known_narrative_order is not None and scene_narrative_order is not None and known_narrative_order>scene_narrative_order:
        return Issue("KNOWLEDGE_LEAK","knowledge","error","Information is acquired later in narrative history.",{"acquired":known_narrative_order,"scene":scene_narrative_order})
def knowledge_leak_time(acquired_story_time:int|None,scene_story_time:int|None):
    if acquired_story_time is not None and scene_story_time is not None and acquired_story_time>scene_story_time:
        return Issue("KNOWLEDGE_LEAK_TIME","knowledge","error","Information is acquired later in story time.",{"acquired":acquired_story_time,"scene":scene_story_time})

NON_PHYSICAL_SCENE_TYPES={"flashback","dream","memory","hallucination","vision","reflection"}
_RESTRICTED_LIFE={"DEAD":"đã chết","MISSING":"đang mất tích","IMPRISONED":"đang bị giam","COMA":"đang hôn mê","EXITED":"đã rời mạch truyện"}

def restricted_appearance(char_name:str,lifecycle:str,scene_type:str|None,state_time:int|None,scene_time:int|None,scene_id:str,char_id:str):
    """Character whose lifecycle forbids physical presence appears in scene prose."""
    v=(lifecycle or "").strip().upper()
    if v not in _RESTRICTED_LIFE: return None
    if (scene_type or "").lower() in NON_PHYSICAL_SCENE_TYPES: return None
    # temporal check only when both ends are known — avoids flashback false positives
    if state_time is not None and scene_time is not None and scene_time<state_time: return None
    return Issue("RESTRICTED_APPEARANCE","lifecycle","error",
        f"{char_name} {_RESTRICTED_LIFE[v]} nhưng lại xuất hiện trong cảnh này (tên được nhắc trong văn).",
        {"character_id":char_id,"scene_id":scene_id,"lifecycle":v,
         "state_time":state_time,"scene_time":scene_time})

def location_conflict(char_name:str,char_loc:str,scene_loc_name:str,scene_loc_id:str|None,
                      state_time:int|None,scene_time:int|None,scene_id:str,char_id:str):
    """Character's recorded location differs from the scene's location at the same time."""
    if not char_loc or not scene_loc_name: return None
    cl=char_loc.strip().lower(); sl=scene_loc_name.strip().lower()
    if cl==sl or cl==str(scene_loc_id or "").lower(): return None
    if state_time is not None and scene_time is not None and scene_time<state_time: return None
    return Issue("LOCATION_CONFLICT","place","warning",
        f"{char_name} đang được ghi ở '{char_loc}' nhưng xuất hiện trong cảnh tại '{scene_loc_name}'.",
        {"character_id":char_id,"scene_id":scene_id,"char_location":char_loc,
         "scene_location":scene_loc_name,"state_time":state_time,"scene_time":scene_time})

def ability_locked(ability_name:str,unlock_state:str|None,unlock_time:int|None,scene_time:int|None,
                   scene_id:str,ability_id:str):
    """Ability is used in prose but has no UNLOCKED state at/before scene story_time."""
    if unlock_state is None and unlock_time is None: return None
    if unlock_time is not None and scene_time is not None and unlock_time>scene_time:
        return Issue("ABILITY_NOT_UNLOCKED","ability","warning",
            f"Năng lực '{ability_name}' được nhắc/dùng trong cảnh nhưng chỉ được mở khoá ở story_time {unlock_time}.",
            {"ability_id":ability_id,"scene_id":scene_id,"unlocked_at":unlock_time,"scene_time":scene_time})
    if unlock_state and unlock_state.strip().upper() not in ("UNLOCKED","ACTIVE","KNOWN"):
        return Issue("ABILITY_NOT_UNLOCKED","ability","warning",
            f"Năng lực '{ability_name}' được nhắc/dùng trong cảnh nhưng trạng thái hiện tại là '{unlock_state}'.",
            {"ability_id":ability_id,"scene_id":scene_id,"state":unlock_state,"scene_time":scene_time})
    return None

def item_owner_mismatch(item_name:str,item_id:str,owner_name:str|None,owner_id:str|None,
                        present_char_ids:set[str],scene_id:str):
    """Item appears in prose; recorded owner is absent while other characters are present."""
    if not owner_id: return None
    if owner_id in present_char_ids: return None
    if not present_char_ids: return None
    return Issue("ITEM_OWNER_MISMATCH","item","warning",
        f"'{item_name}' đang được ghi thuộc về {owner_name or owner_id} nhưng người đó không có mặt trong cảnh.",
        {"item_id":item_id,"owner_id":owner_id,"scene_id":scene_id})

_ENDED_REL={"ENDED","BROKEN","ESTRANGED","HOSTILE","ENEMY","EX"}
def relationship_ended(a_name:str,b_name:str,rel_state:str,rel_id:str,scene_id:str):
    """Both members of an ended/hostile relationship co-appear — check tone of interaction."""
    v=(rel_state or "").strip().upper()
    if v not in _ENDED_REL: return None
    return Issue("RELATIONSHIP_CONFLICT","relationship","warning",
        f"Quan hệ {a_name} ↔ {b_name} đang ở trạng thái {v} nhưng cả hai cùng xuất hiện — kiểm tra tông tương tác.",
        {"relationship_id":rel_id,"scene_id":scene_id,"state":v})

def stale_thread(thread,last_touched_order:int|None,current_order:int|None,gap:int=15):
    if current_order is None: return None
    base=last_touched_order if last_touched_order is not None else 0
    if thread.planned_payoff_order is not None and current_order>thread.planned_payoff_order:
        return Issue("THREAD_OVERDUE","narrative_debt","warning",
            f"Hố '{thread.title}' đã qua cửa sổ payoff dự kiến (Ch{thread.planned_payoff_order}).",
            {"thread_id":thread.id,"planned_payoff":thread.planned_payoff_order,"current":current_order})
    if current_order-base>=gap:
        return Issue("STALE_THREAD","narrative_debt","warning",
            f"Hố '{thread.title}' nằm im ~{current_order-base} chương kể từ lần chạm cuối.",
            {"thread_id":thread.id,"last_touched":base,"current":current_order})
    return None
