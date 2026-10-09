
import pytest
from app.services.credentials import encrypt_secret,decrypt_secret,key_hint

def test_secret_roundtrip_and_hint():
    enc=encrypt_secret("sk-test-123456")
    assert "sk-test" not in enc
    assert decrypt_secret(enc)=="sk-test-123456"
    assert key_hint("sk-test-123456")=="••••3456"

@pytest.mark.asyncio
async def test_credential_never_returns_secret(client):
    r=(await client.post("/api/v1/account/credentials",json={
        "provider":"openai","secret":"sk-super-secret-value"})).json()
    assert r["secret"] is None and r["key_hint"]=="••••alue"
    assert "sk-super" not in str(r)
    lst=(await client.get("/api/v1/account/credentials")).json()
    assert all(c["secret"] is None for c in lst)
    d=(await client.delete(f"/api/v1/account/credentials/{r['id']}")).json()
    assert d["status"]=="revoked"

@pytest.mark.asyncio
async def test_credential_tier_auto_and_override(client):
    # auto: provider map quyết tier (kiraai=low, openai=strong, custom=standard)
    k=(await client.post("/api/v1/account/credentials",json={
        "provider":"kiraai","secret":"sk-k1"})).json()
    assert k["tier"]=="low" and k["tier_override"] is None
    o=(await client.post("/api/v1/account/credentials",json={
        "provider":"openai","secret":"sk-o1"})).json()
    assert o["tier"]=="strong"
    c=(await client.post("/api/v1/account/credentials",json={
        "provider":"custom","secret":"sk-c1","tier":"strong"})).json()
    assert c["tier"]=="strong" and c["tier_override"]=="strong"
    # override qua PATCH; tier=null → về auto
    p=(await client.patch(f"/api/v1/account/credentials/{k['id']}",json={"tier":"strong"})).json()
    assert p["tier"]=="strong" and p["tier_override"]=="strong"
    p=(await client.patch(f"/api/v1/account/credentials/{k['id']}",json={"tier":None})).json()
    assert p["tier"]=="low" and p["tier_override"] is None
    bad=await client.patch(f"/api/v1/account/credentials/{k['id']}",json={"tier":"mega"})
    assert bad.status_code==400
    # list trả tier
    lst=(await client.get("/api/v1/account/credentials")).json()
    assert all("tier" in x for x in lst)

@pytest.mark.asyncio
async def test_model_preference_resolution(client,proj):
    pid=proj["project"]["id"]
    await client.post("/api/v1/account/model-preferences",json={
        "task":"writing","provider":"openai","model":"gpt-4.1"})
    await client.post("/api/v1/account/model-preferences",json={
        "task":"writing","provider":"anthropic","model":"claude","project_id":pid})
    r=(await client.get("/api/v1/account/model-preferences/resolve",
        params={"task":"writing","project_id":pid})).json()
    assert r["model"]=="claude" and r["source"]=="project"
    r=(await client.get("/api/v1/account/model-preferences/resolve",
        params={"task":"writing"})).json()
    assert r["model"]=="gpt-4.1" and r["source"]=="account"

@pytest.mark.asyncio
async def test_branch_merge_only_creates_decision_and_is_idempotent(client,proj):
    pid=proj["project"]["id"]
    b=(await client.post(f"/api/v1/projects/{pid}/branches",json={"name":"what-if"})).json()
    bad=await client.post(f"/api/v1/projects/{pid}/branches/{b['id']}/changes",json={
        "change_type":"delete_canon","payload":{}})
    assert bad.status_code==400
    ch=(await client.post(f"/api/v1/projects/{pid}/branches/{b['id']}/changes",json={
        "change_type":"canon_override","payload":{"fact":"x","new":"y"}})).json()
    m1=(await client.post(f"/api/v1/projects/{pid}/branches/{b['id']}/changes/{ch['id']}/merge")).json()
    assert m1["mutates_canon"] is False and m1["mutates_manuscript"] is False
    m2=(await client.post(f"/api/v1/projects/{pid}/branches/{b['id']}/changes/{ch['id']}/merge")).json()
    assert m2["idempotent"] is True and m2["decision_id"]==m1["decision_id"]
    decisions=(await client.get(f"/api/v1/projects/{pid}/author-decisions")).json()
    assert len(decisions)==1
    facts=(await client.get(f"/api/v1/projects/{pid}/canon-facts")).json()
    assert facts==[]


@pytest.mark.asyncio
async def test_usage_log_records_ai_calls(client, proj):
    pid = proj["project"]["id"]
    th = (await client.post(f"/api/v1/projects/{pid}/discussions", json={
        "title": "T", "role": "assistant"})).json()
    await client.post(f"/api/v1/projects/{pid}/discussions/{th['id']}/messages",
                      json={"content": "hello", "author": "author"})
    r = await client.post(f"/api/v1/projects/{pid}/discussions/{th['id']}/ai-reply",
                          json={})
    assert r.status_code == 200
    usage = (await client.get("/api/v1/account/usage")).json()
    assert usage["rows"], "expected usage rows"
    disc = next((r for r in usage["rows"] if r["task"] == "discussion"), None)
    assert disc and disc["project_id"] == pid and disc["provider"] == "fake"
    assert usage["by_task"]["discussion"]["calls"] >= 1
