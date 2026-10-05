
import pytest

@pytest.mark.asyncio
async def test_context_preview_budget_and_protected(client,proj):
    pid=proj["project"]["id"]
    r=(await client.post(f"/api/v1/projects/{pid}/context/preview",json={
        "budget":10,
        "items":[
            {"bucket":"author_brief","text":"must keep","priority":0,"source":"author"},
            {"bucket":"lore","text":"x"*80,"priority":99,"source":"db"}]})).json()
    assert "must keep" in r["text"]
    assert any(o["reason"]=="token_budget" for o in r["manifest"]["omitted"])

@pytest.mark.asyncio
async def test_writer_helpers(client):
    r=(await client.post("/api/v1/writer/parse-brief",json={
        "text":"Lan enters the ruin\nkhông giết ai\ntìm thấy bản đồ","target_words":1500})).json()
    assert len(r["beats"])==2 and len(r["constraints"])==1 and r["target_words"]==1500
    b=(await client.post("/api/v1/writer/word-budget",json={"target":1000,"scene_count":3})).json()
    assert sum(b["allocation"])==1000
    d=(await client.post("/api/v1/writer/line-diff",json={"original":"a\nb","replacement":"a\nc"})).json()
    assert any(x.startswith("-") for x in d["diff"])

@pytest.mark.asyncio
async def test_ai_complete_fake_provider(client,proj):
    pid=proj["project"]["id"]
    r=await client.post(f"/api/v1/projects/{pid}/ai/complete",json={"task":"writing","prompt":"hi"})
    assert r.status_code==200
    body=r.json()
    assert body["provider"]=="fake" and body["reply"] and "usage" in body

@pytest.mark.asyncio
async def test_ai_skeleton_task(client,proj):
    pid=proj["project"]["id"]; sid=proj["scene"]["id"]
    r=await client.post(f"/api/v1/projects/{pid}/ai/complete",
                        json={"task":"skeleton","prompt":"","scene_id":sid})
    assert r.status_code==200
    body=r.json()
    assert body["provider"]=="fake" and body["reply"]

@pytest.mark.asyncio
async def test_ai_turn_persisted_and_session_memory(client,proj):
    pid=proj["project"]["id"]; sid=proj["scene"]["id"]
    r1=await client.post(f"/api/v1/projects/{pid}/ai/complete",
                         json={"task":"writing","prompt":"draft one","scene_id":sid})
    assert r1.status_code==200
    # second call on same scene must see the first turn in its manifest
    r2=await client.post(f"/api/v1/projects/{pid}/ai/context-manifest",
                         json={"task":"writing","scene_id":sid})
    assert r2.status_code==200
    manifest=" ".join(r2.json()["manifest"])
    assert "session-turns" in manifest

@pytest.mark.asyncio
async def test_summary_injected_in_context(client,proj):
    pid=proj["project"]["id"]; chid=proj["chapter"]["id"]; sid=proj["scene"]["id"]
    r=await client.post(f"/api/v1/projects/{pid}/summaries",
                        json={"scope_type":"chapter","scope_id":chid,
                              "summary":"Chương mở: Khánh bị mất kiếm.","narrative_end":1})
    assert r.status_code==200
    m=await client.post(f"/api/v1/projects/{pid}/ai/context-manifest",
                        json={"task":"writing","scene_id":sid})
    assert m.status_code==200
    assert "summaries" in " ".join(m.json()["manifest"])

@pytest.mark.asyncio
async def test_chapter_outline_task(client,proj):
    pid=proj["project"]["id"]; chid=proj["chapter"]["id"]
    m=await client.post(f"/api/v1/projects/{pid}/ai/context-manifest",
                        json={"task":"chapter_outline","chapter_id":chid})
    assert m.status_code==200
    assert "chapter-info" in " ".join(m.json()["manifest"])
    r=await client.post(f"/api/v1/projects/{pid}/ai/complete",
                        json={"task":"chapter_outline","prompt":"","chapter_id":chid})
    assert r.status_code==200
    assert r.json()["provider"]=="fake" and r.json()["reply"]

@pytest.mark.asyncio
async def test_scene_prose_edit_marks_summary_stale(client,proj):
    pid=proj["project"]["id"]; sid=proj["scene"]["id"]
    s=await client.post(f"/api/v1/projects/{pid}/summaries",
                        json={"scope_type":"scene","scope_id":sid,
                              "summary":"Cảnh mở đầu.","narrative_end":1})
    assert s.status_code==200
    p=await client.patch(f"/api/v1/projects/{pid}/scenes/{sid}",json={"prose":"Văn mới vừa viết."})
    assert p.status_code==200
    rows=await client.get(f"/api/v1/projects/{pid}/summaries?scope_type=scene")
    row=[r for r in rows.json() if r["scope_id"]==sid][0]
    assert row["stale"] is True

@pytest.mark.asyncio
async def test_ai_complete_503_when_fake_disabled(client,proj,monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings,"allow_fake_provider",False)
    pid=proj["project"]["id"]
    r=await client.post(f"/api/v1/projects/{pid}/ai/complete",json={"task":"writing","prompt":"hi"})
    assert r.status_code==503

@pytest.mark.asyncio
async def test_scene_author_brief_roundtrip(client,proj):
    pid=proj["project"]["id"]; sid=proj["scene"]["id"]
    brief={"goal":"Minh finds torn file","target_words":1500,"freedom":"low",
           "must_avoid":"no reveal of An","ending_beat":"he pockets the page"}
    r=await client.patch(f"/api/v1/projects/{pid}/scenes/{sid}",json={"brief":brief})
    assert r.status_code==200 and r.json()["brief"]==brief
    tree=(await client.get(f"/api/v1/projects/{pid}/manuscript")).json()
    scene=[s for c in tree["chapters"] for s in c["scenes"] if s["id"]==sid][0]
    assert scene["brief"]==brief

@pytest.mark.asyncio
async def test_continuity_knowledge_leak(client,proj):
    pid=proj["project"]["id"]; sid=proj["scene"]["id"]
    c=(await client.post(f"/api/v1/projects/{pid}/characters",json={"name":"Minh Trần"})).json()
    await client.patch(f"/api/v1/projects/{pid}/scenes/{sid}",json={
        "prose":"Minh Trần bước vào căn phòng và nhắc tới bí mật phòng."})
    f=(await client.post(f"/api/v1/projects/{pid}/canon-facts",json={
        "subject_type":"story","predicate":"secret","value_text":"bí mật phòng"})).json()
    await client.post(f"/api/v1/projects/{pid}/knowledge-states",json={
        "knower_type":"character","knower_id":c["id"],"fact_id":f["id"],
        "state":"KNOWS","acquired_narrative_order":50})
    r=(await client.get(f"/api/v1/projects/{pid}/continuity/check")).json()
    assert r["auto_mutations"]==0
    assert any(i["code"]=="KNOWLEDGE_LEAK" and i["evidence"]["scene_id"]==sid for i in r["issues"])
    # same setup but knower absent from prose → no leak
    c2=(await client.post(f"/api/v1/projects/{pid}/characters",json={"name":"Vắng Mặt"})).json()
    await client.post(f"/api/v1/projects/{pid}/knowledge-states",json={
        "knower_type":"character","knower_id":c2["id"],"fact_id":f["id"],
        "state":"KNOWS","acquired_narrative_order":50})
    r2=(await client.get(f"/api/v1/projects/{pid}/continuity/check")).json()
    assert not any(i["code"]=="KNOWLEDGE_LEAK" and i["evidence"].get("knower_id")==c2["id"] for i in r2["issues"])

@pytest.mark.asyncio
async def test_scene_temporal_roundtrip(client,proj):
    pid=proj["project"]["id"]; sid=proj["scene"]["id"]
    r=await client.patch(f"/api/v1/projects/{pid}/scenes/{sid}",json={"story_time":42,"narrative_order":7})
    assert r.status_code==200
    assert r.json()["story_time"]==42 and r.json()["narrative_order"]==7

@pytest.mark.asyncio
async def test_story_state_as_of(client,proj):
    pid=proj["project"]["id"]
    await client.post(f"/api/v1/projects/{pid}/story-states",json={
        "entity_type":"character","entity_id":"c1","key":"lifecycle","value_text":"ALIVE","story_time":10})
    await client.post(f"/api/v1/projects/{pid}/story-states",json={
        "entity_type":"character","entity_id":"c1","key":"lifecycle","value_text":"DEAD","story_time":50})
    r=(await client.get(f"/api/v1/projects/{pid}/story-states/as-of",
                        params={"entity_id":"c1","key":"lifecycle","story_time":30})).json()
    assert r["value_text"]=="ALIVE"
    r=(await client.get(f"/api/v1/projects/{pid}/story-states/as-of",
                        params={"entity_id":"c1","key":"lifecycle","story_time":60})).json()
    assert r["value_text"]=="DEAD"

@pytest.mark.asyncio
async def test_continuity_restricted_appearance(client,proj):
    pid=proj["project"]["id"]; sid=proj["scene"]["id"]
    c=(await client.post(f"/api/v1/projects/{pid}/characters",json={"name":"Minh Trần"})).json()
    await client.post(f"/api/v1/projects/{pid}/story-states",json={
        "entity_type":"character","entity_id":c["id"],"key":"lifecycle","value_text":"DEAD","story_time":10})
    await client.patch(f"/api/v1/projects/{pid}/scenes/{sid}",json={
        "prose":"Minh bước vào căn phòng tối.","story_time":20})
    r=(await client.get(f"/api/v1/projects/{pid}/continuity/check")).json()
    assert any(i["code"]=="RESTRICTED_APPEARANCE" and i["evidence"]["scene_id"]==sid for i in r["issues"])

@pytest.mark.asyncio
async def test_continuity_stale_thread(client,proj):
    pid=proj["project"]["id"]
    await client.post(f"/api/v1/projects/{pid}/threads",json={
        "title":"Hố thử nghiệm","planned_payoff_order":0})
    r=(await client.get(f"/api/v1/projects/{pid}/continuity/check")).json()
    assert any(i["code"] in ("THREAD_OVERDUE","STALE_THREAD") for i in r["issues"])

@pytest.mark.asyncio
async def test_continuity_location_conflict(client,proj):
    pid=proj["project"]["id"]; sid=proj["scene"]["id"]
    loc_a=(await client.post(f"/api/v1/projects/{pid}/locations",json={"name":"Hầm số 4"})).json()
    loc_b=(await client.post(f"/api/v1/projects/{pid}/locations",json={"name":"Khách sạn"})).json()
    c=(await client.post(f"/api/v1/projects/{pid}/characters",json={"name":"Bà Lệ"})).json()
    await client.post(f"/api/v1/projects/{pid}/story-states",json={
        "entity_type":"character","entity_id":c["id"],"key":"location",
        "value_text":"Hầm số 4","story_time":10})
    r=await client.patch(f"/api/v1/projects/{pid}/scenes/{sid}",json={
        "prose":"Bà Lệ mở cửa phòng.","story_time":20,"location_id":loc_b["id"]})
    assert r.status_code==200 and r.json()["location_id"]==loc_b["id"]
    r=(await client.get(f"/api/v1/projects/{pid}/continuity/check")).json()
    assert any(i["code"]=="LOCATION_CONFLICT" and i["evidence"]["scene_id"]==sid for i in r["issues"])

@pytest.mark.asyncio
async def test_continuity_ability_locked(client,proj):
    pid=proj["project"]["id"]; sid=proj["scene"]["id"]
    ab=(await client.post(f"/api/v1/projects/{pid}/abilities",json={"name":"Đọc Ký Ức"})).json()
    await client.post(f"/api/v1/projects/{pid}/story-states",json={
        "entity_type":"ability","entity_id":ab["id"],"key":"status",
        "value_text":"UNLOCKED","story_time":99})
    await client.patch(f"/api/v1/projects/{pid}/scenes/{sid}",json={
        "prose":"Ông dùng Đọc Ký Ức lên trang giấy.","story_time":20,"location_id":None})
    r=(await client.get(f"/api/v1/projects/{pid}/continuity/check")).json()
    assert any(i["code"]=="ABILITY_NOT_UNLOCKED" and i["evidence"]["scene_id"]==sid for i in r["issues"])

@pytest.mark.asyncio
async def test_continuity_item_owner_mismatch(client,proj):
    pid=proj["project"]["id"]; sid=proj["scene"]["id"]
    owner=(await client.post(f"/api/v1/projects/{pid}/characters",json={"name":"Chủ Cũ"})).json()
    other=(await client.post(f"/api/v1/projects/{pid}/characters",json={"name":"Kẻ Lạ"})).json()
    it=(await client.post(f"/api/v1/projects/{pid}/items",json={"name":"Chìa Khoá Hầm"})).json()
    await client.post(f"/api/v1/projects/{pid}/story-states",json={
        "entity_type":"item","entity_id":it["id"],"key":"ownership","value_text":owner["id"]})
    await client.patch(f"/api/v1/projects/{pid}/scenes/{sid}",json={
        "prose":"Kẻ Lạ xoay Chìa Khoá Hầm trong tay.","location_id":None})
    r=(await client.get(f"/api/v1/projects/{pid}/continuity/check")).json()
    assert any(i["code"]=="ITEM_OWNER_MISMATCH" and i["evidence"]["scene_id"]==sid for i in r["issues"])

@pytest.mark.asyncio
async def test_continuity_relationship_ended(client,proj):
    pid=proj["project"]["id"]; sid=proj["scene"]["id"]
    a=(await client.post(f"/api/v1/projects/{pid}/characters",json={"name":"Anh Hai"})).json()
    b=(await client.post(f"/api/v1/projects/{pid}/characters",json={"name":"Em Ba"})).json()
    rel=(await client.post(f"/api/v1/projects/{pid}/relationships",json={
        "source_character_id":a["id"],"target_character_id":b["id"],
        "relationship_type":"siblings"})).json()
    await client.post(f"/api/v1/projects/{pid}/story-states",json={
        "entity_type":"relationship","entity_id":rel["id"],"key":"status","value_text":"HOSTILE"})
    await client.patch(f"/api/v1/projects/{pid}/scenes/{sid}",json={
        "prose":"Anh Hai ngồi đối diện Em Ba.","location_id":None})
    r=(await client.get(f"/api/v1/projects/{pid}/continuity/check")).json()
    assert any(i["code"]=="RELATIONSHIP_CONFLICT" and i["evidence"]["scene_id"]==sid for i in r["issues"])

@pytest.mark.asyncio
async def test_extract_materializes_story_state(client,proj):
    pid=proj["project"]["id"]; sid=proj["scene"]["id"]
    c=(await client.post(f"/api/v1/projects/{pid}/characters",json={"name":"Minh Trần"})).json()
    await client.patch(f"/api/v1/projects/{pid}/scenes/{sid}",json={"story_time":20})
    r=await client.post(f"/api/v1/projects/{pid}/suggestions",json={
        "scene_id":sid,"change_type":"story_state",
        "payload":{"entity_name":"Minh Trần","entity_kind":"character","key":"lifecycle","value":"DEAD"}})
    sug=r.json()
    r2=await client.post(f"/api/v1/projects/{pid}/suggestions/{sug['id']}/approve")
    d=r2.json(); assert r2.status_code==200 and "applied_id" in d
    states=(await client.get(f"/api/v1/projects/{pid}/story-states")).json()
    st=[s for s in states if s["entity_id"]==c["id"]][0]
    assert st["value_text"]=="DEAD" and st["story_time"]==20

@pytest.mark.asyncio
async def test_extract_materializes_knowledge_and_thread(client,proj):
    pid=proj["project"]["id"]; sid=proj["scene"]["id"]
    c=(await client.post(f"/api/v1/projects/{pid}/characters",json={"name":"Bà Lệ"})).json()
    th=(await client.post(f"/api/v1/projects/{pid}/threads",json={"title":"Bí mật hầm"})).json()
    sug1=(await client.post(f"/api/v1/projects/{pid}/suggestions",json={
        "scene_id":sid,"change_type":"knowledge_state",
        "payload":{"knower_name":"Bà Lệ","predicate":"bí mật","value_text":"hầm 4 tồn tại","state":"KNOWS"}})).json()
    d1=(await client.post(f"/api/v1/projects/{pid}/suggestions/{sug1['id']}/approve")).json()
    assert "applied_id" in d1
    ks=(await client.get(f"/api/v1/projects/{pid}/knowledge-states")).json()
    assert ks[0]["knower_id"]==c["id"] and ks[0]["state"]=="KNOWS"
    sug2=(await client.post(f"/api/v1/projects/{pid}/suggestions",json={
        "scene_id":sid,"change_type":"thread_beat",
        "payload":{"thread_title":"Bí mật hầm","beat_type":"reinforcement","note":"nhắc lại hầm 4"}})).json()
    d2=(await client.post(f"/api/v1/projects/{pid}/suggestions/{sug2['id']}/approve")).json()
    assert "applied_id" in d2
    beats=(await client.get(f"/api/v1/projects/{pid}/threads/{th['id']}/beats")).json()
    assert beats[0]["beat_type"]=="reinforcement" and beats[0]["scene_id"]==sid

@pytest.mark.asyncio
async def test_reader_knowledge_knower_type(client,proj):
    pid=proj["project"]["id"]
    f=(await client.post(f"/api/v1/projects/{pid}/canon-facts",json={
        "subject_type":"story","predicate":"twist","value_text":"x"})).json()
    r=await client.post(f"/api/v1/projects/{pid}/knowledge-states",json={
        "knower_id":"reader","fact_id":f["id"],"state":"KNOWS"})
    assert r.status_code==200 and r.json()["knower_type"]=="reader"

@pytest.mark.asyncio
async def test_author_decision_rationale_rejected(client,proj):
    pid=proj["project"]["id"]
    r=await client.post(f"/api/v1/projects/{pid}/author-decisions",json={
        "title":"An Vũ là ai","decision_text":"Là ký ức bị tách",
        "rationale":"giữ twist cho tập 2","rejected":[{"option":"An Vũ là người thật","why":"nhàm"}]})
    assert r.status_code==200
    d=r.json(); assert d["rationale"]=="giữ twist cho tập 2"
    import json as _j; assert _j.loads(d["rejected_json"])[0]["option"].startswith("An Vũ")
    r2=await client.patch(f"/api/v1/projects/{pid}/author-decisions/{d['id']}",json={
        "rationale":"đổi ý","rejected":[]})
    assert r2.status_code==200 and r2.json()["rationale"]=="đổi ý"
