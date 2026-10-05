import pytest

@pytest.mark.asyncio
async def test_health(client):
    r=await client.get("/health")
    assert r.status_code==200 and r.json()["status"]=="ok"

@pytest.mark.asyncio
async def test_project_manuscript_flow(client):
    p=(await client.post("/api/v1/projects",json={"name":"Novel A"})).json()
    v=(await client.post(f"/api/v1/projects/{p['id']}/volumes",json={"title":"Volume 1","order_index":1})).json()
    a=(await client.post(f"/api/v1/projects/{p['id']}/arcs",json={"title":"Arc 1","order_index":1,"volume_id":v["id"]})).json()
    ch=(await client.post(f"/api/v1/projects/{p['id']}/chapters",json={"title":"Chapter 1","order_index":1,"volume_id":v["id"],"arc_id":a["id"]})).json()
    sc=(await client.post(f"/api/v1/projects/{p['id']}/chapters/{ch['id']}/scenes",json={"title":"Opening","order_index":1,"prose":"Ten lines become a chapter later."})).json()
    tree=(await client.get(f"/api/v1/projects/{p['id']}/manuscript")).json()
    assert tree["chapters"][0]["scenes"][0]["id"]==sc["id"]

@pytest.mark.asyncio
async def test_cross_project_chapter_reference_rejected(client):
    p1=(await client.post("/api/v1/projects",json={"name":"A"})).json()
    p2=(await client.post("/api/v1/projects",json={"name":"B"})).json()
    ch=(await client.post(f"/api/v1/projects/{p1['id']}/chapters",json={"title":"A1","order_index":1})).json()
    r=await client.post(f"/api/v1/projects/{p2['id']}/chapters/{ch['id']}/scenes",json={"order_index":1})
    assert r.status_code==404
