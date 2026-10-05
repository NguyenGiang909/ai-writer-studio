
from app.services.memory import invalidate_chain,bounded_backlog,impact_preview
def test_hierarchy_and_bounded_maintenance():
    assert invalidate_chain("scene")==["scene","chapter","arc","volume","story"]
    x=[{"scope_type":"story","stale":True},{"scope_type":"scene","stale":True}]
    assert bounded_backlog(x,1)[0]["scope_type"]=="scene"
def test_impact_is_preview_only():
    x=impact_preview("scene","s1",[{"references":["s1"],"id":"later"}]); assert x["auto_apply"] is False
