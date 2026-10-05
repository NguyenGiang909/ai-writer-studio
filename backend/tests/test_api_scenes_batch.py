import pytest

@pytest.mark.asyncio
async def test_batch_creates_scenes_with_sequential_order(client, proj):
    pid, ch = proj["project"]["id"], proj["chapter"]["id"]
    # fixture đã có 1 scene order_index=1 → batch phải nối tiếp từ 2
    r = await client.post(f"/api/v1/projects/{pid}/chapters/{ch}/scenes/batch", json={
        "scenes": [
            {"title": "S2", "skeleton": "• beat a"},
            {"title": "S3", "skeleton": "• beat b"},
        ],
    })
    assert r.status_code == 200
    scenes = r.json()
    assert [s["order_index"] for s in scenes] == [2, 3]
    assert scenes[0]["skeleton"] == "• beat a"
    tree = (await client.get(f"/api/v1/projects/{pid}/manuscript")).json()
    got = tree["chapters"][0]["scenes"]
    assert len(got) == 3 and [s["title"] for s in got[1:]] == ["S2", "S3"]

@pytest.mark.asyncio
async def test_batch_rejects_empty_list(client, proj):
    pid, ch = proj["project"]["id"], proj["chapter"]["id"]
    r = await client.post(f"/api/v1/projects/{pid}/chapters/{ch}/scenes/batch", json={"scenes": []})
    assert r.status_code == 422
    tree = (await client.get(f"/api/v1/projects/{pid}/manuscript")).json()
    assert len(tree["chapters"][0]["scenes"]) == 1

@pytest.mark.asyncio
async def test_batch_cross_project_chapter_rejected(client, proj):
    pid, ch = proj["project"]["id"], proj["chapter"]["id"]
    other = (await client.post("/api/v1/projects", json={"name": "B"})).json()
    r = await client.post(
        f"/api/v1/projects/{other['id']}/chapters/{ch}/scenes/batch",
        json={"scenes": [{"title": "X"}]},
    )
    assert r.status_code == 404
    tree = (await client.get(f"/api/v1/projects/{pid}/manuscript")).json()
    assert len(tree["chapters"][0]["scenes"]) == 1

@pytest.mark.asyncio
async def test_batch_atomic_no_partial_on_invalid_item(client, proj):
    # item sai kiểu → pydantic 422 → không scene nào được tạo (all-or-nothing)
    pid, ch = proj["project"]["id"], proj["chapter"]["id"]
    r = await client.post(f"/api/v1/projects/{pid}/chapters/{ch}/scenes/batch", json={
        "scenes": [{"title": "OK"}, {"title": 123, "skeleton": {"bad": "type"}}],
    })
    assert r.status_code == 422
    tree = (await client.get(f"/api/v1/projects/{pid}/manuscript")).json()
    assert len(tree["chapters"][0]["scenes"]) == 1
