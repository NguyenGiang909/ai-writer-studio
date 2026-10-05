# AI Writer Studio — ghi nhớ phiên làm việc

Story OS cho tiểu thuyết dài kỳ: tác giả viết trước, AI hỗ trợ (thảo luận, mở rộng, kiểm tra continuity). **Tác giả là authority** — AI không được tự đổi Canon/prose; mọi gợi ý là bản nháp hoặc qua Review queue.

## Git / GitHub

- Repo: **public** `https://github.com/NguyenGiang909/ai-writer-studio` (branch `main`)
- `gh` CLI đã cài + auth `NguyenGiang909` (scope đủ, kể cả `workflow`)
- Seed truyện thật KHÔNG public: `seed_lac_hong*.py`, `seed_vinhthanh.py` trong `.gitignore`, file vẫn nằm local; repo chỉ có `seed_demo.py` (Vĩnh Thành rút gọn 15 chương)
- Commit dùng identity inline `-c user.name/user.email` (không sửa git config)

## Stack & chạy dev

- Backend: FastAPI + SQLAlchemy async + SQLite (`backend/writer.db`) + Alembic
- Frontend: Next.js 15 + React + TS (`frontend/`)
- **Port backend: 8001** (port 8000 bị `gold-analyzer` của `D:\Trading System` chiếm — KHÔNG kill)
- `frontend/.env.local`: `NEXT_PUBLIC_API_URL=http://127.0.0.1:8001`
- Frontend: `localhost:3000`
- Start backend: `cd backend && uvicorn app.main:app --port 8001`
- Start frontend: `cd frontend && npm run dev`
- DB schema: `create_all` tự tạo bảng dev; migration chuẩn qua `backend/alembic/versions/`

## Verify

- Backend tests: `cd backend && pytest` — hiện **93 pass** (warnings deprecation: FastAPI `on_event`, `datetime.utcnow`, asyncio policy — chưa xử lý)
- Frontend: `cd frontend && npx tsc --noEmit`
- Browser test: Playwright đã cài ở `C:\Users\Admin\AppData\Local\Temp\evon-probe\` (script `node -e "..."` lái `localhost:3000`)
- Context AI preview miễn phí: `POST /api/v1/projects/{pid}/ai/context-manifest` body `{task, scene_id}` — xem manifest không tốn model call. Nút tương đương trong UI: `⌄ Ngữ cảnh được sử dụng` (RightPanel, tab Mở rộng)

## Provider AI (quan trọng)

- `model_preferences` trong `writer.db`: task `writing`, `discussion`, `revision`, `extraction`, `review`, `summarization`, `skeleton`, `expand`, `scene_expand`, `chapter_outline` → provider `kiraai` / model `deepseek-v4.1-flash`, credential `connected` — **call thật, ~57s/lần**
- Task không có preference (`chat`, `brainstorm`) → `FakeProvider` instant (settings.allow_fake_provider)
- `ModelRouter` ưu tiên: project preference > account preference > request.model > fake
- UX chậm đã vá: `AiPanel` hiện pha (dựng context → chờ model + đếm giây) và nút Hủy qua AbortController (`postJSON`/`putJSON`/`patchJSON` nhận `signal`)

## Kiến trúc AI memory (đã xây)

- `ai_turns` table (`backend/app/models/memory.py`, alembic `0016`): ghi mọi call `ai/complete` — task/scene/prompt/reply/provider
- `compose.py::_story_context`: session-turns (≤3 turn gần của scene, task ∈ MEMORY_TASKS), StorySummary non-stale theo ancestor chain, characters/canon **ranked theo relevance** (không cắt [:N] ngây), constraints cap 20 dòng, manifest `included ~Ntok [label]`/`omitted`
- `build_story_prompt` tasks: `writing/expand/scene_expand` (WRITING_SYSTEM + constraints + BRIEF), `revision`, `extraction`, `skeleton` (SKELETON_SYSTEM + open threads), `chapter_outline` (system riêng + chapter-info + open threads, output `Tên cảnh — beat`), `summarization` (tóm tắt scene → StorySummary), `discussion/chat/brainstorm` (raw prompt)
- Post-gen: `writing/expand/scene_expand/revision` có scene_id → check `restricted_appearance` trên draft → trả `issues[]`

## Đã xong gần đây

- Skeleton AI: nút `AI gợi ý` trong `SceneEditor` (Ghi chú xương cảnh), confirm trước khi ghi đè, autosave, KHÔNG qua Review/Canon — đúng "skeleton là nháp"
- Timeline: resolve UUID→tên, dịch `key=value` qua `frontend/lib/stateText.ts` (6 kiểu machine-string → VI/EN), gom `<details>` theo thực thể mặc định đóng + preview trạng thái mới nhất, `ListFilter` tự mở nhóm khi lọc, form thêm sự kiện gập lại
- Continuity check: knowledge-leak mới chỉ flag khi knower=POV hoặc có mặt trong văn + fact được nhắc; 167→18 điểm trên seed
- `ProjectModal`: fix `createPortal` — modal từng vỡ vì `backdrop-filter` trên `header.top` làm containing block cho `position:fixed`
- Chapter outline AI: nút `✦` trên chapter-row (`ManuscriptTree`) mở `ChapterOutlineModal` (portal) — model trả `Tên — beat` mỗi dòng, tick/sửa tay/bỏ tick rồi "Tạo N cảnh" → **1 request `POST .../scenes/batch` atomic** (backend tự tính `order_index = max+1`, rollback all-or-nothing)
- A3: `GET/DELETE /ai/turns` + `POST /ai/turns/prune {keep}` + card "Lịch sử AI" trên trang Memory (`AiTurnsCard` — `<details>` gập, xoá từng turn, prune giữ N mới nhất)
- A1: `POST /summaries/generate` (upsert StorySummary theo scope, nguồn: scene→prose, chapter→con summaries, arc→chapter, volume→arc+orphan chapter, story→volume+orphan) + `GET /summaries/coverage` (đếm fresh/stale/missing/skipped từng tầng + pending list có label) + `SummarizeAllCard` chạy queue frontend (progress n/N + elapsed + Dừng qua AbortController, mỗi scope 1 request → hủy được, lưu ngay)
- A4: `POST /characters/assist {name, hint}` — quét prose tìm đoạn chứa tên (≤8 đoạn ±260 ký tự), task `character_profile` trả JSON {role,summary,voice_notes,status,aliases} → `CharacterAssist` modal sửa → POST/PATCH /characters + aliases. KHÔNG tự ghi DB. Pref `character_profile`→kiraai trong writer.db
- Auto-summarize cảnh: `patch_scene` đánh stale `story_summaries` khi prose đổi; `SceneEditor` hiện tóm tắt cảnh + badge "đã cũ" + nút tóm tắt lại (task `summarization` → upsert StorySummary)

## Quy ước code

- i18n: `t(lang, "Chuỗi tiếng Việt gốc")`, key VI → value EN trong `frontend/lib/i18n.ts`. Placeholder nhiều dòng dùng `\n` escape, không viết newline thật trong string literal
- Free-text `value_text` trong StoryState/seed viết dạng `KEY_SubKey` / `VERB_args` (vd `STOLEN_BY_Ba_Mắt_Lươn`, `SEALED_Tàng_Khố`, `SECRETLY_PROTECTS_Khánh`) — dịch ở tầng display qua `stateText.ts`, KHÔNG sửa data
- UI/UX chuẩn: `.devin/skills/evon-uiux/` (app/dashboard); `.devin/skills/uxui/SKILL.md` trỏ làm authority chính, luật dự án override khi mâu thuẫn

## Backlog / hướng tiếp theo

- C+A roadmap memory: C đã xong (session turns + summaries + ranking); A = OpenAI Responses thread / Gemini chats khi cần provider giữ history thật
- Timeline nâng tiếp: toggle chế độ xem (chronology/narrative/theo thực thể), semantic translation map đầy đủ hơn
- Export/backup project, prose version history, tìm kiếm toàn cục, đọc trên mobile
- Auth thật, retrieval (embedding), Postgres migration test, Tauri packaging

## Test data / id hay dùng

- Project demo: `37269ce5-dfc9-430a-9ef2-207093354046`
- Scene test: `89d54776-b72a-462d-a51e-01ddfee5d7d4` ("Hội cầu ngư — vớt được tàn kiếm", Ch.1)
