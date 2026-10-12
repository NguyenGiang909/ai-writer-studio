# Demo — 3 truyện do máy viết gần trọn

Ba dự án thật được viết end-to-end bởi authoring engine + model giá rẻ
(KiraAI flash-tier), sau đó tác giả rà/sửa — đúng quy trình "AI nháp,
người tổng biên". Export bằng `GET /projects/{id}/export`.

| Dự án | Chương | Cảnh | ~Ký tự prose | AI calls | Pipeline |
|---|---|---|---|---|---|
| Những Cuộc Tình Tải Xuống | 69 | 468 | ~1.5M | 897 | Full: arc_chapters → chapter_outline → scene_expand → chapter_facts → summaries → deep_check |
| Những Năm Tháng Ấy Ở Khu Tập Thể | 58 | 397 | ~1.9M | 50 | authoring run + scene_expand |
| Vĩnh Thành Lúc Hai Giờ | 55 | 55 | ~0.5M | 121 | task `writing` trực tiếp (workflow đời cũ) |

Mỗi dự án 2 file:

- `*.json` — dump toàn bộ project-scoped tables (scenes, chapters,
  canon_facts, threads, states, ai_turns…): import lại được, đủ để soi
  provenance — cảnh nào AI viết, facts nào được trích, turn nào tốn bao
  lâu (`latency_ms`)
- `*.md` — bản thảo Quyển→Hồi→Chương→Cảnh để đọc trực tiếp

**Không chứa** credential/API key (secrets là bảng bí-mật-trong-truyện).

## Video mô phỏng (quay tự động)

`demo-record*.js` — Playwright headless tự lái app (backend :8001 +
frontend :3000), `recordVideo` ra `.webm`:

- `demo-record.js` — tour truyện 69 chương: manuscript, prose, review,
  timeline, authoring, search
- `demo-record-authoring.js` — project rỗng → `POST /authoring/start`
  (premise → gate `awaiting_review`)
- `demo-record-chapters.js` — auto-approve từng gate → **3 chương +
  scenes do engine viết trước mắt**

Video nằm ngoài repo (`demo/video/` gitignored — ~60MB). Quay lại:
`cd demo && node demo-record.js` (cần playwright + app đang chạy).

## Đọc nhanh bằng chứng "máy viết"

`nhung-cuoc-tinh-tai-xuong.json` → `ai_turns[]` có 897 turn: task
`scene_expand` 459, `chapter_facts` 331, `chapter_outline` 68,
`arc_chapters` 8, `deep_check` 4 — đúng chuỗi pipeline của engine.
`authoring_runs` (trong `counts`) có 1 run target 69 chương đạt đủ rồi
hard-stop.

## Chi phí

Hai cuốn lớn viết trên model flash-tier (deepseek-v4.1-flash,
qwen3.8-flash qua gateway KiraAI) — mức giá cents-scale mỗi nghìn token;
toàn bộ continuity do story DB + checker deterministic gánh, model rẻ
chỉ lo văn.
