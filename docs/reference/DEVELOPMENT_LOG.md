# AI Writer Studio — Development Log

Nhật ký này ghi các checkpoint triển khai đủ lớn để có thể quay lại/đối chiếu. Không dùng để ghi từng chỉnh sửa nhỏ.

## Checkpoint 2026-09-22 — Baseline audit / A0 backend foundation

### Đã xác minh
- FastAPI app import được và `/health` đã có contract test.
- SQLAlchemy metadata cấu hình được đầy đủ; hiện có 38 bảng ORM.
- Alembic migration chain `0001` → `0009` sinh SQL thành công.
- Backend test suite hiện tại: **12/12 passed**.
- `scripts/verify.sh` chạy thành công cho compileall, pytest, ORM mapper và Alembic static upgrade.
- PostgreSQL/pgvector, Redis, MinIO, API, worker và web đã có cấu hình trong `docker-compose.yml`.

### Giới hạn môi trường tại checkpoint
- `ruff`/`mypy` không được cài trong runtime hiện tại nên chưa chạy lint/type-check Python bằng các tool này.
- Frontend chưa có `node_modules`; lần `npm install` trong runtime hiện tại bị timeout, vì vậy chưa xác minh `next build`/`tsc` tại checkpoint này.

### Quy tắc tiếp tục
- Không viết lại module đã tồn tại chỉ vì STATUS cũ chưa phản ánh đúng.
- Tăng độ phủ test quanh các invariants quan trọng: project scoping, authority của Author, knowledge visibility, AI suggestion approval, writer plot-boundary.
- Mỗi nhóm thay đổi có ý nghĩa phải chạy `scripts/verify.sh` trước khi đánh dấu hoàn tất.

## Checkpoint 2026-09-22 — Integrity + Writer boundaries + knowledge-safe context

### Thay đổi chính
- Thêm project-scoped reference helpers cho record ngoài `StoryEntity`.
- Siết cross-project references ở Discussion, Author Decision, Thread/Thread Beat, Timeline Event và AI Suggestion approval.
- Sửa AI Suggestion source handling: chỉ suggestion nguồn `scene` mới được ghi `source_scene_id`; discussion ID không còn có thể lọt vào Scene FK.
- Knowledge suggestion phải tham chiếu CanonFact cùng project; `entity:<id>` phải là entity cùng project.
- Discussion prompt có `MEMORY AUTHORITY` rõ ràng: confirmed Author Decision/Canon > project data > pin/working memory > summary/chat > AI inference.
- Lỗi memory compaction không còn làm thất bại một chat reply đã commit.
- Writer Expansion Plan có Plot Boundary Manifest, allowlist theo `AI freedom` và protected story layers.
- Word budget của beats được phân bổ đúng tổng `target_words`.
- Context Builder tách `KNOWS` khỏi `SUSPECTS/BELIEVES/FALSE_BELIEF`; hidden truth không còn đi vào CANON chỉ vì POV nghi ngờ.
- Context Builder tự nhận diện entity được nhắc bằng name/alias, lấy participant/location từ scene events và thêm `CURRENT STORY STATE` cho entity liên quan.

### Xác minh
- Backend tests: **30/30 passed**.
- ORM: **38 tables** configure thành công.
- Alembic `0001` → `0009`: static upgrade SQL thành công.
- `scripts/verify.sh`: pass toàn bộ phần khả dụng trong runtime.

### Chưa giải quyết ở checkpoint này
- Frontend typecheck/build vẫn chưa xác minh vì runtime không có npm dependencies và không có network để cài.
- Chưa có live PostgreSQL integration test trong runtime.

## Checkpoint 2026-09-22 — Temporal state + thread lifecycle + retrieval/briefing

### Thay đổi chính
- Thêm `StoryStateService` để quản transition theo thời gian thay vì mutate trực tiếp trong SuggestionService.
- Chặn state transition đi ngược `valid_from_order`; back-dated change phải đi Retcon/branch.
- Thêm partial unique index `uq_story_state_current` qua migration `0010`: chỉ một current state cho mỗi project/entity/state_type.
- Historical `state_at` không còn trả closed timeless rows; temporal history được ưu tiên hơn current fallback không có mốc.
- Thêm `ThreadService`, PATCH thread, status enum và kiểm tra chapter/scene cùng project + cùng chapter.
- Hierarchical summary retrieval ưu tiên lexical relevance trước, specific scope sau, có scope diversity.
- `Before-write briefing` lấy previous scene theo narrative order, arc info, recent events, relevant entity state, related threads và knowledge focus thay vì dump toàn project.

### Xác minh
- Backend tests: **41/41 passed**.
- ORM: **38 tables** configure thành công.
- Alembic `0001` → `0010`: static upgrade SQL thành công.
- `scripts/verify.sh`: pass toàn bộ phần khả dụng trong runtime.

## Session save 2026-09-22 — User requested checkpoint before continuing

- Repository state preserved in place; no ZIP export.
- Verified checkpoint remains: **41/41 backend tests passed**, ORM **38 tables**, Alembic **0001 → 0010** static upgrade valid.
- Resume point: **After-write extraction + continuity hardening**.
- Immediate next work: reference-aware extraction catalog, payload normalization/validation, grouped after-write report, and tests proving no direct Canon/Story State mutation.

## Checkpoint 2026-09-22 — Reference-safe after-write extraction

### Thay đổi chính
- Extraction prompt nhận stable reference catalog theo scene.
- Payload AI phải qua structural normalization **và** catalog validation trước khi thành `SuggestedChange`.
- Hallucinated entity/thread/fact IDs bị loại trước persistence.
- New thread provenance (`introduced_scene_id/chapter_id`) do server gắn, không tin model output.
- AI-extracted Canon luôn hạ xuống `INFERRED`, `author_only`, `locked=false`; author mới có quyền promote.
- Story-state extraction không được tự điều khiển `valid_from/valid_to`, source event/scene hay current flag.
- Thêm author-facing After-write report (`by_type`, review priority, protected changes, `auto_mutations=0`).

### Xác minh
- Backend tests: **51/51 passed**.
- ORM: **38 tables**.
- Alembic `0001` → `0010`: static SQL pass.

## Checkpoint 2026-09-22 — Persisted POV + deterministic continuity

### Thay đổi chính
- Scene lưu `pov_subject_key` (`entity:<character_id>` hoặc `narrator`) qua migration `0011`.
- Writer tự dùng POV đã lưu của scene nếu request không truyền POV mới.
- Reviewer thêm knowledge-boundary warning cho hidden Canon mà POV chưa `KNOWS`.
- Reviewer thêm thread/payoff consistency warning.
- Reviewer thêm temporal location-state vs scene event-location warning.
- After-write endpoint trả cả Suggestions + deterministic warnings + report counts.
- Reviewer vẫn `auto_mutations=0`; không sửa prose/Canon/State.

### Xác minh
- Backend tests: **57/57 passed**.
- ORM: **38 tables**.
- Alembic `0001` → `0011`: static SQL pass.

## Checkpoint 2026-09-22 — Idempotent After-write + author-approved event lifecycle

### Thay đổi chính
- Scene lưu `last_extraction_hash` qua migration `0013` để After-write analysis idempotent kể cả khi extractor trả 0 suggestions.
- Pending suggestions cùng content hash được reuse; cùng content đã phân tích xong không gọi model lại; `force=true` mới chủ động re-analyze.
- Pending suggestions cũ của scene bị `superseded` khi một analysis mới thành công.
- After-write report tách `protected_truth`, `narrative_control`, `informational` và đếm pending/status rõ ràng.
- AI-extracted `story_event` không được tự gán `story_order`/`world_time_minutes`; scene/chapter provenance do server sở hữu.
- Author-approved Story Event được gắn provenance trong `event_data`.
- Author-approved `thread_status=resolved` từ scene tự ghi `resolved_chapter_id` và PAYOFF beat nếu chưa có; reopen sẽ bỏ current resolution marker nhưng giữ lịch sử beat.

### Xác minh
- Backend tests: **62/62 passed**.
- ORM: **38 tables**.
- Alembic `0001` → `0013`: static SQL pass.
- `auto_mutations=0` ở After-write review: AI vẫn không trực tiếp thay Canon/State/Thread lifecycle.

## Checkpoint 2026-09-22 — Continuity dashboard + Narrative Debt + Reader Memory baseline

### Thay đổi chính
- Thêm Continuity Dashboard deterministic ở cấp project, không gọi model và không mutate dữ liệu.
- Dashboard tổng hợp pending protected suggestions, Hố/payoff lệch lifecycle, hidden Canon chưa có knowledge tracking, event thiếu story order, scene có nội dung nhưng chưa khai POV và mức phủ After-write.
- Thêm Narrative Debt monitoring cho truyện dài: tuổi Hố theo lần reinforce gần nhất, Hố quan trọng chưa có payoff plan, Hố chưa từng reinforce, PAYOFF chưa resolve và net-opened trong cửa sổ chương gần đây.
- Thêm Reader Memory / Cast Dormancy heuristic dựa trên khoảng cách exposure của nhân vật qua StoryEvent, không tuyên bố mô phỏng trí nhớ con người thật.
- Reader Memory phân biệt lần xuất hiện gần nhất và lần hành động có ý nghĩa gần nhất; đưa tín hiệu tái giới thiệu nhẹ khi nhân vật quay lại sau quãng dài.
- Analytics router đã có endpoint continuity, narrative-debt, cast-dormancy, similar-character-names và repetition candidates.

### Xác minh
- Backend tests: **72/72 passed**.
- ORM: **38 tables** configure thành công.
- Alembic `0001` → `0013`: static upgrade SQL thành công.
- `scripts/verify.sh`: pass toàn bộ phần khả dụng trong runtime.

### Resume point
- Tiếp tục harden **Reader Memory / Cast Dormancy** cho tình huống truyện vài trăm–nghìn chương.
- Sau đó nối tín hiệu reintroduction vào Before-write briefing nhưng chỉ dưới dạng advisory, tuyệt đối không tự chèn exposition vào prose.

## Session save 2026-09-22 — Before Reader Memory hardening continuation

- User requested an explicit save before continuing; repository remains in-place, no ZIP export.
- Re-verified actual repository baseline: **80/80 backend tests passed**, ORM **39 tables**, Alembic **0001 → 0014** static upgrade SQL valid.
- `0014_identities` and temporal `CharacterIdentity` support already exist; do not duplicate that work.
- Resume target: harden Reader Memory against sparse event logging and distinguish an explicit character return in the target chapter from mere contextual/recent-event relevance.
- Planned slice: separate target-return entity hints from general context entities, add manuscript-mention fallback/provenance where deterministic, keep all reader-memory outputs advisory-only.

## Session save 2026-09-22 — 6-minute checkpoint cadence requested

- User requested: save, continue, and while this active session runs, checkpoint work about every ~6 minutes before continuing.
- No ZIP export; repository remains the source of truth.
- Verified baseline at save: **80/80 backend tests**, ORM **39 tables**, Alembic **0001 → 0014** static SQL valid.
- Resume target remains: harden Reader Memory / Cast Dormancy, then wire advisory reintroduction cues into Before-write briefing without mutating prose.
- Checkpoint cadence is an in-session working discipline, not a background automation.

## Checkpoint 2026-09-22 — Reader Memory hardening + manuscript exposure fallback

### Thay đổi chính
- Reader Memory không còn coi nhân vật là `first_introduction_candidate` chỉ vì thiếu StoryEvent; reader-visible manuscript mention cũng được tính là exposure.
- Cast Dormancy dashboard dùng nguồn exposure mới nhất giữa StoryEvent và manuscript mention, có `exposure_basis` rõ ràng.
- Matching tên/alias dùng boundary-aware regex để tránh false positive kiểu `Lan` nằm trong `Lantern`; alias 1 ký tự bị bỏ qua.
- Before-write target hints có thể nhận các CharacterIdentity đang active tại chapter hiện tại, không chỉ canonical name/StoryEntity aliases.
- Reader-memory signal vẫn advisory-only; không mutate Canon, Knowledge hay prose.

### Xác minh
- Backend tests: **85/85 passed**.
- Repo chưa đóng ZIP; checkpoint lưu trực tiếp trong source tree.

### Resume point
- Identity/alias continuity: temporal labels, reveal-gated identities và tránh leak tên thật cho POV/reader trước thời điểm reveal.

## Checkpoint 2026-09-22 — Identity Continuity analytics

### Thay đổi chính
- Thêm deterministic `IdentityContinuityService` và endpoint `/analytics/identity-continuity`.
- Rà reader-visible Scene prose để phát hiện temporal label dùng trước `valid_from_order` hoặc sau `valid_to_order`.
- Nếu identity bị gate bởi secret fact và reader KNOWS fact tại một source event xác định, cảnh báo label xuất hiện trước reader reveal.
- Kết quả chỉ advisory; không mutate identity, Knowledge, Canon hay prose.

### Xác minh
- Backend tests: **89/89 passed**.
- Reader Memory/Cast Dormancy + identity continuity đều giữ nguyên nguyên tắc author-controlled.

### Resume point
- Long-novel character continuity: lifecycle/status contradictions (dead/exited/missing/archived vs later appearance), then re-entry context.

## Checkpoint 2026-09-22 — Character lifecycle continuity

### Thay đổi chính
- Thêm `/analytics/character-continuity` để rà lifecycle dài hạn từ `StoryStateEntry.state_type=character_status`.
- Event participation sau trạng thái dead/exited/missing là strong review signal.
- Prose mention sau trạng thái đó chỉ là review signal vì có thể là flashback, ký ức hoặc lời thoại.
- Không tự kết luận contradiction và không mutate state/prose.

### Xác minh
- Backend tests: **94/94 passed**.
- `scripts/verify.sh` trước slice này: ORM 39 tables, Alembic `0001→0014` valid.

### Resume point
- Temporal Knowledge State/history: prevent future knowledge leaking into flashbacks or historical chapter regeneration.

## Checkpoint 2026-09-22 — Temporal Knowledge State foundation

### Thay đổi chính
- `KnowledgeState` chuyển từ single mutable row thành temporal history với `is_current`, `valid_from_order`, `valid_to_order`.
- Migration `0015_temporal_knowledge` bỏ unique cũ và tạo partial unique index cho current knowledge per project/subject/fact.
- Thêm `KnowledgeService.set_current/current/at`, đóng range cũ khi transition mới và chặn back-date phải đi Retcon/branch.
- AI Suggestion approval không overwrite knowledge cũ; tạo transition mới.
- Context Builder, Before-write briefing, Identity visibility và POV reviewer đọc knowledge `as of` chapter order thay vì future current state.
- Knowledge API mặc định trả current, có `include_history` và `at_order`.
- Snapshot current path chỉ lấy current knowledge.

### Xác minh
- Backend tests: **98/98 passed**.
- ORM: **39 tables**.
- Alembic `0001 → 0015`: static upgrade SQL valid.

### Known limitation
- `valid_*_order` là narrative/chapter order v1. Flashback có story-time khác chapter order cần scene-level story-time anchor riêng, không overload field này.

### Resume point
- Temporal consumers: historical snapshots and reveal-order analytics; then scene story-time anchor design.

## Checkpoint 2026-09-22 — Temporal relationship/item/ability invariants

### Thay đổi chính
- HistoryService chuyển sang append-only transition semantics thay vì bulk-close mù.
- Relationship transition key gồm source/target/relation_type; item ownership theo item; ability progression theo character+ability.
- Chặn `valid_from_order` sai kiểu, transition thiếu order khi đã có state mở, và back-dated transition phải đi Retcon/branch.
- Source StoryEvent được validate cùng project; AbilityUsage event reference cũng được validate.
- Prose/history không bị auto rewrite.

### Xác minh
- Backend tests: **102/102 passed**.

### Resume point
- Server-owned temporal anchoring for AI suggestions from a Scene, then surface current/as-of relationship/item/ability state into Context Builder.

## Checkpoint 2026-09-22 — Ability context leak hardening + pause save

### Thay đổi chính
- Context Builder không còn đưa toàn bộ Ability của project vào POV writing context.
- POV context chỉ nhận ability gắn với nhân vật/ability thực sự liên quan đến scene và lấy progression đúng theo mốc chương.
- Discussion mode không POV vẫn có thể xem phạm vi rộng hơn để phục vụ worldbuilding/brainstorm.
- Temporal relationship/item/ability history vẫn giữ invariant append-only, chặn back-date và dùng server-owned provenance.
- Không có thay đổi nào cho phép AI tự mutate Canon, Knowledge, Thread lifecycle hoặc prose.

### Xác minh
- Backend tests: **104/104 passed**.
- ORM baseline: **39 tables**.
- Latest migration chain hiện có: `0001 → 0015`.
- Repo vẫn là source of truth; **không đóng ZIP** tại checkpoint này.

### Pause point / Resume point
- Tạm dừng theo yêu cầu người dùng tại đúng mốc sau khi chặn Ability context leak.
- Khi tiếp tục: rà các consumer temporal còn lại và thiết kế `scene story-time anchor` riêng cho flashback/history, không overload `chapter/narrative order`.
- Sau đó tiếp tục long-novel continuity theo checklist, ưu tiên as-of state cho relationship/item/ability và historical snapshots.


## Checkpoint 2026-09-22 — Historical Snapshot as-of semantics

### Thay đổi chính
- `SnapshotService` không còn mặc định lấy Current Story State/Knowledge khi tạo snapshot cho một chapter cũ.
- Snapshot `checkpoint_type=chapter` tự resolve `story_order` từ `Chapter.order_index` nếu caller không truyền rõ.
- Story State và Knowledge được đọc bằng `as-of` query tại checkpoint order.
- Bổ sung `HistoryService.relationships_at`, `item_ownership_at`, `ability_progression_at`; snapshot lưu cả ba domain temporal này tại đúng mốc.
- Snapshot manual/không có temporal anchor vẫn giữ current Story State/Knowledge và không giả lập history cho relationship/item/ability khi không biết mốc.
- Chưa thêm scene story-time anchor; chapter/narrative order vẫn được giữ tách biệt với story/world time.

### Xác minh
- `scripts/verify.sh`: **105/105 backend tests passed**.
- ORM: **39 tables**.
- Alembic `0001 → 0015`: static upgrade SQL valid.
- Frontend typecheck vẫn skip vì `node_modules` chưa có trong runtime hiện tại.

### Resume point
- Thiết kế `scene story-time anchor` riêng cho flashback/history.
- Sau đó rà các temporal consumer còn lại và quyết định API contract cho snapshot theo narrative-time vs story-time.

## Checkpoint 2026-09-22 — Scene Story-Time Anchor + flashback-aware Story State

### Thay đổi chính
- Scene có `story_order_anchor`, `world_time_minutes_anchor`, `story_time_label` riêng; không overload `Chapter.order_index`.
- Migration `0016_scene_story_time` thêm anchor/index cho Scene.
- Thêm `StoryTimeResolver`: trả đồng thời narrative/chapter order và in-world story/world-time, ưu tiên explicit Scene anchor và chỉ fallback sang earliest Scene Event khi thiếu.
- `StoryStateService.at_story_order()` tái dựng mutable state theo chronology thật từ StoryEvent/Scene anchors; tuyệt đối không dùng narrative `valid_from_order` như story-time.
- Context Builder dùng story-time state khi Scene có story anchor; nếu không có mới dùng historical chapter order/current fallback.
- Thêm `TEMPORAL ANCHOR` context bucket để model biết hai time axis là độc lập.
- Revision snapshot của Scene lưu cả ba story-time fields.

### Xác minh
- Backend tests: **110/110 passed**.
- ORM: **39 tables**.
- Alembic `0001 → 0016`: static upgrade SQL valid.
- Frontend typecheck vẫn skip vì runtime chưa có `node_modules`.

### Known limitation / Resume point
- Knowledge/identity/ability/item/relationship temporal consumers vẫn chủ yếu dùng narrative/chapter order; chưa được phép coi A4 là full flashback safety.
- Bước tiếp theo: A5 flashback-aware Knowledge, sau đó regression matrix cho Knowledge/Ability/Item/Relationship trong flashback.

## Checkpoint 2026-09-22 — Flashback-aware Knowledge

### Thay đổi chính
- `KnowledgeState` lưu `source_scene_id` để knowledge transition từ After-write/author approval có provenance tới Scene.
- Migration `0017_knowledge_scene` thêm FK/index cho source scene.
- `KnowledgeService.at_story_order()` tái dựng KNOWS/SUSPECTS/BELIEVES/FALSE_BELIEF theo in-world chronology từ source StoryEvent hoặc Scene story anchor.
- Context Builder ưu tiên story-time knowledge cho POV khi scene có story anchor; future chapter knowledge không còn tự động lọt vào flashback.
- Restricted/reveal-gated identity lookup có thể dùng `knowledge_story_order`, nên tên thật/bí danh bí mật không bị mở chỉ vì flashback nằm trong chapter muộn.
- Story-time knowledge vẫn giữ timeless current row làm fallback chỉ khi cùng fact không có transition được neo chronology.

### Xác minh
- Backend tests: **114/114 passed**.
- ORM: **39 tables**.
- Alembic `0001 → 0017`: static upgrade SQL valid.

### Resume point
- A6: source-anchor + story-time reconstruction cho relationship/item/ability histories.
- Sau đó regression matrix: chapter 500 flashback phải không thấy future ability/item ownership/relationship state.

## Checkpoint 2026-09-22 — Flashback-safe temporal histories (A6)

### Thay đổi chính
- RelationshipState, ItemOwnership, AbilityProgression lưu `source_scene_id` bên cạnh source_event.
- Migration `0018_history_scene` thêm FK/index cho ba temporal history tables.
- HistoryService có story-order reconstruction riêng cho relationship/item/ability; chọn transition gần nhất trước scene story anchor và bỏ future transition.
- Suggestion approval luôn lưu Scene provenance cho temporal changes; explicit `valid_from_order` của caller không bị overwrite.
- Context Builder Ability Progression dùng story-time history khi scene có `story_order_anchor`, tránh future upgrade lọt vào flashback.
- Relationship/item story-time helpers đã có và test-covered; chưa dump bừa vào Writer context để tránh lộ inventory/relationship không liên quan.

### Xác minh
- Backend tests: **118/118 passed**.
- ORM: **39 tables**.
- Alembic `0001 → 0018`: static upgrade SQL valid.
- Frontend typecheck vẫn skip vì runtime chưa có `node_modules`.

### Resume point
- Nhóm B: scene-level snapshot semantics và World/Character lifecycle snapshot.
- Sau đó có thể nối relationship/item context theo relevant-entity policy, không dump toàn project.
