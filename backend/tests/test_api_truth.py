
import pytest

@pytest.mark.asyncio
async def test_canon_fact_crud(client,proj):
    pid=proj["project"]["id"]
    f=(await client.post(f"/api/v1/projects/{pid}/canon-facts",json={
        "subject_type":"character","predicate":"has_scar","value_text":"left cheek",
        "source_scene_id":proj["scene"]["id"]})).json()
    assert f["truth_status"]=="CANON"
    lst=(await client.get(f"/api/v1/projects/{pid}/canon-facts")).json()
    assert any(x["id"]==f["id"] for x in lst)
    r=await client.patch(f"/api/v1/projects/{pid}/canon-facts/{f['id']}",json={"truth_status":"REJECTED"})
    assert r.json()["truth_status"]=="REJECTED"

@pytest.mark.asyncio
async def test_canon_fact_rejects_foreign_scene(client,proj):
    pid=proj["project"]["id"]
    other=(await client.post("/api/v1/projects",json={"name":"B"})).json()
    ch=(await client.post(f"/api/v1/projects/{other['id']}/chapters",json={"title":"X","order_index":1})).json()
    sc=(await client.post(f"/api/v1/projects/{other['id']}/chapters/{ch['id']}/scenes",json={"order_index":1})).json()
    r=await client.post(f"/api/v1/projects/{pid}/canon-facts",json={
        "subject_type":"story","predicate":"p","value_text":"v","source_scene_id":sc["id"]})
    assert r.status_code==400

@pytest.mark.asyncio
async def test_decisions_events_secrets(client,proj):
    pid=proj["project"]["id"]
    d=(await client.post(f"/api/v1/projects/{pid}/author-decisions",json={"title":"D","decision_text":"keep"})).json()
    assert d["status"]=="active"
    ev=(await client.post(f"/api/v1/projects/{pid}/story-events",json={
        "scene_id":proj["scene"]["id"],"event_type":"meeting","summary":"A meets B","narrative_order":1})).json()
    assert ev["narrative_order"]==1
    f=(await client.post(f"/api/v1/projects/{pid}/canon-facts",json={
        "subject_type":"character","predicate":"secret","value_text":"is a spy"})).json()
    s=(await client.post(f"/api/v1/projects/{pid}/secrets",json={"fact_id":f["id"],"title":"Spy"})).json()
    assert s["fact_id"]==f["id"]

@pytest.mark.asyncio
async def test_story_state_as_of(client,proj):
    pid=proj["project"]["id"]
    await client.post(f"/api/v1/projects/{pid}/story-states",json={
        "entity_type":"character","entity_id":"c1","key":"location","value_text":"home","narrative_order":1})
    await client.post(f"/api/v1/projects/{pid}/story-states",json={
        "entity_type":"character","entity_id":"c1","key":"location","value_text":"away","narrative_order":5})
    r=(await client.get(f"/api/v1/projects/{pid}/story-states/as-of",
        params={"entity_id":"c1","key":"location","narrative_order":3})).json()
    assert r["value_text"]=="home"
    r=(await client.get(f"/api/v1/projects/{pid}/story-states/as-of",
        params={"entity_id":"c1","key":"location","narrative_order":9})).json()
    assert r["value_text"]=="away"

@pytest.mark.asyncio
async def test_knowledge_state_as_of(client,proj):
    pid=proj["project"]["id"]
    f=(await client.post(f"/api/v1/projects/{pid}/canon-facts",json={
        "subject_type":"story","predicate":"killer","value_text":"the butler"})).json()
    await client.post(f"/api/v1/projects/{pid}/knowledge-states",json={
        "knower_id":"hero","fact_id":f["id"],"state":"KNOWS","acquired_narrative_order":10})
    before=(await client.get(f"/api/v1/projects/{pid}/knowledge-states/as-of",
        params={"knower_id":"hero","narrative_order":5})).json()
    assert before==[]
    after=(await client.get(f"/api/v1/projects/{pid}/knowledge-states/as-of",
        params={"knower_id":"hero","narrative_order":12})).json()
    assert len(after)==1 and after[0]["state"]=="KNOWS"


@pytest.mark.asyncio
async def test_decision_patch_and_delete(client, proj):
    pid = proj["project"]["id"]
    d = (await client.post(f"/api/v1/projects/{pid}/author-decisions", json={
        "title": "AD-1", "decision_text": "v1"})).json()
    p = (await client.patch(f"/api/v1/projects/{pid}/author-decisions/{d['id']}", json={
        "decision_text": "v2", "rationale": "đổi ý", "status": "superseded"})).json()
    assert p["decision_text"] == "v2" and p["status"] == "superseded" and p["rationale"] == "đổi ý"
    r = await client.delete(f"/api/v1/projects/{pid}/author-decisions/{d['id']}")
    assert r.status_code == 200
    assert (await client.get(f"/api/v1/projects/{pid}/author-decisions")).json() == []


@pytest.mark.asyncio
async def test_project_patch(client, proj):
    pid = proj["project"]["id"]
    p = (await client.patch(f"/api/v1/projects/{pid}", json={
        "description": "premise mới", "name": "Đổi tên"})).json()
    assert p["description"] == "premise mới" and p["name"] == "Đổi tên"
    bad = await client.patch("/api/v1/projects/nonexistent", json={"name": "x"})
    assert bad.status_code == 404


@pytest.mark.asyncio
async def test_project_delete_cascades(client, proj):
    pid = proj["project"]["id"]
    # seed related rows across domains
    c = (await client.post(f"/api/v1/projects/{pid}/characters", json={"name": "X"})).json()
    th = (await client.post(f"/api/v1/projects/{pid}/threads", json={"title": "T"})).json()
    await client.post(f"/api/v1/projects/{pid}/threads/{th['id']}/beats", json={"beat_type": "setup"})
    await client.post(f"/api/v1/projects/{pid}/canon-facts", json={
        "subject_type": "character", "subject_id": c["id"],
        "predicate": "p", "value_text": "v"})
    await client.post(f"/api/v1/projects/{pid}/author-decisions",
                      json={"title": "D", "decision_text": "x"})
    r = await client.delete(f"/api/v1/projects/{pid}")
    assert r.status_code == 200
    # everything gone
    assert (await client.get(f"/api/v1/projects")).json() == [] or \
        all(p["id"] != pid for p in (await client.get(f"/api/v1/projects")).json())
    for ep in ["characters", "threads", "canon-facts", "author-decisions", "manuscript"]:
        resp = await client.get(f"/api/v1/projects/{pid}/{ep}")
        assert resp.status_code in (404, 200) and (resp.status_code == 404 or resp.json() in ([], {"chapters": []}) or not resp.json())
