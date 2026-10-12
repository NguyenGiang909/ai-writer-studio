"""Style memory (Novel Humanizer port): lifecycle candidate→confirmed→rejected,
scope resolution, prompt injection, preset idempotency."""
import pytest

B = "/api/v1/projects"


async def _manifest(client, pid, scene_id):
    r = await client.post(f"{B}/{pid}/ai/context-manifest",
                          json={"task": "writing", "scene_id": scene_id})
    assert r.status_code == 200
    return r.json().get("manifest", [])


def _style_lines(manifest):
    return [l for l in manifest if "style-rules" in str(l)]


@pytest.mark.asyncio
async def test_rule_lifecycle_and_injection(client, proj):
    pid, scene = proj["project"]["id"], proj["scene"]["id"]
    # tạo luật tường minh → confirmed ngay (không qua chờ duyệt)
    r = await client.post(f"{B}/{pid}/style-rules",
                          json={"pattern": "gộp đoạn 3-8 câu",
                                "strength": "HARD", "preference_type": "prefer"})
    assert r.status_code == 200, r.text
    rid = r.json()["id"]
    assert r.json()["status"] == "confirmed"
    assert r.json()["profile_name"] == "AI tự học"

    # confirmed → inject vào manifest
    assert any("style-rules: 1" in l for l in _style_lines(await _manifest(client, pid, scene)))

    # reject → mất hiệu lực
    r = await client.patch(f"{B}/{pid}/style-rules/{rid}", json={"status": "rejected"})
    assert r.json()["status"] == "rejected"
    assert any("style-rules: 0" in l for l in _style_lines(await _manifest(client, pid, scene)))

    # mở lại → có hiệu lực trở lại
    r = await client.patch(f"{B}/{pid}/style-rules/{rid}", json={"status": "confirmed"})
    assert any("style-rules: 1" in l for l in _style_lines(await _manifest(client, pid, scene)))


@pytest.mark.asyncio
async def test_candidates_not_injected(client, proj):
    """Candidate (AI suy ra) KHÔNG được vào prompt — chỉ confirmed mới là luật."""
    pid, scene = proj["project"]["id"], proj["scene"]["id"]
    # hạ rule xuống candidate qua patch (cùng hướng AI tạo candidate)
    r = await client.post(f"{B}/{pid}/style-rules", json={"pattern": "x"})
    rid = r.json()["id"]
    await client.patch(f"{B}/{pid}/style-rules/{rid}", json={"status": "candidate"})
    assert any("style-rules: 0" in l for l in _style_lines(await _manifest(client, pid, scene)))


@pytest.mark.asyncio
async def test_scope_resolution(client, proj):
    """Rule gắn scope chương KHÁC → không áp cho cảnh hiện tại."""
    pid, ch, scene = proj["project"]["id"], proj["chapter"]["id"], proj["scene"]["id"]
    r = await client.post(f"{B}/{pid}/style-rules", json={
        "pattern": "luật của chương khác", "scope_type": "chapter",
        "scope_id": "00000000-0000-0000-0000-000000000000"})
    assert r.status_code == 200
    assert any("style-rules: 0" in l for l in _style_lines(await _manifest(client, pid, scene)))
    # scope đúng chương này → áp
    await client.post(f"{B}/{pid}/style-rules", json={
        "pattern": "luật chương này", "scope_type": "chapter", "scope_id": ch})
    assert any("style-rules: 1" in l for l in _style_lines(await _manifest(client, pid, scene)))


@pytest.mark.asyncio
async def test_learn_instruction_and_apply_preset_idempotent(client, proj):
    pid = proj["project"]["id"]
    # instruction → confirmed (tác giả nói thẳng, không cần duyệt)
    r = await client.post(f"{B}/{pid}/style-rules/learn",
                          json={"instruction": "ít dấu gạch ngang"})
    assert r.status_code == 200, r.text
    assert r.json()["created"] == "confirmed"
    # apply-preset idempotent: lần 2 không nhân đôi
    payload = {"profiles": [{"name": "P1", "instructions": "giọng gãy"}],
               "rules": [{"pattern": "rule-a"}, {"pattern": "rule-b"}],
               "canon_facts": [{"predicate": "ghế", "value_text": "5"}]}
    a1 = (await client.post(f"{B}/{pid}/style/apply-preset", json=payload)).json()["applied"]
    assert a1 == {"profiles": 1, "rules": 2, "canon_facts": 1}
    a2 = (await client.post(f"{B}/{pid}/style/apply-preset", json=payload)).json()["applied"]
    assert a2 == {"profiles": 0, "rules": 0, "canon_facts": 0}
    # rules preset → status confirmed, source preset
    rules = (await client.get(f"{B}/{pid}/style-rules")).json()["rules"]
    preset_rules = [x for x in rules if x["source"] == "preset"]
    assert len(preset_rules) == 2 and all(x["status"] == "confirmed" for x in preset_rules)
