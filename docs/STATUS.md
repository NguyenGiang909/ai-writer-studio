
# AI Writer Studio — GĐ1 Recovery M10 Status

## Recovery milestones implemented
- M1 Runtime + Manuscript
- M2 Story Database
- M3 Story Truth + Temporal contracts
- M4 Narrative Threads/Holes
- M5 AI Router + Context Budget/Manifest foundation
- M6 Writer Pipeline foundation
- M7 Story Room + Style preference foundation
- M8 After-write Suggestions + Continuity foundation
- M9 Hierarchical Long-Novel Memory + Impact/Retcon foundation
- M10 What-if Branch + Account/BYOK model routing + Settings shell

## Safety / authority invariants restored
- Project is the data boundary.
- AI generation is not Canon authority.
- Suggested changes default to not auto-applied.
- Knowledge has narrative acquisition order.
- Story time and narrative order are separate.
- Partial disclosure is represented explicitly.
- What-if merge creates AuthorDecision only; it does not mutate Canon/manuscript.
- Provider secret is server-side; public view exposes hint only.

## 2026-10 — Post-M10 hardening (dogfooded on a real 55-chapter novel)

Writer-facing features shipped since the M10 milestone, all exercised end-to-end
on a live project (~116k words) rather than unit tests alone:

- **Audit & repair**: 7 new deterministic checkers (`CANON_CONFLICT`,
  `STATE_CONFLICT`, `STATE_REGRESSION`, `LOCATION_DRIFT`, `PHASE_LEAK`,
  `MISSING_EXTRACTION`, `SCENE_NO_NARR`); `audit_findings` table (mig 0025) +
  `POST /chapters/{id}/deep-check`; `services/repair.py` — chapter insert with
  narrative-axis shift, re-extract, delete+compact; "Giữ giá trị này" conflict
  resolution; `scenes/{id}/ai-fix` with preview→apply.
- **Selection-scoped revision**: textarea selection → fragment-only AI rewrite
  (~1k prompt vs ~12k whole scene — avoids 60s gateway timeouts), preview,
  offset-verified splice, auto snapshot.
- **API capability tier**: `provider_credentials.tier` (mig 0026) —
  low/standard/strong, auto-inferred per provider (kiraai=low, major APIs=strong,
  custom=standard), user-overridable. Deep-check window sizing reads the tier
  instead of hardcoding provider names.
- **Versions / export / search / reading**: `scene_versions` with restore,
  JSON + Markdown export, full-text search with deep links, per-chapter
  reading mode, AI turn history with prune, layered summary coverage dashboard,
  `characters/assist`.
- **UX fixes from screenshot review**: no toast spam on tab switch, inline
  markdown in chat replies, draft cards preserve paragraph breaks, scroll-to-
  selection, FastAPI `on_event` → lifespan.

Test suite: **155 passed**. Known debt: `datetime.utcnow()` deprecations
(needs data migration before switching to tz-aware), KiraAI gateway can still
stall under load (retry/skip degrades gracefully).

## 2026-09-24 — Backend ↔ Frontend integration checkpoint

### Backend
- Full API surface for all persisted models is now routed under `/api/v1`:
  - manuscript (existing) + story GET list endpoints completed
  - `truth.py`: canon-facts, author-decisions, story-events, story-states (+as-of), knowledge-states (+as-of), secrets
  - `narrative.py`: threads, beats, dependencies (self-dep + 2-cycle blocked)
  - `discussion.py`: threads, messages, pin, ai-reply (503 without provider), style-preferences
  - `review.py`: suggestions list/create/approve/reject; approve materializes `canon_fact`→INFERRED and `story_event`; `auto_applied` always False
  - `memory.py`: summaries + ancestor-chain invalidate + stale backlog, retcon proposals, impact-preview (read-only)
  - `account.py`: BYOK credentials (Fernet-encrypted, hint-only views), model preferences + resolve, branches + changes + idempotent merge→AuthorDecision
  - `ai.py`: context preview w/ manifest, parse-brief, word-budget, line-diff, ai/complete (503), deterministic continuity check
- CORS enabled for `localhost:3000`.
- Provider secrets encrypted with Fernet keyed by `SECRET_KEY` env (dev default present; override in production).
- Alembic offline mode added (`upgrade head --sql` verified for 0001→0010).

### Frontend (Next.js)
- `lib/api.ts`: get/post/patch/del + ApiError.
- Visual system ported from the static demo `dist/index.html` (v14): full CSS extracted to `frontend/app/globals.css` (tokens `--ink/--paper/--panel/--line/--muted/--gold/--teal/--red`, dark theme via `html[data-theme="dark"]`, responsive shell).
- Top bar (brand mark, project switcher, search, save indicator, account shortcut, theme toggle) + 3-column shell (manuscript tree / serif editor / inspector) in the project layout; `page/dashboard/card/list-row/pill/section-label` classes used across all section pages.
- Home: project list + create.
- Workspace: manuscript tree + chapter/scene create, SceneEditor autosave (PATCH, 800ms debounce), POV/scene_type, word count, inspector.
- Screens wired to API: Story DB, Threads/Hố, Canon & Truth, Discussions (+thread), Review (suggestions + continuity), Memory (summaries/retcon), What-if Branches (+merge), Settings (credentials + model routing).
- `next@15.2.0` → `15.5.26` (CVE-2025-66478 patch).

### Verification
- Backend: **46/46 pytest passed** (SQLite in-memory).
- `compileall` clean; `alembic upgrade head --sql` produces full 0001→0010 chain.
- Frontend: `npm install` OK; `next build` OK (12 routes, typecheck passed).
- Smoke: uvicorn :8000 + `next dev` :3000 — project/chapter created via API render on home + workspace pages (HTTP 200 all screens).

### Still required before declaring GĐ1 FINAL
1. Alembic against real PostgreSQL/pgvector (no Docker in this environment).
2. Real provider E2E + retry/cost accounting (ai/complete currently 503 without configured provider).
3. After-write AI extraction pipeline (model-driven suggestions) — review surface exists, extractor pending.
4. ~~Frontend port of the richer v14 static-demo UX~~ — DONE: `globals.css` extracted verbatim from the demo; all pages on demo classes; `next build` green; smoke 200 on all routes.

## 2026-09-24 — v14 markup/behavior parity pass

- `/manuscript` response now includes `volumes` + `arcs`; workspace tree renders Volume→Arc→Chapter→Scene with status dots, POV, scene counts (chapters with missing parent arc fall back to top level).
- New `PATCH /projects/{id}/chapters/{chapter_id}` (ChapterPatch, incl. `order_index`) — verified live: valid PATCH 200, bad-id 404, cross-project 404.
- Demo behavior ported via client components: `AppBehaviors` (toast, mode toggle, tree collapse, mobile nav/AI toggles, context toggle, draft actions, tabs), `NavLink` (active state), `ThemeToggle` (localStorage `writer-theme`), `KnowledgePeek` (`knowledge-states/as-of` card), `AiPanel` (expand→`/ai/complete`, draft→Review suggestion).
- New `/timeline` page (story time vs narrative order, story states, add-event form).
- Section pages restyled to demo dashboard patterns (`.dash-head`/eyebrow, `.person`/`.avatar`, `.thread`/`.bar`, `.review-item`, `.settings-grid`, `.project-stats`).
- Sample `thanh-pho-khong-ngu.sample.json` imported: project + 3 chars + 2 locations + 1 ability + 4 chapters + 7 scenes + 3 threads + 3 pending suggestions + global style profile.
- Verified: tsc clean, `next build` green, all routes 200, chapter PATCH live-verified.

## 2026-09-24 — Second parity pass (full audit vs v14 markup+JS)

### Structure fix (was the biggest gap)
- Demo is a persistent 3-column SPA: left nav + right AI panel stay fixed, only `.main` swaps. The shell has been moved into `projects/[projectId]/layout.tsx` — `LeftNav` + `RightPanel` now persist across all section pages; pages render only `<main className="main">`.

### Backend
- `Scene.skeleton` (Text, nullable) + migration `0011` + schema fields; dev `writer.db` ALTERed. PATCH verified live.

### Components
- `ManuscriptTree` (client): demo tree — `.tree-tools` + `•••` (opens Quyển/Hồi forms), `button.tree-node-toggle` collapse, `.arc-group`, `.chapter-row` draggable (`data-chapter-id`, `data-first-scene`), `.scene-list` only under active chapter, `.tree-add` "＋ Thêm chương", title normalized ("10 · Dưới ga tàu" — no more "10 · Chương 10. …" duplication).
- `RightPanel` (client): in-panel tabs Thảo luận / Mở rộng / Kiểm tra, `context-btn` toggle (context collapsed by default), real counts.
- `ProjectModal` (client): project-switch opens modal — project grid w/ live stats, new-project form POSTs API, Esc/backdrop close, "Hiện tại" pill.
- `SaveIndicator`: "Đã lưu HH:MM", updates on `writer:saved` event from SceneEditor.
- `ProfileForm`: localStorage `writer-profile-v1`.
- `PostForm`: `triggerClass`/`triggerLabel`/`trigger` props.

### Pages
- New: `/characters` (person cards + aliases + arcs + relationships + KnowledgePeek), `/world`, `/abilities`, `/style` (demo screens), `/account` (Hồ sơ + Credit), `/timeline` from previous pass.
- `/story` slimmed to Premise + Author Decision per demo.
- `/settings` gets `.top` header; home gets `.empty-project` card.
- `SceneEditor`: head per demo (eyebrow "Cảnh x/y", h1=chapter, meta words/POV/save, Lịch sử + gold Review), status-strip pills, editable `.skeleton` block, dispatches `writer:saved`.
- `AiPanel`: 3 draft actions (Bỏ / Chèn để sửa→appends to scene prose / Chấp nhận→Review).

### Verified
- `pytest` 46/46, `tsc --noEmit` clean, `next build` green (18 routes), smoke 200 on all routes.

## 2026-09-26 — D1: provider adapter + fake provider (test UI trước khi nối model thật)

- `app/ai/providers.py`: `CompletionResult` + `BaseProvider`; `FakeProvider` (deterministic, task-aware — writing/discussion/extraction); `OpenAICompatibleProvider` (chat-completions qua httpx, base URL map `PROVIDER_ENDPOINTS` cho openai/openrouter — mở rộng thêm provider bằng cách thêm endpoint).
- `app/ai/router.py` viết lại: `ModelRouter(db)` resolve ModelPreference theo project→task→account, giải mã Fernet credential, tạo adapter thật; **fallback `FakeProvider` khi `settings.allow_fake_provider` (default True cho dev)**; không còn chế độ thì 503.
- `config.py`: thêm `allow_fake_provider: bool = True`.
- `ai/complete` + `discussions/{tid}/ai-reply` truyền db + project_id; response `/ai/complete` giờ trả `{reply, provider, model, usage}`.
- Tests: `test_ai_complete_fake_provider` (200 + provider=fake), `test_ai_complete_503_when_fake_disabled` (monkeypatch flag), `test_ai_reply_fake_provider` + `test_ai_reply_503_when_fake_disabled`. **48/48 pytest pass.**
- Smoke live: backend :8100 — `/ai/complete` trả bản nháp giả mạch Vĩnh Thành; `ai-reply` đăng message `author=ai` vào thread.
- Vẫn giữ bất biến: fake output chỉ là draft/suggestion — không auto-mutate Canon/manuscript.

## 2026-09-26 — E2: Author Brief form (scene-level)

- `Scene.brief_json` (Text) + migration `0012`; `ScenePatch.brief` (dict → JSON), `SceneOut.brief` computed từ `brief_json`. PATCH/round-trip qua manuscript tree verified live.
- `AiPanel` viết lại thành Author Brief form theo spec §18: mục tiêu, xương 5–15 dòng, số từ mục tiêu, AI freedom (Thấp/Vừa/Cao), ràng buộc (phải có / không được), quyền mystery + quan hệ, ending beat.
- Brief persist per-scene (nút "Lưu brief vào cảnh"; Expand tự lưu trước khi gọi model); prompt compose deterministic từ fields → `ai/complete`.
- Test `test_scene_author_brief_roundtrip`. **49/49 pytest pass**, tsc clean.

## 2026-09-26 — Real provider (kiraai) E2E + security pass

- `PROVIDER_ENDPOINTS` += `deepseek`, `kiraai` (base `https://kiraai.vn/api/v1`, OpenAI-compatible `/chat/completions`). Settings provider list += `kiraai`.
- Router: pref-without-credential / provider-without-endpoint → 503 rõ lỗi (không lặng lặng rớt fake); `httpx.HTTPError` bọc thành RuntimeError sạch.
- **Verified E2E**: credential `kiraai` (hint ••••418b) + prefs writing/discussion → `ai/complete` trả `provider=kiraai`, usage tokens thật.
- Fix `DiscussionMessage` thiếu `created_at` — messages trước sort theo UUID `id` (thứ tự loạn, `msgs[-20:]` lấy sai context). Migration `0013`, sort theo `created_at`.
- Security: CORS += localhost:3001; `_fernet()` refuse `dev-insecure-key-change-me` khi `environment != development`; `.gitignore` mới chặn `*.db`/`.env*`/`node_modules`. API response chỉ trả `key_hint`, `secret=None` (giữ nguyên).
- Còn lại (ghi nhận, chưa vá — phù hợp single-user local dev): không có authentication; OpenAI error detail có thể chứa metadata provider; rotate SECRET_KEY sẽ làm credential cũ không giải mã được (cần re-key/re-enter).
