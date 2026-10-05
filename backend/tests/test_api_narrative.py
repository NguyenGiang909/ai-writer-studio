
import pytest

@pytest.mark.asyncio
async def test_thread_crud_and_beats(client,proj):
    pid=proj["project"]["id"]
    t=(await client.post(f"/api/v1/projects/{pid}/threads",json={
        "title":"Who killed?","thread_type":"mystery"})).json()
    assert t["status"]=="OPEN"
    b=(await client.post(f"/api/v1/projects/{pid}/threads/{t['id']}/beats",json={
        "beat_type":"setup","scene_id":proj["scene"]["id"],"narrative_order":1})).json()
    assert b["thread_id"]==t["id"]
    beats=(await client.get(f"/api/v1/projects/{pid}/threads/{t['id']}/beats")).json()
    assert len(beats)==1
    r=await client.patch(f"/api/v1/projects/{pid}/threads/{t['id']}",json={"status":"RESOLVED"})
    assert r.json()["status"]=="RESOLVED"

@pytest.mark.asyncio
async def test_thread_dependency_guards(client,proj):
    pid=proj["project"]["id"]
    a=(await client.post(f"/api/v1/projects/{pid}/threads",json={"title":"A"})).json()
    b=(await client.post(f"/api/v1/projects/{pid}/threads",json={"title":"B"})).json()
    r=await client.post(f"/api/v1/projects/{pid}/thread-dependencies",json={
        "thread_id":a["id"],"depends_on_thread_id":a["id"]})
    assert r.status_code==400
    ok=(await client.post(f"/api/v1/projects/{pid}/thread-dependencies",json={
        "thread_id":a["id"],"depends_on_thread_id":b["id"]}))
    assert ok.status_code==200
    cyc=await client.post(f"/api/v1/projects/{pid}/thread-dependencies",json={
        "thread_id":b["id"],"depends_on_thread_id":a["id"]})
    assert cyc.status_code==400

@pytest.mark.asyncio
async def test_thread_scope_enforced(client,proj):
    other=(await client.post("/api/v1/projects",json={"name":"B"})).json()
    t=(await client.post(f"/api/v1/projects/{proj['project']['id']}/threads",json={"title":"A"})).json()
    r=await client.post(f"/api/v1/projects/{other['id']}/threads/{t['id']}/beats",json={"beat_type":"setup"})
    assert r.status_code==400
