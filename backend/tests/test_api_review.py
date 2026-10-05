
import pytest

@pytest.mark.asyncio
async def test_suggestion_lifecycle(client,proj):
    pid=proj["project"]["id"]
    s=(await client.post(f"/api/v1/projects/{pid}/suggestions",json={
        "scene_id":proj["scene"]["id"],"change_type":"note",
        "payload":{"text":"check this"}})).json()
    assert s["status"]=="pending" and s["auto_applied"] is False
    r=(await client.post(f"/api/v1/projects/{pid}/suggestions/{s['id']}/reject")).json()
    assert r["status"]=="rejected"
    again=await client.post(f"/api/v1/projects/{pid}/suggestions/{s['id']}/approve")
    assert again.status_code==400

@pytest.mark.asyncio
async def test_approve_canon_fact_materializes_inferred(client,proj):
    pid=proj["project"]["id"]
    s=(await client.post(f"/api/v1/projects/{pid}/suggestions",json={
        "scene_id":proj["scene"]["id"],"change_type":"canon_fact",
        "payload":{"subject_type":"character","predicate":"eyes","value_text":"green"}})).json()
    r=(await client.post(f"/api/v1/projects/{pid}/suggestions/{s['id']}/approve")).json()
    assert r["status"]=="approved" and r["materialized"] is True
    facts=(await client.get(f"/api/v1/projects/{pid}/canon-facts")).json()
    assert len(facts)==1 and facts[0]["truth_status"]=="INFERRED" and facts[0]["locked"] is False

@pytest.mark.asyncio
async def test_approve_story_event_materializes(client,proj):
    pid=proj["project"]["id"]
    s=(await client.post(f"/api/v1/projects/{pid}/suggestions",json={
        "scene_id":proj["scene"]["id"],"change_type":"story_event",
        "payload":{"event_type":"duel","summary":"They fight"}})).json()
    r=(await client.post(f"/api/v1/projects/{pid}/suggestions/{s['id']}/approve")).json()
    events=(await client.get(f"/api/v1/projects/{pid}/story-events")).json()
    assert len(events)==1 and events[0]["event_type"]=="duel" and events[0]["scene_id"]==proj["scene"]["id"]

@pytest.mark.asyncio
async def test_approve_ai_draft_appends_to_scene_prose(client,proj):
    pid=proj["project"]["id"]; sid=proj["scene"]["id"]
    s=(await client.post(f"/api/v1/projects/{pid}/suggestions",json={
        "scene_id":sid,"change_type":"ai_draft",
        "payload":{"text":"Đoạn văn AI đề xuất."}})).json()
    r=(await client.post(f"/api/v1/projects/{pid}/suggestions/{s['id']}/approve")).json()
    assert r["materialized"] is True
    tree=(await client.get(f"/api/v1/projects/{pid}/manuscript")).json()
    scene=[x for c in tree["chapters"] for x in c["scenes"] if x["id"]==sid][0]
    assert "Đoạn văn AI đề xuất." in scene["prose"]

@pytest.mark.asyncio
async def test_pending_filter(client,proj):
    pid=proj["project"]["id"]
    await client.post(f"/api/v1/projects/{pid}/suggestions",json={"change_type":"a","payload":{}})
    s=(await client.post(f"/api/v1/projects/{pid}/suggestions",json={"change_type":"b","payload":{}})).json()
    await client.post(f"/api/v1/projects/{pid}/suggestions/{s['id']}/reject")
    pending=(await client.get(f"/api/v1/projects/{pid}/suggestions",params={"status":"pending"})).json()
    assert len(pending)==1 and pending[0]["change_type"]=="a"
