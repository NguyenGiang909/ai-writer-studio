import pytest

@ pytest.mark.asyncio
async def test_patch_prose_snapshots_previous_version(client, proj):
    pid, sc = proj["project"]["id"], proj["scene"]["id"]
    # prose gốc "Some prose." → sửa → version phải chứa bản cũ
    r = await client.patch(f"/api/v1/projects/{pid}/scenes/{sc}", json={"prose": "New prose v2."})
    assert r.status_code == 200 and r.json()["prose"] == "New prose v2."
    vs = (await client.get(f"/api/v1/projects/{pid}/scenes/{sc}/versions")).json()
    assert len(vs) == 1
    assert vs[0]["excerpt"].startswith("Some prose")
    assert vs[0]["chars"] == len("Some prose.")

@ pytest.mark.asyncio
async def test_version_full_prose_and_restore(client, proj):
    pid, sc = proj["project"]["id"], proj["scene"]["id"]
    await client.patch(f"/api/v1/projects/{pid}/scenes/{sc}", json={"prose": "Second draft."})
    vs = (await client.get(f"/api/v1/projects/{pid}/scenes/{sc}/versions")).json()
    full = (await client.get(f"/api/v1/projects/{pid}/scenes/{sc}/versions/{vs[0]['id']}")).json()
    assert full["prose"] == "Some prose."
    # restore → prose quay lại bản cũ; trạng thái "Second draft" được snapshot trước
    r = await client.post(f"/api/v1/projects/{pid}/scenes/{sc}/versions/{vs[0]['id']}/restore")
    assert r.status_code == 200 and r.json()["prose"] == "Some prose."
    vs2 = (await client.get(f"/api/v1/projects/{pid}/scenes/{sc}/versions")).json()
    assert len(vs2) == 2
    assert any(v["excerpt"].startswith("Second draft") for v in vs2)

@ pytest.mark.asyncio
async def test_rapid_saves_coalesce_to_one_version(client, proj):
    pid, sc = proj["project"]["id"], proj["scene"]["id"]
    # 3 save liên tiếp trong <90s → chỉ 1 checkpoint (bản trước burst)
    for i in range(3):
        await client.patch(f"/api/v1/projects/{pid}/scenes/{sc}", json={"prose": f"draft {i}"})
    vs = (await client.get(f"/api/v1/projects/{pid}/scenes/{sc}/versions")).json()
    assert len(vs) == 1 and vs[0]["excerpt"].startswith("Some prose")

@ pytest.mark.asyncio
async def test_patch_without_prose_creates_no_version(client, proj):
    pid, sc = proj["project"]["id"], proj["scene"]["id"]
    await client.patch(f"/api/v1/projects/{pid}/scenes/{sc}", json={"title": "Renamed"})
    vs = (await client.get(f"/api/v1/projects/{pid}/scenes/{sc}/versions")).json()
    assert vs == []

@ pytest.mark.asyncio
async def test_versions_scoped_and_404s(client, proj):
    pid, sc = proj["project"]["id"], proj["scene"]["id"]
    other = (await client.post("/api/v1/projects", json={"name": "B"})).json()
    assert (await client.get(f"/api/v1/projects/{other['id']}/scenes/{sc}/versions")).status_code == 404
    assert (await client.post(f"/api/v1/projects/{pid}/scenes/{sc}/versions/nonexist/restore")).status_code == 404
