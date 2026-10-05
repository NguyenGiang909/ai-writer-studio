import pytest

@pytest.mark.asyncio
async def test_generate_scene_summary_upserts(client, proj):
    pid = proj["project"]["id"]; sid = proj["scene"]["id"]
    r = await client.post(f"/api/v1/projects/{pid}/summaries/generate",
                          json={"scope_type": "scene", "scope_id": sid})
    assert r.status_code == 200
    s1 = r.json()
    assert s1["scope_type"] == "scene" and s1["stale"] is False and s1["summary"]
    # generate lại → upsert, không tạo hàng mới
    r2 = await client.post(f"/api/v1/projects/{pid}/summaries/generate",
                           json={"scope_type": "scene", "scope_id": sid})
    assert r2.status_code == 200 and r2.json()["id"] == s1["id"]
    rows = (await client.get(f"/api/v1/projects/{pid}/summaries?scope_type=scene")).json()
    assert len(rows) == 1
    # turn được ghi lại
    turns = (await client.get(f"/api/v1/projects/{pid}/ai/turns")).json()
    assert turns["total"] >= 2

@pytest.mark.asyncio
async def test_generate_empty_scene_400(client, proj):
    pid = proj["project"]["id"]; ch = proj["chapter"]["id"]
    empty = (await client.post(f"/api/v1/projects/{pid}/chapters/{ch}/scenes",
                               json={"order_index": 9})).json()
    r = await client.post(f"/api/v1/projects/{pid}/summaries/generate",
                          json={"scope_type": "scene", "scope_id": empty["id"]})
    assert r.status_code == 400

@pytest.mark.asyncio
async def test_generate_chapter_uses_child_summaries(client, proj):
    pid = proj["project"]["id"]; ch = proj["chapter"]["id"]; sid = proj["scene"]["id"]
    await client.post(f"/api/v1/projects/{pid}/summaries",
                      json={"scope_type": "scene", "scope_id": sid, "summary": "Cảnh mở."})
    r = await client.post(f"/api/v1/projects/{pid}/summaries/generate",
                          json={"scope_type": "chapter", "scope_id": ch})
    assert r.status_code == 200 and r.json()["summary"]

@pytest.mark.asyncio
async def test_summaries_coverage(client, proj):
    pid = proj["project"]["id"]; ch = proj["chapter"]["id"]; sid = proj["scene"]["id"]
    cov = (await client.get(f"/api/v1/projects/{pid}/summaries/coverage")).json()
    # fixture: 1 chapter có 1 scene có prose; story luôn có nội dung
    assert cov["levels"]["scene"]["missing"] == 1
    assert cov["levels"]["chapter"]["missing"] == 1
    assert cov["levels"]["story"]["missing"] == 1
    assert cov["pending_count"] == 3
    # thứ tự pending: scene → chapter → story
    assert [p["scope_type"] for p in cov["pending"]] == ["scene", "chapter", "story"]
    # sau khi generate scene → pending giảm
    await client.post(f"/api/v1/projects/{pid}/summaries/generate",
                      json={"scope_type": "scene", "scope_id": sid})
    cov2 = (await client.get(f"/api/v1/projects/{pid}/summaries/coverage")).json()
    assert cov2["levels"]["scene"]["fresh"] == 1 and cov2["pending_count"] == 2
    # đánh stale → quay lại pending với reason=stale
    s = (await client.get(f"/api/v1/projects/{pid}/summaries?scope_type=scene")).json()[0]
    await client.patch(f"/api/v1/projects/{pid}/summaries/{s['id']}", json={"stale": True})
    cov3 = (await client.get(f"/api/v1/projects/{pid}/summaries/coverage")).json()
    assert cov3["levels"]["scene"]["stale"] == 1
    assert any(p["reason"] == "stale" and p["scope_id"] == sid for p in cov3["pending"])

@pytest.mark.asyncio
async def test_generate_scope_validation(client, proj):
    pid = proj["project"]["id"]
    r = await client.post(f"/api/v1/projects/{pid}/summaries/generate",
                          json={"scope_type": "bogus", "scope_id": "x"})
    assert r.status_code == 400
    other = (await client.post("/api/v1/projects", json={"name": "B"})).json()
    ch2 = (await client.post(f"/api/v1/projects/{other['id']}/chapters",
                             json={"title": "C", "order_index": 1})).json()
    r2 = await client.post(f"/api/v1/projects/{pid}/summaries/generate",
                           json={"scope_type": "chapter", "scope_id": ch2["id"]})
    assert r2.status_code == 400
