
import pytest


@pytest.mark.asyncio
async def test_signals_cast_dormancy(client, proj):
    pid = proj["project"]["id"]
    ch = proj["chapter"]["id"]
    c = (await client.post(f"/api/v1/projects/{pid}/characters",
                           json={"name": "Minh Trần"})).json()
    # scene 1 mentions the character; create many later scenes without them
    await client.patch(f"/api/v1/projects/{pid}/scenes/{proj['scene']['id']}",
                       json={"prose": "Minh Trần bước vào căn phòng tối.",
                             "narrative_order": 1})
    for i in range(2, 15):
        await client.post(f"/api/v1/projects/{pid}/chapters/{ch}/scenes",
                          json={"title": f"S{i}", "order_index": i,
                                "prose": "Cảnh không có ai cả.",
                                "narrative_order": i})
    data = (await client.get(f"/api/v1/projects/{pid}/signals")).json()
    row = next(r for r in data["cast_dormancy"] if r["character_id"] == c["id"])
    assert row["flag"] == "dormant" and row["gap"] >= 10


@pytest.mark.asyncio
async def test_signals_gone_character_not_dormant(client, proj):
    pid = proj["project"]["id"]
    c = (await client.post(f"/api/v1/projects/{pid}/characters",
                           json={"name": "An Vũ"})).json()
    await client.patch(f"/api/v1/projects/{pid}/scenes/{proj['scene']['id']}",
                       json={"prose": "An Vũ xuất hiện rồi chết.",
                             "narrative_order": 1})
    await client.post(f"/api/v1/projects/{pid}/story-states", json={
        "entity_type": "character", "entity_id": c["id"], "key": "lifecycle",
        "value_text": "DEAD", "story_time": 1})
    data = (await client.get(f"/api/v1/projects/{pid}/signals")).json()
    row = next(r for r in data["cast_dormancy"] if r["character_id"] == c["id"])
    assert row["flag"] == "gone"


@pytest.mark.asyncio
async def test_signals_thread_health_and_repetition(client, proj):
    pid = proj["project"]["id"]
    ch = proj["chapter"]["id"]
    th = (await client.post(f"/api/v1/projects/{pid}/threads",
                            json={"title": "Hố mở"})).json()
    # thread with a beat at order 0, then 16 scenes past it
    await client.post(f"/api/v1/projects/{pid}/threads/{th['id']}/beats",
                      json={"beat_type": "setup", "narrative_order": 0})
    repeated = "Hắn siết chặt bàn tay cho đến khi các khớp ngón trắng bệch."
    for i in range(2, 20):
        prose = repeated if i % 5 == 0 else "Nội dung khác nhau hoàn toàn."
        await client.post(f"/api/v1/projects/{pid}/chapters/{ch}/scenes",
                          json={"title": f"S{i}", "order_index": i,
                                "prose": prose, "narrative_order": i})
    data = (await client.get(f"/api/v1/projects/{pid}/signals")).json()
    h = next(r for r in data["thread_health"] if r["thread_id"] == th["id"])
    assert h["flag"] == "stale"
    rep = next((r for r in data["repetition"] if "siết chặt" in r["text"]), None)
    assert rep and rep["count"] >= 3 and len(rep["scenes"]) >= 3
