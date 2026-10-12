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

## Video mô phỏng — máy tự viết trước mắt

Quay tự động bằng Playwright (`recordVideo`) trên app thật — không dựng lại:

**Engine viết 3 chương live** — project rỗng → premise → các gate duyệt →
chapters/scenes hiện ra trong manuscript tree:

<video src="video/ai-writer-chapters-live.mp4" controls width="720"></video>

**Tour truyện 69 chương thật** — manuscript tree, prose do máy viết,
review/audit, timeline, search:

<video src="video/ai-writer-demo.mp4" controls width="720"></video>

**Start run trên project rỗng** — `POST /authoring/start`, premise →
`awaiting_review` (cổng duyệt của tác giả):

<video src="video/ai-writer-authoring-live.mp4" controls width="720"></video>

Script quay lại: `demo-record*.js` trong thư mục này (cần Playwright +
app chạy :3000/:8001). Bản webm gốc ~60MB giữ ngoài repo.

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
