
HIERARCHY=["scene","chapter","arc","volume","story"]

async def ancestor_chain(db, pid: str, scope_type: str, scope_id: str):
    """Walk scope → chapter → arc/volume → story. Returns [(type,id)] including self."""
    from app.models import Project, Volume, Arc, Chapter, Scene
    SCOPE={"scene":Scene,"chapter":Chapter,"arc":Arc,"volume":Volume,"story":Project}
    out=[(scope_type,scope_id)]
    cur_type,cur_id=scope_type,scope_id
    while cur_type!="story":
        rec=await db.get(SCOPE[cur_type],cur_id)
        if rec is None: break
        if cur_type=="scene": cur_type,cur_id="chapter",rec.chapter_id
        elif cur_type=="chapter":
            if rec.arc_id: cur_type,cur_id="arc",rec.arc_id
            elif rec.volume_id: cur_type,cur_id="volume",rec.volume_id
            else: cur_type,cur_id="story",pid
        elif cur_type=="arc": cur_type,cur_id=("volume",rec.volume_id) if rec.volume_id else ("story",pid)
        elif cur_type=="volume": cur_type,cur_id="story",pid
        out.append((cur_type,cur_id))
    return out

def invalidate_chain(scope_type):
    i=HIERARCHY.index(scope_type); return HIERARCHY[i:]
def bounded_backlog(items,limit=20):
    rank={x:i for i,x in enumerate(HIERARCHY)}
    return sorted([x for x in items if x.get("stale")],key=lambda x:rank.get(x.get("scope_type"),99))[:max(1,min(limit,100))]
def impact_preview(change_type,target_id,refs,depth=2):
    """Walk the reference graph: nodes whose `references` touch a reached id are affected.
    BFS up to `depth` hops; the target itself and already-visited ids are skipped."""
    seen={target_id}; frontier={target_id}; affected=[]; hit_ids=set()
    for hop in range(depth):
        nxt=set()
        for r in refs:
            if r["id"] in hit_ids: continue
            if set(r.get("references",[])) & frontier:
                r=dict(r); r["hop"]=hop+1; affected.append(r); hit_ids.add(r["id"])
                nxt|={x for x in r.get("references",[]) if x}
        frontier=nxt-seen; seen|=nxt
        if not frontier: break
    return {"change_type":change_type,"target_id":target_id,"affected":affected,
            "depth":depth,"auto_apply":False}
