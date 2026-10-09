
import re
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

# ---- audit toàn project: lớp lỗi dữ liệu/pha truyện (thấy từ ch2 project 58ch) ----

def _uniq_vals(values:list[str]):
    seen={}
    for v in values:
        k=re.sub(r"\s+"," ",(v or "").strip().lower())
        if k and k not in seen: seen[k]=(v or "").strip()
    out=list(seen.values())
    # bỏ giá trị là tập con của giá trị khác (near-duplicate, không phải mâu thuẫn)
    def _norm(x): return re.sub(r"\s+"," ",x.strip().lower())
    return [v for v in out
            if not any(v is not w and _norm(v) in _norm(w) for w in out)]

def _options_from(items:list[tuple[str,str]],vals:list[str]):
    """Mỗi unique value → list id fact/state mang giá trị đó (cho nút 'giữ giá trị này')."""
    def nv(x): return re.sub(r"\s+"," ",(x or "").strip().lower())
    return [{"value":v,"ids":[i for i,iv in items if nv(iv)==nv(v)]} for v in vals]

def canon_conflict(subject_label:str,predicate:str,fact_ids:list[str],values:list[str],
                   character_id:str|None=None):
    """Canon facts cùng (subject, predicate) nhưng giá trị khác nhau — tuổi/nghề/quê lệch nhau."""
    vals=_uniq_vals(values)
    if len(vals)<2: return None
    show=" · ".join(f"'{v[:40]}'" for v in vals[:5])
    return Issue("CANON_CONFLICT","canon","warning",
        f"'{predicate}' của {subject_label} có {len(vals)} giá trị mâu thuẫn: {show} — cần tác giả chốt một.",
        {"fact_id":fact_ids[0],"predicate":predicate,
         "options":_options_from(list(zip(fact_ids,values)),vals),
         "character_id":character_id})

def state_conflict(entity_label:str,key:str,narr:int|None,state_ids:list[str],values:list[str],
                   entity_type:str,entity_id:str):
    """Cùng entity+key tại cùng vị trí narrative mà 2 giá trị khác nhau."""
    vals=_uniq_vals(values)
    if len(vals)<2: return None
    where=f"chương {narr}" if narr is not None else "vị trí chưa gán"
    show=" · ".join(f"'{v[:40]}'" for v in vals[:4])
    return Issue("STATE_CONFLICT","state","warning",
        f"{entity_label} — '{key}' tại {where} có {len(vals)} giá trị mâu thuẫn: {show}.",
        {"entity_type":entity_type,"entity_id":entity_id,"key":key,"narrative_order":narr,
         "options":_options_from(list(zip(state_ids,values)),vals),
         "character_id":entity_id if entity_type=="character" else None})

_VN_NUM={"một":1,"mốt":1,"hai":2,"ba":3,"bốn":4,"tư":4,"năm":5,"lăm":5,"sáu":6,
         "bảy":7,"bẩy":7,"tám":8,"chín":9}
def num_from(text:str|None):
    """Số đầu tiên trong chuỗi, hoặc số chữ tiếng Việt (lớp Chín→9, lớp Sáu→6)."""
    if not text: return None
    m=re.search(r"\d+",text)
    if m: return int(m.group())
    tl=text.lower()
    if "mười" in tl:
        tail=tl.split("mười",1)[1]
        for w in tail.split():
            if w in _VN_NUM: return 10+_VN_NUM[w]
        return 10
    for w,n in _VN_NUM.items():
        if re.search(r"\b"+w+r"\b",tl): return n
    return None

def state_regression(entity_label:str,key:str,prev:tuple[int,str],cur:tuple[int,str],
                     entity_type:str,entity_id:str):
    """Tuổi/lớp giảm khi narrative_order tăng — mạch truyện không lùi tuổi nếu không có hồi ức."""
    pn,cn=num_from(prev[1]),num_from(cur[1])
    if pn is None or cn is None or cn>=pn: return None
    return Issue("STATE_REGRESSION","state","warning",
        f"{entity_label}: '{key}' lùi ngược mạch — '{prev[1]}' (chương {prev[0]}) → '{cur[1]}' (chương {cur[0]}).",
        {"entity_type":entity_type,"entity_id":entity_id,"key":key,
         "prev_narrative_order":prev[0],"prev_value":prev[1],
         "narrative_order":cur[0],"value":cur[1],
         "character_id":entity_id if entity_type=="character" else None})

def unplanned_location(loc_name:str,loc_id:str,scene_id:str,scene_title:str,scene_narr:int|None):
    """Prose nhắc một địa danh không nằm trong dàn ý cảnh lẫn trạng thái vị trí — nghi lệch pha."""
    return Issue("LOCATION_DRIFT","place","warning",
        f"Cảnh '{scene_title}' nhắc '{loc_name}' nhưng địa danh này không có trong xương cảnh "
        f"và không phải nơi ở đã ghi của nhân vật — kiểm tra lệch bối cảnh/pha truyện.",
        {"location_id":loc_id,"scene_id":scene_id,"narrative_order":scene_narr,
         "location":loc_name})

def phase_leak(entity_label:str,entity_type:str,entity_id:str,scene_id:str,
               scene_title:str,scene_narr:int|None,first_narr:int):
    """Entity được nhắc trong prose trước khi nó tồn tại trong trạng thái/sự kiện đã ghi."""
    return Issue("PHASE_LEAK","timeline","warning",
        f"Cảnh '{scene_title}' (chương {scene_narr}) nhắc {entity_label} nhưng thực thể này "
        f"mới xuất hiện trong dữ kiện từ chương {first_narr} — có thể lẫn pha truyện sau.",
        {"entity_type":entity_type,"entity_id":entity_id,"scene_id":scene_id,
         "scene_narrative_order":scene_narr,"first_narrative_order":first_narr,
         "location_id":entity_id if entity_type=="location" else None,
         "item_id":entity_id if entity_type=="item" else None})

def missing_extraction(chapter_id:str,chapter_title:str,order:int|None):
    """Chương đã có prose nhưng chưa trích sự kiện — các chương/cảnh sau thiếu bối cảnh."""
    return Issue("MISSING_EXTRACTION","pipeline","info",
        f"Chương {order} '{chapter_title}' có văn nhưng chưa trích dữ kiện (0 sự kiện) — "
        f"cảnh sau sẽ viết thiếu ngữ cảnh.",
        {"chapter_id":chapter_id,"narrative_order":order})

def scene_no_narr(scene_id:str,scene_title:str,chapter_order:int|None):
    """Scene có prose mà narrative_order NULL — cơ chế lọc theo vị trí không áp được."""
    return Issue("SCENE_NO_NARR","pipeline","info",
        f"Cảnh '{scene_title}' (chương {chapter_order}) có văn nhưng thiếu narrative_order — "
        f"trạng thái/knowledge không lọc theo vị trí được.",
        {"scene_id":scene_id,"chapter_order":chapter_order})

# ---- style: fatigue words — cụm lặp bất thường = dấu hiệu văn mẫu AI ----
_FUNC_WORDS=set("""và của là một những được trong đã cho với không có ở lại thì
vẫn rồi đến từ về ra lên xuống như khi mà nên cũng đây đó ấy này kia vậy thế đang
sẽ bị vì hay hoặc cả mỗi đều rất quá hơi hơn cùng chỉ ngay luôn tôi anh cô em
mình chị chú họ nó ta người""".split())

def fatigue_phrases(prose:str,min_count:int=8,max_out:int=5):
    """3-gram lặp ≥min_count trong MỘT chương — cụm phải chứa ít nhất 1 từ
    nội dung (không toàn hư từ) để tránh bắt cấu trúc câu bình thường."""
    words=re.findall(r"[a-zA-ZÀ-ỹĐđ]+",prose.lower())
    grams={}
    for i in range(len(words)-2):
        g=" ".join(words[i:i+3])
        grams[g]=grams.get(g,0)+1
    out=[(g,n) for g,n in grams.items() if n>=min_count
         and any(w not in _FUNC_WORDS for w in g.split())]
    return sorted(out,key=lambda x:-x[1])[:max_out]

def style_fatigue(phrase:str,count:int,chapter_id:str,chapter_order:int|None):
    return Issue("STYLE_FATIGUE","style","warning" if count>=10 else "info",
        f"Cụm '{phrase}' lặp {count} lần trong chương {chapter_order} — "
        f"nghi văn mẫu lặp, cân nhắc biến hoá câu.",
        {"chapter_id":chapter_id,"narrative_order":chapter_order,
         "phrase":phrase,"count":count})
