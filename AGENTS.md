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

- Backend tests: `cd backend && pytest` — **162 pass**; `pytest.ini` chạy **session-scoped loop** + conftest dùng **file DB tạm** (aiosqlite conn bind đúng loop tạo nó + `:memory:` mỗi conn = DB riêng — job nền viết, request đọc → không thấy nhau)
- KHÔNG đổi lại loop-scope function hay `:memory:` — background `asyncio.create_task` sẽ chết `bound to a different event loop`
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
- `build_story_prompt` tasks: `writing/expand/scene_expand`+`chapter_write` (WRITING_SYSTEM + constraints + BRIEF), `revision`, `extraction`, `skeleton` (SKELETON_SYSTEM + open threads), `chapter_outline` (system riêng + chapter-info + **bedrock states** + open threads, output `Tên cảnh — beat`), `summarization` (tóm tắt scene → StorySummary), `discussion/chat/brainstorm` (raw prompt)
- Post-gen: `writing/expand/scene_expand/revision` có scene_id → check `restricted_appearance` trên draft → trả `issues[]`
- **Neo vị trí (m11)**: `scenes.narrative_order = chapter.order_index` (chapter-scale, gán lúc dàn cảnh + migration 0024 backfill); `canonical_state_key` gom key tự do (nơi ở→location, tuổi→age, lớp/trường→education, sinh tử→lifecycle, sở hữu→ownership); `states_at` lọc state có narrative_order > vị trí cảnh; `build_constraints` dedupe theo canonical key; `chapter_outline` có block "Hiện trạng nhân vật tại điểm này" (bedrock: tuổi/lớp/ở/lifecycle); cast_gen xin `age`/`context` → h_cast seed StoryState narr=0; chapter_facts xin `recap` → upsert StorySummary chương (0 call thêm); `h_chapter_write` (fast mode) viết cả chương 1 call, marker `### CẢNH:` parse theo tên→thứ tự, cảnh lọt → scene_write bù; `_post_write_issues` flag restricted_appearance + LOCATION_DRIFT vào step output
- Router: `TASK_PREF_FALLBACK` (chapter_write→scene_expand) tránh task mới rơi FakeProvider
- **Dàn vai chương** (`chapters.cast_json` `{"characters","threads","abilities"}`, migration 0027): console `ChapterCastPanel` — tác giả tick nhân vật có mặt + hố/năng lực đụng tới. compose: pinned char vào block Nhân vật nhãn "tác giả chọn cho chương này"; Ability inject block riêng (can_do/cannot_do/limits/cost/conditions); pinned thread → `must_respect` trong constraints + lên đầu `_open_threads_block`
- **Console "Bảng chương"** dock trong `.editor-shell` (không phải card nổi): `@media ≥1700` grid `[1fr|226px|790px|1fr]`, rail pin `grid-column:2` sát mép trái editor + `sticky;top:72`. Sticky trong .main chỉ chạy nhờ `.main{overflow:visible clip}` — `overflow-x:hidden` cũ nuốt scroll-context (`clip` không tạo scroll container, vẫn chặn tràn ngang). KHÔNG làm cột .shell thứ 4 — từng thử: trang `/authoring` render `.page` (không phải `.main`) nên pin column trượt, vỡ 68px. Rail gồm 3 section: DÀN VAI (chips đã chọn + nhóm tick), CẢNH (list cảnh chương, click `?scene=`), NHẬT KÝ (`/ai/turns` lọc scope chương, fallback project khi rỗng, poll 20s). `<1700px` fallback `variant="inline"` trong editor
- **Repair workflow (sửa sau khi viết xong)**: `services/repair.py` — `shift_narrative` dời trục narrative đồng bộ (chapters + scenes.narrative_order + states/events/beats/knowledge/summaries/thread.payoff + canon.valid_from/to); `wipe_chapter_extractions` xoá facts trích của 1 chương theo provenance AI (giữ facts tác giả/locked); `delete_chapter_full` xoá chương+scenes+versions+facts rồi khép trục. `extract_chapter_facts(db,pid,ch,run=None)` — tách từ h_chapter_facts, standalone gọi router trực tiếp vẫn ghi provenance+AiTurn. Endpoints: `POST /chapters/insert {title,order_index}` chèn chương giữa mạch, `POST /chapters/{id}/reextract` trích lại sau khi sửa prose, `DELETE /chapters/{id}?compact=` khép lỗ. `POST scenes` có order_index đụng giữa → đẩy sibling lên (chèn cảnh bổ sung). Review UI: nút "Trích lại dữ kiện chương" + "＋ Chương sau" trong ChapterDeepCheck
- Audit dò lỗi: `/continuity/check` deterministic (CANON/STATE_CONFLICT, STATE_REGRESSION, LOCATION_DRIFT, PHASE_LEAK, MISSING_EXTRACTION, SCENE_NO_NARR + cũ) → resolve subject_id→tên entity trước khi group conflict, chỉ flag predicate đơn-trị, bỏ near-dup; `POST /chapters/{id}/deep-check` AI soi cả chương → `audit_findings` (migration 0025); `POST /scenes/{id}/ai-fix` revision có preview→apply qua PATCH prose (auto-snapshot scene_versions); nút "Giữ giá trị này" trên conflict → REJECTED/xoá bản còn lại

## Đã xong gần đây

- **Audit dò lỗi toàn project** (pid-scoped → mọi dự án): `/continuity/check` thêm 7 checker — CANON_CONFLICT (subject resolve về entity, predicate đơn-trị, bỏ near-dup), STATE_CONFLICT (cùng vị trí narr), STATE_REGRESSION (tuổi/lớp lùi, num_from parse số chữ VI), LOCATION_DRIFT (prose nhắc Location ∉ skeleton∪state), PHASE_LEAK (location/item nhắc trước narr đầu tiên), MISSING_EXTRACTION, SCENE_NO_NARR. Evidence `options:[{value,ids}]` → nút "Giữ giá trị này" (fact→REJECTED / xoá state) + nút "AI sửa" (POST `/scenes/{id}/ai-fix` → preview textarea → PATCH prose, auto-snapshot scene_versions)
- **AI soi chương**: `POST /chapters/{id}/deep-check` task `review` → JSON issues; bảng `audit_findings` (migration 0025) + GET/DELETE; UI `ChapterDeepCheck` trên trang Review (dropdown chương, progress, findings persist)

- Skeleton AI: nút `AI gợi ý` trong `SceneEditor` (Ghi chú xương cảnh), confirm trước khi ghi đè, autosave, KHÔNG qua Review/Canon — đúng "skeleton là nháp"
- Timeline: resolve UUID→tên, dịch `key=value` qua `frontend/lib/stateText.ts` (6 kiểu machine-string → VI/EN), gom `<details>` theo thực thể mặc định đóng + preview trạng thái mới nhất, `ListFilter` tự mở nhóm khi lọc, form thêm sự kiện gập lại
- Continuity check: knowledge-leak mới chỉ flag khi knower=POV hoặc có mặt trong văn + fact được nhắc; 167→18 điểm trên seed
- `ProjectModal`: fix `createPortal` — modal từng vỡ vì `backdrop-filter` trên `header.top` làm containing block cho `position:fixed`
- Chapter outline AI: nút `✦` trên chapter-row (`ManuscriptTree`) mở `ChapterOutlineModal` (portal) — model trả `Tên — beat` mỗi dòng, tick/sửa tay/bỏ tick rồi "Tạo N cảnh" → **1 request `POST .../scenes/batch` atomic** (backend tự tính `order_index = max+1`, rollback all-or-nothing)
- A3: `GET/DELETE /ai/turns` + `POST /ai/turns/prune {keep}` + card "Lịch sử AI" trên trang Memory (`AiTurnsCard` — `<details>` gập, xoá từng turn, prune giữ N mới nhất)
- A1: `POST /summaries/generate` (upsert StorySummary theo scope, nguồn: scene→prose, chapter→con summaries, arc→chapter, volume→arc+orphan chapter, story→volume+orphan) + `GET /summaries/coverage` (đếm fresh/stale/missing/skipped từng tầng + pending list có label) + `SummarizeAllCard` chạy queue frontend (progress n/N + elapsed + Dừng qua AbortController, mỗi scope 1 request → hủy được, lưu ngay)
- A4: `POST /characters/assist {name, hint}` — quét prose tìm đoạn chứa tên (≤8 đoạn ±260 ký tự), task `character_profile` trả JSON {role,summary,voice_notes,status,aliases} → `CharacterAssist` modal sửa → POST/PATCH /characters + aliases. KHÔNG tự ghi DB. Pref `character_profile`→kiraai trong writer.db
- Auto-summarize cảnh: `patch_scene` đánh stale `story_summaries` khi prose đổi; `SceneEditor` hiện tóm tắt cảnh + badge "đã cũ" + nút tóm tắt lại (task `summarization` → upsert StorySummary)
- B1: `GET /projects/{pid}/export?format=json|markdown` — JSON dump toàn bộ bảng project-scoped (không gồm credentials/usage) + `.md` bản thảo Quyển→Hồi→Chương→Cảnh; link `Sao lưu (.json)` / `Bản thảo (.md)` trong LeftNav mục Cá nhân (thẻ `<a download>` thẳng API)
- B2: bảng `scene_versions` (migration 0017) — `patch_scene` snapshot prose cũ khi đổi, gom burst-edit <90s thành 1 checkpoint; `GET versions` (excerpt 160c + chars) / `GET versions/{id}` (full prose) / `POST versions/{id}/restore` (force-snapshot hiện tại trước, đánh stale summaries). `SceneHistory` modal nút "Phiên bản" trong SceneEditor
- B3: `GET /projects/{pid}/search?q=` — cảnh(chapter+prose+skeleton)/chương/nhân vật(+alias)/canon/thread/event/location, snippet ±90c quanh match; `TopSearch` client comp (Enter → `/search?q=`), trang `search/page.tsx` group theo loại + link sâu (scene/chapter→`?scene=`, char→/characters, canon→/truth…)
- B4: `TimelineView` client comp — segmented `.mode` switch Hai trục/Theo thời gian/Theo thứ tự kể bọc 3 list dựng sẵn từ server
- B5: `/projects/{pid}/read?chapter=` — reading mode theo chương, `.read-wrap` 720px + prev/next + `ChapterSelect` dropdown, responsive ≤760px; nav item "Đọc lại" trong LeftNav

## Quy ước code

- i18n: `t(lang, "Chuỗi tiếng Việt gốc")`, key VI → value EN trong `frontend/lib/i18n.ts`. Placeholder nhiều dòng dùng `\n` escape, không viết newline thật trong string literal
- Free-text `value_text` trong StoryState/seed viết dạng `KEY_SubKey` / `VERB_args` (vd `STOLEN_BY_Ba_Mắt_Lươn`, `SEALED_Tàng_Khố`, `SECRETLY_PROTECTS_Khánh`) — dịch ở tầng display qua `stateText.ts`, KHÔNG sửa data
- UI/UX chuẩn: `.devin/skills/evon-uiux/` (app/dashboard); `.devin/skills/uxui/SKILL.md` trỏ làm authority chính, luật dự án override khi mâu thuẫn

## Đợt vá m10-fix (migration 0028 — chi tiết `docs/BIEN_BAN_VAN_HANH.md` mục F)

- **Hard-stop**: `next_step` trả sentinel `__target_done__` khi `len(chapters) ≥ target_chapters`; `arc_chapters` clamp theo ngân sách còn lại. `__wave_pause__` tương tự + `wave_paused_for` chống bắn lặp
- **`pause_after_wave` là cờ BỀN** (không tự reset); đặt được `running`+`awaiting_review` qua POST pause-after-wave hoặc `PATCH /authoring/run` (target/wps/call_mode/goal_mode sửa giữa run, engine đọc mỗi tick)
- **AuditJob** (`audit_jobs`): deep-check chapter/range → POST trả `job_id` ngay, `_spawn_job` GIỮ STRONG-REF task (create_task không ref = GC hủy), `_reap_stale_job` (>8ph running → failed, chống mồ côi chặn dedupe); GET `/audit/jobs/{id}` poll progress/result
- **KiraAI**: non-stream bị gateway cắt ~60s → mọi call qua `_complete_streaming` (SSE, gộp delta); `read=120.0` phát hiện stream câm; `_PROVIDER_SEM=Semaphore(2)` trong router giới hạn tranh call
- **Cast chương**: `PUT /chapters/{id}/cast` validate id cùng project (422 liệt kê), KHÔNG PATCH cast_json trần
- **AuditFinding** dismiss/reopen: `status`+`dismiss_key`; deep-check lọc issue trùng motif đã dismiss
- `ai_turns.latency_ms` + reply cap **20000**; `compose` auto-inject `abilities.owner_character_id` theo nhân vật có mặt; checker mới `LOCATION_DRIFT/PHASE_LEAK/TITLE_CONTENT_DRIFT/FACT_DRIFT`; thread extraction auto-`RESOLVED` khi có beat payoff + dedupe theo title chuẩn hoá

## Đóng gói (package/)

- Plan + checklist: `docs/KE_HOACH_DONG_GOI.md`. Build: `powershell -ExecutionPolicy Bypass -File package\build_package.ps1`
- Kiến trúc: `writer-api.exe` (PyInstaller `backend/writer-api.spec`, desktop_main → ENVIRONMENT=production, port **8765**, DB+secret `%LOCALAPPDATA%/AIWriterStudio`) + `node.exe web\server.js` (Next standalone, port **3300**, `NEXT_PUBLIC_API_URL=…:8765` bake lúc build)
- Copy chuẩn: `.next/standalone/*` → `web/`; **phải copy tay** `.next/static` → `web/.next/static` và `public/` (standalone không chứa — bản 6/10 thiếu → server.js chết "no production build")
- `allow_fake_provider` prod default **False** (dev/test True); `/health` trả `build_id` (build_id.txt cạnh exe) + environment
- `ensure_schema()` lo nâng cấp SQLite (create_all + ALTER ADD COLUMN) — cột mới phải nullable
- **D1 Tauri** (`package/tauri/`): shell Rust spawn sidecar (port-probe tái dùng, không trùng), splash→navigate :3300, tray Mở/Thoát (X=ẩn tray), Exit→kill con. Build `npx tauri build` → NSIS ~65MB currentUser + MSI. Node sidecar cần env PORT=3300 HOSTNAME=127.0.0.1. `.gitignore` mở `package/` cho source, vẫn ignore binary/target/gen
- `.ps1` phải **ASCII-only hoặc UTF-8 BOM** — PS5.1 đọc no-BOM là ANSI, em-dash `—`/dấu tiếng Việt vỡ parse

## Style memory — Novel Humanizer v3 (migration 0030)

- `style_preferences` mở rộng thành style-rule đầy đủ: `strength` (HARD/PREFERRED/AVOID/OPEN), `status` (candidate→confirmed→rejected/superseded), `source` (explicit/approved_edit/observed_edit/inferred/preset), `attribute`, `scope_type`+`scope_id`, `evidence`, `supersedes_id`
- `services/style.py`: scope resolution (scene/chapter/character/arc/global — rule override thắng scope profile), `render_style_block` chỉ trả rule **confirmed** khớp scope; profile chứa "AI tự học" tạo lười
- `compose.py::_style_section` inject block "Gu văn tác giả" vào `_STYLE_TASKS` (writing/expand/revision/humanize/skeleton/chapter_outline…) — manifest `included style-rules: N`
- Routes `api/routes/style.py`: `GET/POST/PATCH/DELETE /projects/{pid}/style-rules`, `POST …/learn` (`{instruction}`→confirmed | `{original,revised,comment?}`→task `style_learn` trích CANDIDATES), `GET …/style/presets`, `POST …/style/import-preset` (AI trích đề xuất, KHÔNG ghi) + `POST …/style/apply-preset` (ghi phần tác giả chọn — idempotent theo name/pattern/predicate+value)
- Task mới: `humanize` (làm mượt không đổi sự kiện — chip "✎ Làm tự nhiên" trong AiPanel gọi thẳng), `style_learn`, `preset_import`; router fallback: humanize→revision, style_learn/preset_import→extraction
- Deep-check 5-gate (A hard/B story/C style/D prose/E regression) + severity blocker/major/minor/intentional + evidence/counter/suggestion + `coverage` (FULL_TEXT/HYBRID_100_PERCENT_INDEX/PARTIAL + coverage_note) — ChapterDeepCheck render gate pill + coverage line
- Preset `backend/presets/quan-net-di-gioi.md` — chỉ áp khi tác giả chọn, pid-scoped không rò project khác
- Anti-overfitting: candidates chờ duyệt (manifest bỏ qua), rejected không gợi lại, provenance giữ qua superseded
- Frontend: `StyleRulesPanel` trên trang Phong cách (list 3 nhóm + Dạy gu + Học từ diff + Import preset modal chọn phần áp); `severityLabel/strengthLabel/scopeLabel/styleStatusLabel` trong labels.ts

## Backlog / hướng tiếp theo

- C+A roadmap memory: C đã xong (session turns + summaries + ranking); A = OpenAI Responses thread / Gemini chats khi cần provider giữ history thật
- Timeline nâng tiếp: group/filter theo thực thể cho events, semantic translation map đầy đủ hơn
- Auth thật, retrieval (embedding/FTS — `func.lower(col).like` chỉ case-fold ASCII, chưa normalize dấu; search hiện word-boundary regex ở tầng Python), Postgres migration test, Tauri packaging

## Test data / id hay dùng

- Project demo: `37269ce5-dfc9-430a-9ef2-207093354046`
- Scene test: `89d54776-b72a-462d-a51e-01ddfee5d7d4` ("Hội cầu ngư — vớt được tàn kiếm", Ch.1)
