import io, json
import pytest

async def _export(client, pid):
    r = await client.get(f"/api/v1/projects/{pid}/export")
    assert r.status_code == 200
    return r.json()

@pytest.mark.asyncio
async def test_import_roundtrip_remaps_ids(client, proj):
    pid, ch, sc = proj["project"]["id"], proj["chapter"]["id"], proj["scene"]["id"]
    c = (await client.post(f"/api/v1/projects/{pid}/characters", json={"name": "Khánh"})).json()
    await client.post(f"/api/v1/projects/{pid}/aliases", json={"character_id": c["id"], "alias": "Ba Khánh"})
    data = await _export(client, pid)
    files = {"file": ("export.json", io.BytesIO(json.dumps(data).encode()), "application/json")}
    r = await client.post("/api/v1/projects/import", files=files)
    assert r.status_code == 200
    new_pid = r.json()["project"]["id"]
    assert new_pid != pid
    # số lượng row khớp
    assert r.json()["counts"]["scenes"] == data["counts"]["scenes"]
    assert r.json()["counts"]["aliases"] == 1
    # character + alias sang project mới, FK trỏ id MỚI chứ không phải id cũ
    chars = (await client.get(f"/api/v1/projects/{new_pid}/characters")).json()
    new_char = chars[0]
    assert new_char["id"] != c["id"] and new_char["name"] == "Khánh"
    aliases = (await client.get(f"/api/v1/projects/{new_pid}/aliases")).json()
    assert aliases[0]["character_id"] == new_char["id"]
    # scene mới độc lập
    tree = (await client.get(f"/api/v1/projects/{new_pid}/manuscript")).json()
    new_scene = tree["chapters"][0]["scenes"][0]
    assert new_scene["id"] != sc and new_scene["prose"] == "Some prose."

@pytest.mark.asyncio
async def test_import_twice_no_collision(client, proj):
    pid = proj["project"]["id"]
    data = await _export(client, pid)
    blob = io.BytesIO(json.dumps(data).encode())
    p1 = (await client.post("/api/v1/projects/import", files={"file": ("a.json", blob, "application/json")})).json()["project"]["id"]
    blob.seek(0)
    p2 = (await client.post("/api/v1/projects/import", files={"file": ("b.json", blob, "application/json")})).json()["project"]["id"]
    assert p1 != p2
    # cả 2 đều query được, không đụng unique/id
    assert (await client.get(f"/api/v1/projects/{p1}/manuscript")).status_code == 200
    assert (await client.get(f"/api/v1/projects/{p2}/manuscript")).status_code == 200

@pytest.mark.asyncio
async def test_import_rejects_garbage(client):
    bad = {"file": ("x.json", io.BytesIO(b"not json"), "application/json")}
    assert (await client.post("/api/v1/projects/import", files=bad)).status_code == 400
    wrong = {"file": ("x.json", io.BytesIO(json.dumps({"format": "other"}).encode()), "application/json")}
    assert (await client.post("/api/v1/projects/import", files=wrong)).status_code == 400
