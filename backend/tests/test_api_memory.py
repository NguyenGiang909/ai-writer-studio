
import pytest

@pytest.mark.asyncio
async def test_summary_crud_and_scope(client,proj):
    pid=proj["project"]["id"]
    s=(await client.post(f"/api/v1/projects/{pid}/summaries",json={
        "scope_type":"scene","scope_id":proj["scene"]["id"],"summary":"Opening happens."})).json()
    assert s["stale"] is False
    bad=await client.post(f"/api/v1/projects/{pid}/summaries",json={
        "scope_type":"bogus","scope_id":"x","summary":"nope"})
    assert bad.status_code==400
    r=await client.patch(f"/api/v1/projects/{pid}/summaries/{s['id']}",json={"summary":"Revised."})
    assert r.json()["summary"]=="Revised."

@pytest.mark.asyncio
async def test_summary_invalidate_walks_ancestors(client,proj):
    pid=proj["project"]["id"]
    sc, ch = proj["scene"], proj["chapter"]
    ss=(await client.post(f"/api/v1/projects/{pid}/summaries",json={
        "scope_type":"scene","scope_id":sc["id"],"summary":"s"})).json()
    cs=(await client.post(f"/api/v1/projects/{pid}/summaries",json={
        "scope_type":"chapter","scope_id":ch["id"],"summary":"c"})).json()
    st=(await client.post(f"/api/v1/projects/{pid}/summaries",json={
        "scope_type":"story","scope_id":pid,"summary":"t"})).json()
    r=(await client.post(f"/api/v1/projects/{pid}/summaries/{ss['id']}/invalidate")).json()
    assert set(r["marked_stale"])=={ss["id"],cs["id"],st["id"]}
    backlog=(await client.get(f"/api/v1/projects/{pid}/summaries/stale-backlog")).json()
    assert len(backlog)==3 and backlog[0]["scope_type"]=="scene"

@pytest.mark.asyncio
async def test_retcon_and_impact_preview(client,proj):
    pid=proj["project"]["id"]
    t1=(await client.post(f"/api/v1/projects/{pid}/threads",json={"title":"A"})).json()
    t2=(await client.post(f"/api/v1/projects/{pid}/threads",json={"title":"B"})).json()
    await client.post(f"/api/v1/projects/{pid}/thread-dependencies",json={
        "thread_id":t1["id"],"depends_on_thread_id":t2["id"]})
    r=(await client.post(f"/api/v1/projects/{pid}/retcon-proposals",json={
        "target_type":"thread","target_id":t2["id"],"proposal":"change B"})).json()
    snap=(await client.get(f"/api/v1/projects/{pid}/retcon-proposals")).json()[0]
    assert snap["impact"]["auto_apply"] is False
    hits=snap["impact"]["affected"]
    assert any(h["kind"]=="thread_dependency" for h in hits)
    pv=(await client.get(f"/api/v1/projects/{pid}/impact-preview",
        params={"target_type":"thread","target_id":t1["id"]})).json()
    assert pv["auto_apply"] is False
