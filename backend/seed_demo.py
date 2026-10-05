"""Demo seed — project "Vĩnh Thành" (rút gọn ~15 chương) qua REST API.

Chạy sau khi backend đã start:
    python seed_demo.py

API base mặc định http://localhost:8000/api/v1 — đổi qua env:
    AI_WRITER_API=http://127.0.0.1:8001/api/v1 python seed_demo.py
"""
import json
import os
import urllib.request

API = os.environ.get("AI_WRITER_API", "http://localhost:8000/api/v1")


def post(path, payload):
    req = urllib.request.Request(
        API + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


# ---------- project ----------
p = post("/projects", {
    "name": "Vĩnh Thành (demo)",
    "description": "Huyền nghi đô thị · Mystery — Một nhân viên lưu trữ phát hiện thành phố liên tục tái cấu trúc sau 02:00: kiến trúc, ký ức, quan hệ đồng loạt thay đổi. Motif: \"Tôi sẽ không quên.\"",
})
pid = p["id"]
print("project", pid)

vol = post(f"/projects/{pid}/volumes", {"title": "Quyển I — Người không có trong hồ sơ", "order_index": 1})
vid = vol["id"]

arcs = {}
for i, t in enumerate(["Hồi 1 · Bản đồ có chín tầng", "Hồi 2 · Sau hai giờ", "Hồi 3 · Đông Thành"], 1):
    arcs[i] = post(f"/projects/{pid}/arcs", {"title": t, "order_index": i, "volume_id": vid})["id"]

CH = [
    "Hồ sơ không khớp", "Một cái tên thừa", "Người đồng nghiệp không tồn tại", "Khách sạn",
    "Chín tầng", "Tôi sẽ không quên",
    "Thử nghiệm đầu tiên", "Hành lang Đông", "Bà Lệ", "Người khách 907",
    "Sự kiện Mất Điện", "Hầm số 4", "Nhà ga vẫn hoạt động", "Không lên tàu",
    "Lời hứa",
]
ARC_OF = {**{i: 1 for i in range(1, 7)}, **{i: 2 for i in range(7, 11)}, **{i: 3 for i in range(11, 16)}}

SYNOPSIS = {
    1: "Minh phát hiện bản vẽ khách sạn 8 tầng trong khi hồ sơ ghi 9. Bản vẽ sau đó cũng trở thành 9 tầng; chỉ ghi chú tay '8T' của Minh còn khác.",
    2: "Minh thấy chữ ký An Vũ trong hồ sơ nhưng nhân sự không có người này. Bên cạnh là nét chữ của chính Minh.",
    3: "Không ai nhớ An. Minh tìm được chìa khóa ký hiệu A.V / 903.",
    4: "Bà Lệ nói 'Lâu hơn lần trước' dù Minh tin đây là lần đầu.",
    5: "Minh đo khách sạn: kích thước trong/ngoài không khớp.",
    6: "Phòng 903: ghi chú của An và câu 'Tôi sẽ không quên' bằng chữ của chính Minh.",
    7: "Minh chủ động đo và ghi chép khách sạn qua 02:00. Hành lang tầng 3 đổi chiều dài.",
    8: "Xuất hiện cửa thứ tám. Bên trong có ảnh Minh và An.",
    9: "Bà Lệ cảnh báo: 'Không phải cái gì cũng đáng mang sang ngày mai.'",
    10: "Khách khẳng định ở 11 năm; lễ tân nói ba ngày. Sáng sau phòng 907 không còn trong cấu trúc hiện tại.",
    11: "Ba nguồn hợp lệ mô tả ba lịch sử khác nhau của Sự kiện Mất Điện.",
    12: "Minh xuống Hầm 4 sau 02:00.",
    13: "Ga ngầm hoạt động bình thường nhưng tuyến tàu thuộc một Vĩnh Thành khác.",
    14: "Minh thấy người giống An trên ET-04 nhưng dừng lại. Khi tàu rời, nhân viên ga hành xử như ga chưa từng đóng.",
    15: "Các phiên bản ghi chép của Minh không thống nhất.",
}

chapter_ids = {}
for i, t in enumerate(CH, 1):
    chapter_ids[i] = post(f"/projects/{pid}/chapters", {
        "title": f"Chương {i}. {t}", "order_index": i, "volume_id": vid, "arc_id": arcs[ARC_OF[i]],
    })["id"]
print("chapters", len(chapter_ids))

# ---------- characters ----------
chars = {}
for name, role, summary, voice in [
    ("Minh Trần", "POV chính", "Nhân viên Cục Lưu trữ Đô thị. Cẩn thận, thiên về kiểm chứng, có thói quen ghi chép; dần ám ảnh với việc xác định cái gì là thật.", "Câu ngắn, quan sát, ít cảm thán"),
    ("An Vũ", "Core Mystery", "Bằng chứng cho thấy từng rất thân thiết với Minh nhưng hồ sơ hiện tại không khớp. Kiến thức của An có giới hạn — không phải NPC biết toàn bộ lore.", None),
    ("Bà Lệ", "Chủ khách sạn", "Liên tục ký ức cao, chứng kiến nhiều phiên bản của khách sạn. Biết nhiều hơn Minh nhưng không biết tất cả.", "Điềm đạm, nói nửa vời"),
]:
    chars[name] = post(f"/projects/{pid}/characters", {"name": name, "role": role, "summary": summary, "voice_notes": voice})["id"]
print("characters", len(chars))
MINH, AN, LE = chars["Minh Trần"], chars["An Vũ"], chars["Bà Lệ"]

post(f"/projects/{pid}/aliases", {"character_id": AN, "alias": "A.V", "notes": "Ký hiệu trên chìa khóa phòng 903"})

# ---------- locations ----------
zone = post(f"/projects/{pid}/locations", {"name": "Trung tâm Cũ", "description": "Cục Lưu trữ, tòa án, thư viện, khách sạn."})["id"]
hotel = post(f"/projects/{pid}/locations", {"name": "Khách sạn 9 tầng", "description": "Hiện tại 9 tầng; dấu vết lịch sử 7 và 8 tầng. Bên trong lớn hơn đo từ ngoài. Chủ: Bà Lệ.", "parent_location_id": zone})["id"]
post(f"/projects/{pid}/locations", {"name": "Hành lang Đông", "description": "Tầng 3 khách sạn. Sau 02:00 đôi khi xuất hiện đoạn hành lang/cửa không có trong sơ đồ hiện tại.", "parent_location_id": hotel})
zone2 = post(f"/projects/{pid}/locations", {"name": "Đông Thành", "description": "Ga tàu, khu trọ, lao động, người nhập cư."})["id"]
ga = post(f"/projects/{pid}/locations", {"name": "Ga Đông Thành", "description": "Đóng cửa từ Sự kiện Mất Điện. Hiện 4 lối hầm; bản vẽ cũ chỉ có 3.", "parent_location_id": zone2})["id"]
post(f"/projects/{pid}/locations", {"name": "Hầm số 4", "description": "Vẫn hoạt động sau 02:00. Một số chuyến tàu có thể thuộc mạng lưới Vĩnh Thành khác. Liên hệ ET-04.", "parent_location_id": ga})
print("locations done")

# ---------- relationships ----------
for a, b, t, n in [
    (MINH, AN, "trung tâm / chưa định danh", "Variant A: đồng nghiệp · Variant B: thân mật · Hiện tại An→Minh: người lạ; Minh→An: tò mò / nghĩa vụ."),
    (MINH, LE, "người giữ ký ức", "Người cố giữ ↔ người đã học cách sống cùng biến đổi."),
    (AN, MINH, "không nhớ", "Current reality: An đang sống với lịch sử hoàn chỉnh không có Minh."),
]:
    post(f"/projects/{pid}/relationships", {"source_character_id": a, "target_character_id": b, "relationship_type": t, "notes": n})

# ---------- canon facts ----------
facts = {}
for key, st, pred, val, status in [
    ("hotel9", "world", "khách-sạn.số-tầng", "9 tầng", "CANON"),
    ("hotel8v", "world", "khách-sạn.số-tầng.lịch-sử", "Từng có dấu vết 7 và 8 tầng", "PLANNED"),
    ("ga4", "world", "ga-đông-thành.lối-hầm", "4 lối hầm hiện tại; bản vẽ cũ 3", "CANON"),
    ("tai-cau-truc", "world", "vĩnh-thành.tái-cấu-trúc", "Sau ~02:00 một số phần thành phố có thể xuất hiện sai lệch", "CANON"),
    ("an-evidence", "character", "an-vũ.bằng-chứng-liên-hệ", "Chữ ký, chìa khóa A.V/903, ảnh, thư, vé ET-04", "CANON"),
]:
    facts[key] = post(f"/projects/{pid}/canon-facts", {
        "subject_type": st, "predicate": pred, "value_text": val, "truth_status": status,
    })["id"]
print("facts", len(facts))

post(f"/projects/{pid}/secrets", {"fact_id": facts["an-evidence"], "title": "An Vũ là ai?", "status": "OPEN"})
post(f"/projects/{pid}/secrets", {"fact_id": facts["hotel8v"], "title": "Vì sao khách sạn có 9 tầng?", "status": "OPEN"})

# ---------- knowledge states ----------
for knower, fid, state, lvl, no in [
    (MINH, facts["hotel9"], "KNOWS", 100, 1),
    (MINH, facts["hotel8v"], "KNOWS", 60, 1),
    (MINH, facts["an-evidence"], "SUPPOSES", 40, 2),
    (AN, facts["hotel9"], "UNAWARE", 0, None),
]:
    post(f"/projects/{pid}/knowledge-states", {"knower_type": "character", "knower_id": knower, "fact_id": fid, "state": state, "disclosure_level": lvl, "acquired_narrative_order": no})
post(f"/projects/{pid}/knowledge-states", {"knower_type": "reader", "knower_id": "reader", "fact_id": facts["an-evidence"], "state": "KNOWS", "disclosure_level": 50, "acquired_narrative_order": 2})

# ---------- threads ----------
threads = {}
for key, title, ttype, desc, payoff in [
    ("M-001", "M-001 · An Vũ là ai?", "mystery", "Giới thiệu Ch.2 · Bằng chứng: chữ ký, chìa khóa, ảnh Minh–An, vé ET-04.", 15),
    ("M-002", "M-002 · Vì sao khách sạn có 9 tầng?", "mystery", "AI rule: không tự giải thích nguồn gốc cuối cùng.", None),
    ("M-003", "M-003 · Sự kiện Mất Điện", "mystery", "Nhiều tài liệu hợp lệ nhưng mâu thuẫn về thời lượng và diễn biến.", None),
]:
    threads[key] = post(f"/projects/{pid}/threads", {
        "title": title, "thread_type": ttype, "status": "OPEN", "description": desc, "planned_payoff_order": payoff,
    })["id"]
print("threads", len(threads))

for btype, no, notes in [
    ("setup", 2, "Chữ ký An Vũ xuất hiện trong hồ sơ"),
    ("reinforcement", 6, "Ghi chú phòng 903: 'Tôi sẽ không quên'"),
    ("escalation", 14, "Người giống An trên tàu ET-04"),
    ("payoff", 15, "Reveal dự kiến: An phân tán bằng chứng tồn tại vào mạng lưới xã hội"),
]:
    post(f"/projects/{pid}/threads/{threads['M-001']}/beats", {"beat_type": btype, "narrative_order": no, "notes": notes})

# ---------- scenes ----------
for ch, stype, titles in [
    (1, "discovery", ["Cục Lưu trữ — phát hiện bản vẽ lệch", "Bản vẽ — hỏi đồng nghiệp"]),
    (6, "reveal", ["Phòng 903 — câu viết bằng chữ chính mình"]),
    (12, "mystery", ["Xuống Hầm 4 sau 02:00"]),
]:
    for j, st in enumerate(titles, 1):
        post(f"/projects/{pid}/chapters/{chapter_ids[ch]}/scenes", {
            "title": st, "order_index": j, "scene_type": stype, "pov_character_id": MINH,
            "skeleton": f"• {SYNOPSIS[ch]}",
        })
print("scenes done")

# ---------- author decisions ----------
for t, dtxt in [
    ("Motif xuyên suốt", "Câu 'Tôi sẽ không quên' đổi nghĩa theo truyện: giữ quá khứ → chống tái cấu trúc → không để ai bị xóa."),
    ("Không giải mystery bằng lore", "Mỗi hồi phải có ít nhất một mystery được giải thật. Triết học không dùng để che plot hole."),
    ("An có kiến thức giới hạn", "Không biến An thành NPC biết toàn bộ lore."),
]:
    post(f"/projects/{pid}/author-decisions", {"title": t, "decision_text": dtxt, "status": "active"})

# ---------- suggestions (demo review queue) ----------
for ct, txt in [
    ("canon_fact", "Minh và Bà Lệ từng gặp nhau trước chương 1 (đề xuất từ draft)"),
    ("relationship", "Đề xuất cập nhật quan hệ Minh–An: 'chưa định danh'"),
]:
    post(f"/projects/{pid}/suggestions", {"change_type": ct, "payload": {"text": txt, "needs_author_review": True}})

# ---------- what-if branch ----------
post(f"/projects/{pid}/branches", {"name": "What-if: An nhớ Minh ở Ch.6"})

# ---------- story events / states ----------
post(f"/projects/{pid}/story-events", {"event_type": "discovery", "summary": "Minh phát hiện bản vẽ 8 tầng lệch với hồ sơ 9 tầng", "story_time": 1, "narrative_order": 1, "location_id": zone})
post(f"/projects/{pid}/story-events", {"event_type": "reveal", "summary": "Phòng 903: 'Tôi sẽ không quên' bằng chữ Minh", "story_time": 6, "narrative_order": 6, "location_id": hotel})
post(f"/projects/{pid}/story-events", {"event_type": "historical", "summary": "Sự kiện Mất Điện — ga Đông Thành đóng cửa", "story_time": -30, "narrative_order": 11, "location_id": ga})
post(f"/projects/{pid}/story-states", {"entity_type": "world", "entity_id": str(hotel), "key": "số tầng", "value_text": "9", "narrative_order": 1})
post(f"/projects/{pid}/story-states", {"entity_type": "character", "entity_id": MINH, "key": "biết-về-an", "value_text": "chưa biết An Vũ là ai", "narrative_order": 1})

# ---------- style profile ----------
post(f"/projects/{pid}/style-profiles", {
    "name": "Tone Vĩnh Thành", "scope_type": "project", "scope_id": pid, "priority": 1, "active": True,
    "instructions": "Trưởng thành, tiết chế. Mystery hiện diện dưới đời sống thường nhật — dị thường càng bình thường càng hiệu quả. Triết học đi qua tình huống, không giảng đạo.",
})

# ---------- discussion ----------
th = post(f"/projects/{pid}/discussions", {"title": "Động não: quan hệ Minh–An", "role": "brainstorm"})
post(f"/projects/{pid}/discussions/{th['id']}/messages", {"content": "Nếu cho An và Minh từng thân mật thì ảnh hưởng gì tới reveal cuối hồi?"})

print("DONE — project id:", pid)
