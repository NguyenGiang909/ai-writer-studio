# AI Writer Studio — Roadmap 10 Giai Đoạn Phát Triển

## Mục tiêu tổng thể
Xây dựng một **Writer-first Story OS** cho tiểu thuyết dài:
- Tác giả quyết định cốt truyện.
- AI hỗ trợ triển khai câu chữ, thảo luận, rà soát và ghi nhớ.
- Canon, Story State, Knowledge, Thread/Hố và các thay đổi quan trọng chỉ cập nhật sau khi tác giả xác nhận.
- Hệ thống hướng tới truyện hàng trăm đến 1.000+ chương.

## Giai đoạn 1 — Runtime + Manuscript Core
Mục tiêu: ứng dụng chạy được từ frontend đến backend và lưu được bản thảo.
- FastAPI backend
- Next.js + React + TypeScript
- PostgreSQL + pgvector
- Redis/worker
- Docker Compose
- Alembic
- Project → Volume → Arc → Chapter → Scene
- Editor cơ bản
- Project isolation

Đầu ra: tạo project, chương, scene, viết/lưu prose, mở workspace.

## Giai đoạn 2 — Story Database
Mục tiêu: tạo bộ nhớ cấu trúc của tác phẩm.
- Character
- Alias
- Character Arc
- Location
- Faction
- Item
- World Entity
- Ability
- Relationship
- Style Profile
- Style Sample

Nguyên tắc: stable ID, project scope, không cross-project reference.

## Giai đoạn 3 — Story Truth + Temporal Engine
Mục tiêu: biến truyện thành hệ thống trạng thái có lịch sử theo thời gian.
- Canon Fact
- Author Decision
- Story Event
- Story State
- Knowledge State
- Secret
- Character lifecycle
- Item ownership history
- Relationship history
- Ability progression history
- Historical snapshot

Nguyên tắc cốt lõi: **Narrative Order ≠ Story Time**.

Đầu ra: có thể hỏi tại thời điểm X nhân vật còn sống không, biết gì, đang ở đâu, có ability gì, item thuộc về ai.

## Giai đoạn 4 — Narrative Engine / Hố truyện
Mục tiêu: theo dõi các nghĩa vụ kể chuyện còn treo.
- Thread / Hố
- Thread Beat
- Thread Dependency
- Narrative Debt
- Planned Payoff
- Secret Reveal
- Reader Knowledge

Trạng thái:
- OPEN
- DORMANT
- PLANNED
- RESOLVED
- ABANDONED

Beat:
- SETUP
- REINFORCEMENT
- MISDIRECTION
- ESCALATION
- PAYOFF

App chỉ nhắc, không ép tác giả phải xử lý Hố.

## Giai đoạn 5 — AI Foundation + Context Builder
Mục tiêu: AI nhận đúng context từ hệ thống thay vì “tự nhớ”.
- Model Router
- Provider abstraction
- Prompt registry
- Retrieval
- Context Builder
- Token budget
- Context Manifest
- Context Preview

Context có thể gồm:
- Author Brief
- Current Scene
- Current Story State
- POV Knowledge
- Relevant Characters
- Abilities
- Threads
- Canon
- Author Decisions
- Style
- Recent prose
- Hierarchical summaries
- Historical context

## Giai đoạn 6 — Writer Pipeline
Workflow cốt lõi:
**Tác giả viết 5–15 dòng → AI triển khai thành 1.000–3.000 từ.**

Pipeline:
Author Brief → Intent Parser → Beat Plan → Plot Boundary Manifest → Context Builder → Generate → Draft → Review

Thành phần:
- Beat extraction
- Constraint extraction
- Target length
- AI Freedom
- POV
- Style
- Word-budget allocation
- Multi-scene generation
- Partial rewrite
- ORIGINAL vs SUGGESTED diff

AI không được tự invent major plot, death, resurrection, secret, ability, payoff, Canon hoặc knowledge transition lớn nếu tác giả chưa cho phép.

## Giai đoạn 7 — Story Room + Style Engine
Mục tiêu: AI trở thành cộng sự thảo luận có memory nhưng không làm bẩn Canon.

Story Room:
- Discussion threads
- Recent chat
- Discussion summary
- Working memory
- Pins
- Relevant Story Memory

Vai trò:
- Brainstorm
- Plot Doctor
- Character Analyst
- Continuity Analyst
- Devil’s Advocate
- Reader Simulator
- Style Editor

Action:
- Pin
- Save as Idea
- Save as Plan
- Make Decision
- Propose Canon

Style Engine:
- Global/Arc/POV/Character/Scene style
- Preferred/Avoid/Banned patterns
- Style samples
- Style drift
- Explicit author feedback

## Giai đoạn 8 — After-write + Continuity Engine
Mục tiêu: sau khi viết xong, phát hiện thay đổi và lỗi continuity.

Pipeline:
Scene → Extractor → Suggested Changes → Author Review → Approve/Edit/Reject → Story Database

Extract:
- Entity
- Event
- Knowledge
- Relationship
- Item ownership
- Ability progression
- Thread/Hố

Continuity Checker:
- nhân vật đã chết lại xuất hiện vật lý
- nhân vật biết điều chưa được biết
- ability chưa học nhưng đã dùng
- item ở sai người
- location/travel vô lý
- lifecycle conflict
- Thread contradiction
- timeline conflict
- POV leak

AI không trực tiếp ghi Canon/Story State.

## Giai đoạn 9 — Long Novel Engine
Mục tiêu: giữ hệ thống ổn định khi truyện lên hàng trăm hoặc hàng nghìn chương.

Hierarchical Memory:
Scene Summary → Chapter Summary → Arc Summary → Volume Summary → Story Summary

Thành phần:
- Summary invalidation
- Bounded rebuild
- Reader Memory
- Cast Dormancy
- Narrative Debt
- Arc Health
- Repetition Candidates
- Identity continuity
- Impact Analysis
- Retcon Manager
- Historical Snapshot
- Temporal retrieval

Nguyên tắc: summary không phải source of truth; structured Story Database mới là source of truth.

## Giai đoạn 10 — What-if + Account/BYOK + Production Readiness
Mục tiêu: hoàn thiện GĐ1 thành sản phẩm có thể sử dụng thật.

What-if:
- Branch
- Branch Change
- Impact Preview
- Compare A/B
- Merge selected plan

Merge What-if chỉ tạo Author Decision, không tự sửa Canon/manuscript.

Account:
- Profile
- AI Providers
- API keys / BYOK
- Model Preferences
- Usage & Cost
- Writing Defaults
- Data/Export
- Security

Model routing:
Task override → Project setting → Account default → System fallback

Provider:
- OpenAI
- Anthropic
- Gemini
- OpenRouter
- Custom/OpenAI-compatible
- Local

Production hardening:
- Full pytest
- PostgreSQL migration test
- Frontend typecheck
- Next.js production build
- Real AI provider E2E
- Retry/error handling
- Cost tracking
- End-to-end tests
- Final OpenAPI validation
- Final source ZIP

## Sau GĐ1
### GĐ2 — AI Writing Intelligence
Scene/Chapter Planner, pacing, dialogue, emotion/tension, setup-payoff, subtext, hook, deep prose review.

### GĐ3 — Story Architect
Plan toàn truyện, volume/arc strategy, character arcs, reveals, climax, dependency planning.

### GĐ4 — Simulation Intelligence
What-if simulation sâu và consequence propagation.

### GĐ5 — Writer OS Ecosystem
Multi-project, version control, collaboration, export DOCX/EPUB/PDF/Markdown, desktop/mobile companion.
