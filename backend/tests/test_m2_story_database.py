
import pytest
@pytest.mark.asyncio
async def test_story_database_and_project_boundaries(client):
    p1=(await client.post("/api/v1/projects",json={"name":"A"})).json()
    p2=(await client.post("/api/v1/projects",json={"name":"B"})).json()
    c1=(await client.post(f"/api/v1/projects/{p1['id']}/characters",json={"name":"Lâm Uyên","role":"protagonist"})).json()
    c2=(await client.post(f"/api/v1/projects/{p1['id']}/characters",json={"name":"Tô Thanh"})).json()
    r=await client.post(f"/api/v1/projects/{p1['id']}/relationships",json={"source_character_id":c1["id"],"target_character_id":c2["id"],"relationship_type":"ally"})
    assert r.status_code==200
    bad=await client.post(f"/api/v1/projects/{p2['id']}/aliases",json={"character_id":c1["id"],"alias":"Sai project"})
    assert bad.status_code==400

@pytest.mark.asyncio
async def test_location_hierarchy_and_style_scope(client):
    p=(await client.post("/api/v1/projects",json={"name":"A"})).json()
    parent=(await client.post(f"/api/v1/projects/{p['id']}/locations",json={"name":"Đại Tần"})).json()
    child=await client.post(f"/api/v1/projects/{p['id']}/locations",json={"name":"Hắc Thủy","parent_location_id":parent["id"]})
    assert child.status_code==200
    style=await client.post(f"/api/v1/projects/{p['id']}/style-profiles",json={"name":"Default","scope_type":"global","instructions":"Tiết chế."})
    assert style.status_code==200
    sample=await client.post(f"/api/v1/projects/{p['id']}/style-samples",json={"style_profile_id":style.json()["id"],"sample_type":"dialogue","text":"Một đoạn mẫu."})
    assert sample.status_code==200
