import pytest

@pytest.mark.asyncio
async def test_search_scene_by_prose_content(client, proj):
    pid, sc = proj["project"]["id"], proj["scene"]["id"]
    await client.patch(f"/api/v1/projects/{pid}/scenes/{sc}", json={"prose": "Hắn rút thanh tàn kiếm ra khỏi bùn."})
    r = await client.get(f"/api/v1/projects/{pid}/search", params={"q": "tàn kiếm"})
    assert r.status_code == 200
    res = r.json()["results"]
    hit = [x for x in res if x["type"] == "scene" and x["id"] == sc]
    assert hit and "tàn kiếm" in hit[0]["snippet"]

@pytest.mark.asyncio
async def test_search_character_and_alias(client, proj):
    pid = proj["project"]["id"]
    c = (await client.post(f"/api/v1/projects/{pid}/characters", json={
        "name": "Khánh", "summary": "thuyền chài sông Đáy"})).json()
    await client.post(f"/api/v1/projects/{pid}/aliases", json={"character_id": c["id"], "alias": "Ba Khánh"})
    r1 = (await client.get(f"/api/v1/projects/{pid}/search", params={"q": "Khánh"})).json()
    assert any(x["type"] == "character" and x["label"] == "Khánh" for x in r1["results"])
    # tìm theo bí danh → vẫn trả về character gốc, 1 lần
    r2 = (await client.get(f"/api/v1/projects/{pid}/search", params={"q": "Ba Khánh"})).json()
    hits = [x for x in r2["results"] if x["type"] == "character" and x["id"] == c["id"]]
    assert len(hits) == 1 and "bí danh" in hits[0]["context"]

@pytest.mark.asyncio
async def test_search_canon_thread_and_scoping(client, proj):
    pid = proj["project"]["id"]
    await client.post(f"/api/v1/projects/{pid}/canon-facts", json={
        "subject_type": "item", "predicate": "ORIGIN", "value_text": "kiếm rỉ từ đáy sông"})
    await client.post(f"/api/v1/projects/{pid}/threads", json={
        "title": "Bí ẩn tàn kiếm", "description": "ai đã ném kiếm xuống sông"})
    r = (await client.get(f"/api/v1/projects/{pid}/search", params={"q": "kiếm"})).json()
    types = {x["type"] for x in r["results"]}
    assert "canon" in types and "thread" in types
    # project khác không lọt kết quả
    other = (await client.post("/api/v1/projects", json={"name": "B"})).json()
    r2 = (await client.get(f"/api/v1/projects/{other['id']}/search", params={"q": "kiếm"})).json()
    assert r2["results"] == []
    assert (await client.get(f"/api/v1/projects/{pid}/search", params={"q": ""})).status_code == 422
