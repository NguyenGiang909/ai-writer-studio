import pytest

@pytest.mark.asyncio
async def test_character_assist_finds_excerpts_and_logs(client, proj):
    pid = proj["project"]["id"]; sid = proj["scene"]["id"]
    await client.patch(f"/api/v1/projects/{pid}/scenes/{sid}", json={
        "prose": "Minh Trần bước xuống bến. Minh Trần nhìn dòng sông chảy."})
    r = await client.post(f"/api/v1/projects/{pid}/characters/assist",
                          json={"name": "Minh Trần"})
    assert r.status_code == 200
    body = r.json()
    assert body["excerpts_used"] == 1
    assert body["draft"]["name"] == "Minh Trần"
    assert body["draft"]["status"] == "active"
    assert body["existing_id"] is None and body["provider"] == "fake"
    turns = (await client.get(f"/api/v1/projects/{pid}/ai/turns")).json()
    assert any(t["task"] == "character_profile" for t in turns["turns"])

@pytest.mark.asyncio
async def test_character_assist_existing_profile_flagged(client, proj):
    pid = proj["project"]["id"]
    c = (await client.post(f"/api/v1/projects/{pid}/characters",
                           json={"name": "Bà Lệ"})).json()
    r = await client.post(f"/api/v1/projects/{pid}/characters/assist",
                          json={"name": "Bà Lệ"})
    assert r.status_code == 200 and r.json()["existing_id"] == c["id"]

@pytest.mark.asyncio
async def test_character_assist_blank_name_400(client, proj):
    pid = proj["project"]["id"]
    r = await client.post(f"/api/v1/projects/{pid}/characters/assist", json={"name": "   "})
    assert r.status_code == 400

@pytest.mark.asyncio
async def test_character_assist_no_prose_still_returns_draft(client, proj):
    pid = proj["project"]["id"]
    r = await client.post(f"/api/v1/projects/{pid}/characters/assist",
                          json={"name": "Người Chưa Xuất Hiện"})
    assert r.status_code == 200
    assert r.json()["excerpts_used"] == 0
    assert r.json()["draft"]["name"] == "Người Chưa Xuất Hiện"
