"""Audit dò lỗi toàn dự án — checker deterministic mới.

Mỗi checker bắt đúng lớp lỗi phát hiện từ project 58 chương: canon mâu
thuẫn, state xung đột cùng vị trí, tuổi/lớp lùi mạch, prose nhắc địa điểm
ngoài dàn ý, entity nhắc trước khi tồn tại, chương chưa trích dữ kiện.
Endpoint /continuity/check phải trả đủ code mới; deep-check lưu findings.
"""
import json

import pytest, pytest_asyncio
import app.services.authoring as eng
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models import Arc, Character, Chapter, Scene
from app.models.story import Location
from app.models.truth import CanonFact, StoryEvent, StoryState
from app.models.review import AuditFinding
from app.services.continuity import (
    canon_conflict, state_conflict, state_regression, num_from,
    phase_leak, missing_extraction, scene_no_narr)


@pytest.fixture(autouse=True)
def _no_spawn(monkeypatch):
    monkeypatch.setattr(eng, "spawn", lambda rid: None)


def test_num_from():
    assert num_from("lớp 6A4") == 6
    assert num_from("lớp Chín") == 9
    assert num_from("mười một tuổi") == 11
    assert num_from("12") == 12
    assert num_from("không số") is None


def test_canon_conflict_and_options():
    iss = canon_conflict("Sơn", "age", ["f1", "f2"],
                         ["11 tuổi", "11 tuổi, con trai"])
    assert iss is None  # "11 tuổi" là subset → gộp thành 1 giá trị
    iss = canon_conflict("Sơn", "age", ["f1", "f2"],
                         ["lớp Chín", "lớp Sáu"])
    assert iss and iss.code == "CANON_CONFLICT"
    assert iss.evidence["fact_id"] == "f1"
    opts = iss.evidence["options"]
    assert {o["value"] for o in opts} == {"lớp Chín", "lớp Sáu"}
    assert opts[0]["ids"] == ["f1"]


def test_state_conflict_and_regression():
    iss = state_conflict("Sơn", "education", 25, ["s1", "s2"],
                         ["trường cấp hai thành phố", "6A4"], "character", "cid")
    assert iss and iss.code == "STATE_CONFLICT"
    assert iss.evidence["character_id"] == "cid"
    assert len(iss.evidence["options"]) == 2
    # cùng giá trị (kể cả near-dup) → không flag
    assert state_conflict("Sơn", "location", 2, ["s1", "s2"],
                          ["khu tập thể", "Khu  tập thể"], "character", "cid") is None
    # lùi mạch: Chín(9) → sáu(6)
    iss = state_regression("Sơn", "education", (1, "lớp Chín"), (25, "lớp sáu"),
                           "character", "cid")
    assert iss and iss.code == "STATE_REGRESSION"
    # tăng bình thường → không flag
    assert state_regression("Sơn", "age", (1, "11 tuổi"), (25, "12 tuổi"),
                            "character", "cid") is None


def test_phase_leak_and_pipeline_checks():
    iss = phase_leak("Quán net", "location", "lid", "sc1", "Đường về", 2, 11)
    assert iss and iss.code == "PHASE_LEAK"
    assert iss.evidence["location_id"] == "lid"
    assert missing_extraction("c1", "Tên", 5).code == "MISSING_EXTRACTION"
    assert scene_no_narr("s1", "Tên", 5).code == "SCENE_NO_NARR"


@pytest.mark.asyncio
async def test_check_endpoint_finds_new_issue_codes(client):
    pid = (await client.post("/api/v1/projects", json={"name": "Audit"})).json()["id"]
    async with SessionLocal() as db:
        ch = Chapter(project_id=pid, title="C1", order_index=1)
        loc = Location(project_id=pid, name="Quán net Hồng Hà")
        c = Character(project_id=pid, name="Minh")
        db.add_all([ch, loc, c]); await db.flush()
        db.add(Scene(project_id=pid, chapter_id=ch.id, title="Đường về",
                     order_index=1, narrative_order=1,
                     skeleton="Đi học về qua làng",
                     prose="Minh ghé Quán net Hồng Hà chơi một ván."))
        # canon mâu thuẫn: cùng Sơn-subject, predicate tuổi, 2 giá trị khác
        db.add_all([
            CanonFact(project_id=pid, subject_type="character", subject_id=c.id,
                      predicate="tuổi", value_text="11"),
            CanonFact(project_id=pid, subject_type="character", subject_id=c.id,
                      predicate="tuổi", value_text="15"),
            # location entity chỉ xuất hiện từ ch11 → nhắc ở ch1 = phase leak
            StoryState(project_id=pid, entity_type="location", entity_id=loc.id,
                       key="status", value_text="mở cửa", narrative_order=11),
        ])
        await db.commit()
    r = await client.get(f"/api/v1/projects/{pid}/continuity/check")
    assert r.status_code == 200
    codes = {i["code"] for i in r.json()["issues"]}
    assert "CANON_CONFLICT" in codes
    assert "LOCATION_DRIFT" in codes   # "Quán net Hồng Hà" không có trong skeleton/state
    assert "PHASE_LEAK" in codes       # địa danh chỉ có state từ ch11
    assert "MISSING_EXTRACTION" in codes


@pytest.mark.asyncio
async def test_check_no_conflict_when_consistent(client):
    pid = (await client.post("/api/v1/projects", json={"name": "OK"})).json()["id"]
    async with SessionLocal() as db:
        c = Character(project_id=pid, name="Minh")
        db.add(c); await db.flush()
        db.add_all([
            CanonFact(project_id=pid, subject_type="character", subject_id=c.id,
                      predicate="tuổi", value_text="11"),
            CanonFact(project_id=pid, subject_type="character", subject_id=c.id,
                      predicate="tuổi", value_text="11 tuổi"),
        ])
        await db.commit()
    r = await client.get(f"/api/v1/projects/{pid}/continuity/check")
    codes = {i["code"] for i in r.json()["issues"]}
    assert "CANON_CONFLICT" not in codes  # near-dup → không phải conflict


@pytest.mark.asyncio
async def test_deep_check_persists_findings(client):
    pid = (await client.post("/api/v1/projects", json={"name": "Deep"})).json()["id"]
    async with SessionLocal() as db:
        ch = Chapter(project_id=pid, title="C1", order_index=1)
        db.add(ch); await db.flush()
        db.add(Scene(project_id=pid, chapter_id=ch.id, title="Sáng",
                     order_index=1, narrative_order=1,
                     prose="Minh đi học qua cánh đồng."))
        chid = ch.id
        await db.commit()
    r = await client.post(f"/api/v1/projects/{pid}/chapters/{chid}/deep-check")
    assert r.status_code == 200
    fid = r.json()["finding_id"]
    async with SessionLocal() as db:
        f = await db.get(AuditFinding, fid)
        assert f and f.scope_id == chid and json.loads(f.issues_json) is not None
    # list + delete
    lst = (await client.get(f"/api/v1/projects/{pid}/audit/findings")).json()
    assert any(x["id"] == fid and x["chapter_title"] == "C1" for x in lst["findings"])
    r = await client.delete(f"/api/v1/audit/findings/{fid}")
    assert r.status_code == 200
    lst = (await client.get(f"/api/v1/projects/{pid}/audit/findings")).json()
    assert not any(x["id"] == fid for x in lst["findings"])
    # chương không prose → 400
    async with SessionLocal() as db:
        ch2 = Chapter(project_id=pid, title="Trống", order_index=2)
        db.add(ch2); await db.commit()
        ch2id = ch2.id
    r = await client.post(f"/api/v1/projects/{pid}/chapters/{ch2id}/deep-check")
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_range_deep_check(client):
    pid = (await client.post("/api/v1/projects", json={"name": "Range"})).json()["id"]
    async with SessionLocal() as db:
        for i in (1, 2, 3):
            ch = Chapter(project_id=pid, title=f"C{i}", order_index=i)
            db.add(ch); await db.flush()
            db.add(Scene(project_id=pid, chapter_id=ch.id, title=f"S{i}",
                         order_index=1, narrative_order=i,
                         prose=f"Đoạn văn của chương {i}. " * 60))
        await db.commit()
    r = await client.post(f"/api/v1/projects/{pid}/deep-check",
                          json={"from_order": 1, "to_order": 2})
    assert r.status_code == 200
    d = r.json()
    assert d["mode"] == "prose" and d["from_order"] == 1 and d["to_order"] == 2
    assert any("thiếu tóm tắt" in w for w in d["warnings"])
    fid = d["finding_id"]
    async with SessionLocal() as db:
        f = await db.get(AuditFinding, fid)
        assert f and f.scope_type == "range" and f.scope_id == "1-2"
    lst = (await client.get(f"/api/v1/projects/{pid}/audit/findings")).json()
    assert any(x["id"] == fid and x["scope_label"] == "Chương 1–2" for x in lst["findings"])
    # invalid ranges
    assert (await client.post(f"/api/v1/projects/{pid}/deep-check",
            json={"from_order": 3, "to_order": 1})).status_code == 400
    assert (await client.post(f"/api/v1/projects/{pid}/deep-check",
            json={"from_order": 8, "to_order": 9})).status_code == 400
    # outline mode: chương chỉ có skeleton
    pid2 = (await client.post("/api/v1/projects", json={"name": "Outline"})).json()["id"]
    async with SessionLocal() as db:
        ch = Chapter(project_id=pid2, title="O1", order_index=1)
        db.add(ch); await db.flush()
        db.add(Scene(project_id=pid2, chapter_id=ch.id, title="OS",
                     order_index=1, skeleton="Minh mở rương cũ"))
        await db.commit()
    r = await client.post(f"/api/v1/projects/{pid2}/deep-check", json={})
    assert r.status_code == 200 and r.json()["mode"] == "outline"


@pytest.mark.asyncio
async def test_style_fatigue_flagged(client):
    pid = (await client.post("/api/v1/projects", json={"name": "Fatigue"})).json()["id"]
    # cụm "cái nhìn lạnh lẽo" lặp 10 lần — dấu hiệu văn mẫu
    prose = " ".join(["Minh bước đi trên con đường quen thuộc mỗi sáng sớm. Cái nhìn lạnh lẽo phủ xuống căn phòng vắng." for _ in range(10)])
    async with SessionLocal() as db:
        ch = Chapter(project_id=pid, title="F1", order_index=1)
        db.add(ch); await db.flush()
        db.add(Scene(project_id=pid, chapter_id=ch.id, title="F",
                     order_index=1, narrative_order=1, prose=prose))
        await db.commit()
    r = await client.get(f"/api/v1/projects/{pid}/continuity/check")
    codes = {i["code"] for i in r.json()["issues"]}
    assert "STYLE_FATIGUE" in codes
    fat = [i for i in r.json()["issues"] if i["code"] == "STYLE_FATIGUE"]
    assert fat[0]["evidence"]["count"] >= 8
