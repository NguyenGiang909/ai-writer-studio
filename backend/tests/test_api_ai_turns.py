import pytest

async def _mk_turns(client, pid, n, sid=None):
    for i in range(n):
        r = await client.post(f"/api/v1/projects/{pid}/ai/complete",
                              json={"task": "writing", "prompt": f"prompt {i}", "scene_id": sid})
        assert r.status_code == 200

@pytest.mark.asyncio
async def test_list_ai_turns(client, proj):
    pid = proj["project"]["id"]; sid = proj["scene"]["id"]
    await _mk_turns(client, pid, 3, sid)
    r = await client.get(f"/api/v1/projects/{pid}/ai/turns")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3 and len(body["turns"]) == 3
    t = body["turns"][0]
    assert t["task"] == "writing" and t["provider"] == "fake"
    assert t["prompt_excerpt"] and t["reply_text"] and t["created_at"]

@pytest.mark.asyncio
async def test_list_ai_turns_scoped_by_project(client, proj):
    pid = proj["project"]["id"]
    other = (await client.post("/api/v1/projects", json={"name": "B"})).json()
    await _mk_turns(client, pid, 2)
    await _mk_turns(client, other["id"], 1)
    r = (await client.get(f"/api/v1/projects/{pid}/ai/turns")).json()
    assert r["total"] == 2

@pytest.mark.asyncio
async def test_delete_ai_turn(client, proj):
    pid = proj["project"]["id"]
    await _mk_turns(client, pid, 2)
    turns = (await client.get(f"/api/v1/projects/{pid}/ai/turns")).json()["turns"]
    r = await client.delete(f"/api/v1/projects/{pid}/ai/turns/{turns[0]['id']}")
    assert r.status_code == 200
    assert (await client.get(f"/api/v1/projects/{pid}/ai/turns")).json()["total"] == 1

@pytest.mark.asyncio
async def test_delete_ai_turn_cross_project_rejected(client, proj):
    pid = proj["project"]["id"]
    other = (await client.post("/api/v1/projects", json={"name": "B"})).json()
    await _mk_turns(client, pid, 1)
    tid = (await client.get(f"/api/v1/projects/{pid}/ai/turns")).json()["turns"][0]["id"]
    r = await client.delete(f"/api/v1/projects/{other['id']}/ai/turns/{tid}")
    assert r.status_code == 404
    assert (await client.get(f"/api/v1/projects/{pid}/ai/turns")).json()["total"] == 1

@pytest.mark.asyncio
async def test_prune_ai_turns(client, proj):
    pid = proj["project"]["id"]
    await _mk_turns(client, pid, 5)
    r = await client.post(f"/api/v1/projects/{pid}/ai/turns/prune", json={"keep": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["deleted"] == 3 and body["kept"] == 2
    assert (await client.get(f"/api/v1/projects/{pid}/ai/turns")).json()["total"] == 2
    r2 = await client.post(f"/api/v1/projects/{pid}/ai/turns/prune", json={"keep": 0})
    assert r2.json()["deleted"] == 2
    assert (await client.get(f"/api/v1/projects/{pid}/ai/turns")).json()["total"] == 0
