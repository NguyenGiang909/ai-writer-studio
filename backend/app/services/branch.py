
ALLOWED={"canon_override","thread_plan","scene_plan","chapter_plan","plan_note"}
def validate_change(change_type,payload):
    if change_type not in ALLOWED: raise ValueError("unsupported branch change")
    if not isinstance(payload,dict): raise ValueError("payload must be object")
    return payload
def merge_contract(change):
    if change.get("merged_decision_id"): return {"idempotent":True,"decision_id":change["merged_decision_id"]}
    return {"idempotent":False,"artifact":"AuthorDecision","mutates_canon":False,"mutates_manuscript":False}
