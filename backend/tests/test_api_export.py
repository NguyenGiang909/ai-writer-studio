import json
import pytest

@pytest.mark.asyncio
async def test_export_json_full_dump(client, proj):
    pid = proj["project"]["id"]
    await client.post(f"/api/v1/projects/{pid}/characters", json={"name": "Minh"})
    await client.post(f"/api/v1/projects/{pid}/threads", json={"title": "Hố A"})
    await client.post(f"/api/v1/projects/{pid}/summaries",
                      json={"scope_type": "scene", "scope_id": proj["scene"]["id"], "summary": "s"})
    r = await client.get(f"/api/v1/projects/{pid}/export")
    assert r.status_code == 200
    assert "attachment" in r.headers["content-disposition"]
    data = r.json()
    assert data["format"] == "ai-writer-studio-export"
    assert data["project"]["id"] == pid
    assert len(data["scenes"]) == 1 and len(data["chapters"]) == 1
    assert len(data["characters"]) == 1 and len(data["threads"]) == 1
    assert len(data["story_summaries"]) == 1
    assert "provider_credentials" not in data
    assert data["counts"]["scenes"] == 1

@pytest.mark.asyncio
async def test_export_markdown_manuscript(client, proj):
    pid = proj["project"]["id"]
    r = await client.get(f"/api/v1/projects/{pid}/export?format=markdown")
    assert r.status_code == 200
    assert "text/markdown" in r.headers["content-type"]
    body = r.text
    assert "# T" in body
    assert "Chương 1" in body and "Some prose." in body

@pytest.mark.asyncio
async def test_export_scoped_and_404(client, proj):
    other = (await client.post("/api/v1/projects", json={"name": "B"})).json()
    await client.post(f"/api/v1/projects/{other['id']}/characters", json={"name": "Kẻ Lạ"})
    r = await client.get(f"/api/v1/projects/{proj['project']['id']}/export")
    assert r.json()["counts"]["characters"] == 0
    assert (await client.get("/api/v1/projects/nonexistent/export")).status_code == 404
