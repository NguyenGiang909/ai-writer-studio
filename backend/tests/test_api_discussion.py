
import pytest

@pytest.mark.asyncio
async def test_discussion_flow(client,proj):
    pid=proj["project"]["id"]
    t=(await client.post(f"/api/v1/projects/{pid}/discussions",json={
        "title":"Plot talk","role":"plot_doctor"})).json()
    m=(await client.post(f"/api/v1/projects/{pid}/discussions/{t['id']}/messages",json={
        "content":"What if the mentor betrays?"})).json()
    assert m["author"]=="author"
    msgs=(await client.get(f"/api/v1/projects/{pid}/discussions/{t['id']}/messages")).json()
    assert len(msgs)==1
    r=await client.patch(f"/api/v1/projects/{pid}/discussions/{t['id']}/messages/{m['id']}",json={"pinned":True})
    assert r.json()["pinned"] is True

@pytest.mark.asyncio
async def test_ai_reply_fake_provider(client,proj):
    pid=proj["project"]["id"]
    t=(await client.post(f"/api/v1/projects/{pid}/discussions",json={"title":"T"})).json()
    await client.post(f"/api/v1/projects/{pid}/discussions/{t['id']}/messages",json={"content":"hi"})
    r=await client.post(f"/api/v1/projects/{pid}/discussions/{t['id']}/ai-reply")
    assert r.status_code==200 and r.json()["author"]=="ai"
    msgs=(await client.get(f"/api/v1/projects/{pid}/discussions/{t['id']}/messages")).json()
    assert len(msgs)==2 and msgs[-1]["author"]=="ai"

@pytest.mark.asyncio
async def test_ai_reply_503_when_fake_disabled(client,proj,monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings,"allow_fake_provider",False)
    pid=proj["project"]["id"]
    t=(await client.post(f"/api/v1/projects/{pid}/discussions",json={"title":"T"})).json()
    await client.post(f"/api/v1/projects/{pid}/discussions/{t['id']}/messages",json={"content":"hi"})
    r=await client.post(f"/api/v1/projects/{pid}/discussions/{t['id']}/ai-reply")
    assert r.status_code==503
    msgs=(await client.get(f"/api/v1/projects/{pid}/discussions/{t['id']}/messages")).json()
    assert len(msgs)==1

@pytest.mark.asyncio
async def test_discussion_auto_summary(client,proj):
    pid=proj["project"]["id"]
    t=(await client.post(f"/api/v1/projects/{pid}/discussions",json={"title":"T"})).json()
    for i in range(4):
        await client.post(f"/api/v1/projects/{pid}/discussions/{t['id']}/messages",json={"content":f"msg {i}"})
        r=await client.post(f"/api/v1/projects/{pid}/discussions/{t['id']}/ai-reply")
        assert r.status_code==200
    s=(await client.get(f"/api/v1/projects/{pid}/summaries?scope_type=discussion")).json()
    assert len(s)==1 and s[0]["scope_id"]==t["id"] and s[0]["narrative_end"]==8 and s[0]["summary"]
    # 9 messages → next reply keeps going, summary stays the memory of earlier turns
    await client.post(f"/api/v1/projects/{pid}/discussions/{t['id']}/messages",json={"content":"more"})
    r=await client.post(f"/api/v1/projects/{pid}/discussions/{t['id']}/ai-reply")
    assert r.status_code==200
    s2=(await client.get(f"/api/v1/projects/{pid}/summaries?scope_type=discussion")).json()
    assert len(s2)==1 and s2[0]["stale"] is False

@pytest.mark.asyncio
async def test_style_preference(client,proj):
    pid=proj["project"]["id"]
    sp=(await client.post(f"/api/v1/projects/{pid}/style-profiles",json={"name":"Default","scope_type":"global"})).json()
    p=(await client.post(f"/api/v1/projects/{pid}/style-preferences",json={
        "style_profile_id":sp["id"],"preference_type":"banned","pattern":"suddenly"})).json()
    assert p["explicit_author_feedback"] is True
    lst=(await client.get(f"/api/v1/projects/{pid}/style-preferences")).json()
    assert len(lst)==1
