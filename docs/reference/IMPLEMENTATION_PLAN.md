# AI Writer Studio — Implementation Plan

> Mục tiêu: phát triển dần một **Writer-first Story OS** cho tiểu thuyết dài. Tác giả quyết định cốt truyện; AI hỗ trợ thảo luận, mở rộng bản thảo, ghi nhớ, rà soát và phát hiện mâu thuẫn.
>
> Nguyên tắc triển khai: **mỗi milestone phải chạy được, có test và được xác minh trước khi sang milestone kế tiếp**. Không đóng gói ZIP lại sau từng thay đổi nhỏ; chỉ đóng gói ở mốc lớn hoặc khi được yêu cầu.

---

## 0. Nguyên tắc bất biến của dự án

### 0.1 Writer-first
- Author là nguồn quyền lực cao nhất.
- AI không được tự thay đổi Canon, Author Decision, Knowledge State hay trạng thái Hố/Thread quan trọng.
- AI có thể: đề xuất, viết nháp, phân tích, phản biện, phát hiện xung đột.
- Mọi thay đổi quan trọng do AI tạo ra phải đi qua `Suggestion -> Review -> Approve/Reject`.

### 0.2 Story data là nguồn nhớ dài hạn, không phải chat history
- Database lưu Story Canon, Characters, World, Abilities, Threads, Timeline, Author Decisions, Story State.
- Chat chỉ là workspace để suy nghĩ.
- Context Builder lấy đúng dữ liệu truyện liên quan rồi mới gọi model.

### 0.3 Mở sẵn đường cho truyện 500–1.000+ chương
Ngay từ MVP phải giữ:
- stable IDs;
- project scope;
- revision metadata;
- source reference tới chapter/scene/event;
- module boundaries rõ;
- không overwrite những dữ liệu sau này cần history nếu có thể tránh.

Không cần triển khai toàn bộ temporal/versioning ở MVP, nhưng schema và service layer không được khóa đường mở rộng.

### 0.4 Modular monolith trước
Ban đầu:
- 1 Next.js web app;
- 1 FastAPI backend;
- 1 PostgreSQL + pgvector;
- 1 Redis/worker khi bắt đầu có background jobs.

Chưa dùng microservice, Neo4j hay multi-agent thật sự nếu chưa có nhu cầu thực tế.

---

# GIAI ĐOẠN A — NỀN TẢNG CHẠY ĐƯỢC

## Milestone A0 — Chuẩn hóa repo và môi trường phát triển

### Mục tiêu
Repo clone/xả ra là có thể chạy backend, frontend và database bằng quy trình rõ ràng.

### Việc thực hiện
- Chuẩn hóa `.env.example`.
- Hoàn thiện `docker-compose.yml` cho PostgreSQL/pgvector và Redis.
- Backend config theo environment.
- SQLAlchemy async + Alembic.
- Health endpoint.
- Logging/error envelope cơ bản.
- Frontend cấu hình Next.js/TypeScript thật sự chạy được.
- API client cơ bản.
- Lint/test scripts.

### Test/Acceptance
- `docker compose up` chạy database.
- FastAPI `/health` trả OK.
- Frontend chạy và gọi được `/health`.
- Unit test đầu tiên chạy thành công.

### Không làm ở bước này
- Login/auth đầy đủ.
- AI API.
- UI đẹp.

---

## Milestone A1 — Persistence Core + Project

### Mục tiêu
Tạo được một project truyện và lưu/retrieve ổn định.

### Domain
- `Project`
- Project settings cơ bản: title, description, genre, language, status.

### Backend
- SQLAlchemy model.
- Pydantic schemas.
- Repository/service/router.
- Alembic migration.
- CRUD API.

### Frontend
- Trang danh sách Project.
- Tạo project.
- Mở project workspace.

### Test/Acceptance
- CRUD project qua API.
- Project A không truy cập nhầm dữ liệu Project B.
- UI tạo/mở project được.

---

## Milestone A2 — Manuscript Core: Volume / Arc / Chapter / Scene

### Mục tiêu
Có thể dùng app như một editor truyện cơ bản trước khi có AI.

### Domain
- `Volume`
- `Arc`
- `Chapter`
- `Scene`
- `Revision` mức tối thiểu.

### Quy tắc
- Scene là đơn vị nội dung nhỏ nhất mà AI xử lý.
- Chapter có thể chứa nhiều scene.
- Content không trộn với Story Canon.

### Backend
- CRUD hierarchy.
- Ordering/reorder.
- Autosave endpoint.
- Revision metadata.

### Frontend
- Left tree: Volume/Arc/Chapter/Scene.
- Center editor.
- Autosave.
- Word count.

### Test/Acceptance
- Tạo 2 volume, nhiều arc/chapter/scene.
- Reorder không mất dữ liệu.
- Refresh browser không mất nội dung.
- Revision cơ bản được ghi nhận.

---

# GIAI ĐOẠN B — STORY DESIGN CHO NGƯỜI VIẾT

## Milestone B1 — Story Design / Cốt truyện chính

### Mục tiêu
Người viết xây được khung tác phẩm nhưng không bị ép phải hoàn thiện toàn bộ từ đầu.

### Domain
- premise;
- main conflict;
- main goal;
- planned ending;
- story notes;
- arc intent;
- start/end state dự kiến của arc.

### UI
- Trang `Story`.
- Các field có thể để trống.
- Scratchpad riêng, không coi là Canon/Plan.

### Acceptance
- Author có thể ghi khung sơ lược và chỉnh dần.
- Scratchpad không bị AI/logic hệ thống coi là sự thật.

---

## Milestone B2 — Characters

### Mục tiêu
Quản lý nhân vật đủ tốt cho việc viết trước, chưa cần temporal state phức tạp.

### Domain
- identity;
- aliases/titles;
- role/importance tier;
- appearance;
- background;
- personality;
- values;
- desires/fears;
- character arc;
- voice notes;
- current notes.

### Thiết kế mở
Tách rõ:
- `CharacterProfile`: nhân vật là ai;
- `CharacterState`: nhân vật hiện tại thế nào (sẽ làm sâu ở V1).

### Acceptance
- Tìm/search nhân vật.
- Alias không tạo duplicate đơn giản.
- Character có thể link tới chapter/scene liên quan sau này.

---

## Milestone B3 — World / Bối cảnh

### Domain ban đầu
- Location
- Faction/Organization
- Item
- Lore/Rule

### Mục tiêu
Không tạo form quá cứng. Dùng core fields + flexible metadata.

### Acceptance
- Tạo/đọc/sửa entity.
- Liên kết entity với Project.
- Chuẩn bị sẵn generic Story Entity ID hoặc entity references để các module khác liên kết.

---

## Milestone B4 — Abilities / Kỹ năng đặc biệt

### Domain
- Ability/Skill/Technique/Method.
- owner/users.
- description.
- can_do.
- cannot_do.
- limitations.
- costs.
- conditions.
- counters.
- progression/stages (schema mở, UI tối thiểu).

### Mục tiêu
Dùng cho cả:
- tu tiên/pháp thuật;
- trinh thám/suy luận;
- giải mộng/chiêm đoán;
- kỹ năng nghề nghiệp;
- sci-fi/fantasy.

### Acceptance
- Author định nghĩa được ranh giới năng lực.
- Dữ liệu đủ để checker sau này phát hiện AI cho nhân vật làm điều năng lực không cho phép.

---

## Milestone B5 — Style Engine dữ liệu

### Domain
- `StyleProfile`
- `StyleSample`
- `StylePreference`

### Scope chuẩn bị sẵn
- global;
- arc;
- POV;
- character;
- scene type.

### Nội dung
- POV/narrator;
- sentence rhythm;
- description density;
- dialogue rules;
- internal monologue;
- preferred/avoid/banned expressions;
- sample type: dialogue/combat/description/emotion/etc.

### Acceptance
- Author tạo profile.
- Upload/paste văn mẫu.
- Có thể chọn văn mẫu theo type.
- Chưa cần tự động style analysis ở milestone này.

---

# GIAI ĐOẠN C — NARRATIVE CONTROL

## Milestone C1 — Hố truyện / Story Threads

### Domain
`StoryThread` với type:
- Mystery
- Foreshadow
- Promise
- Conflict
- Secret
- Question
- Quest
- Future Payoff
- Custom

Status:
- Open
- Dormant
- Planned
- Resolved
- Abandoned

### Thread beats
- Setup
- Reinforcement
- Escalation
- Misdirection
- Payoff

### Dữ liệu quan trọng
- introduced_at;
- author_intent;
- planned_payoff;
- related entities;
- related chapters/scenes;
- notes.

### Acceptance
- Tạo Hố từ UI.
- Gắn vào chapter/scene/character.
- Chưa ép phải có payoff.
- Có dashboard Open/Dormant/Resolved.

---

## Milestone C2 — Timeline cơ bản

### Domain
- Story Event.
- story order/time.
- narrative chapter/scene occurrence.
- participants.
- location.

### UI
- Event list.
- Story timeline đơn giản.
- Character-filtered timeline.

### Thiết kế mở
Chuẩn bị cho:
- narrative timeline;
- concurrent timeline;
- relative time;
- temporal state sau này.

### Acceptance
- Event có stable ID.
- Một event link được nhiều entity.
- Có thể lọc events của một character.

---

## Milestone C3 — Canon + Author Decisions

### Canon
Phân biệt tối thiểu:
- CANON
- INFERRED
- PLANNED
- RUMOR
- REJECTED

### Author Decision
Lưu:
- decision;
- reason/intent;
- alternatives rejected;
- related entities/threads/arcs;
- status: confirmed/superseded/revoked.

### Mục tiêu
Chat/thảo luận không tự biến thành Canon.

### Acceptance
- Chỉ Author hoặc service được phép approve mới tạo Canon/Decision.
- Có source/provenance.
- Có audit cơ bản.

---

# GIAI ĐOẠN D — AI STORY ROOM

## Milestone D1 — Model Provider Interface + Model Router

### Mục tiêu
Không hardcode một nhà cung cấp AI.

### Interface chung
- chat/generate;
- streaming;
- structured output;
- token/cost metadata;
- capability metadata.

### Provider đầu tiên
Triển khai một provider thật trước; provider khác dùng adapter sau.

### Router
Task classes:
- discussion;
- writing;
- extraction;
- summarization;
- review.

### Acceptance
- Fake provider dùng trong tests.
- Thay model/provider không đổi business modules.
- Secret/API key chỉ nằm server-side.

---

## Milestone D2 — Discussion Sessions giống chatbot

### Domain
- DiscussionSession
- DiscussionMessage
- DiscussionSummary
- PinnedItem
- WorkingMemory
- linked_entities

### Context mỗi lượt
1. system role;
2. relevant Story Context;
3. pinned decisions;
4. conversation summary;
5. recent raw messages;
6. current user message.

### Role UI ban đầu
- Brainstorm
- Plot Doctor
- Character Analyst
- Continuity Analyst
- Devil's Advocate
- Reader Simulation
- Style discussion

Các role có thể dùng cùng model, khác prompt/context policy.

### Acceptance
- Nói chuyện 30+ lượt vẫn liên hệ được vấn đề cũ qua summary + recent messages.
- “Phương án thứ hai lúc nãy” vẫn resolve được trong recent window.
- Pin được ý quan trọng.
- Chat idea không tự ghi Story DB.

---

## Milestone D3 — Discuss with AI trên từng module

### Điểm gọi
- Story plot
- Character
- World
- Ability
- Thread/Hố
- Timeline
- Style

### Mục tiêu UX
AI đi theo nơi tác giả đang làm việc, không bắt tác giả copy context sang một chatbot chung.

### Acceptance
- Từ Character page mở discussion có Character context tự động.
- Từ Thread page có Thread + related events/entities.
- User có thể `Pin`, `Save as Plan`, `Propose Canon`.

---

# GIAI ĐOẠN E — WRITER AI: 5–15 DÒNG -> 1.000–3.000 TỪ

## Milestone E1 — Context Builder v1

### Mục tiêu
Đây là lõi kỹ thuật quan trọng nhất của AI layer.

### Input
- task;
- project;
- target scene/chapter;
- author instruction;
- token budget.

### Context buckets
- author input;
- story/arc plan;
- characters present;
- relevant world/abilities;
- relevant canon/decisions;
- relevant threads;
- style profile;
- style samples;
- recent manuscript;
- retrieved historical material.

### Yêu cầu
- Có trace/debug view cho biết context nào đã được chọn.
- Có priority và token budget theo bucket.

### Acceptance
- Unit tests cho context selection.
- Không gửi toàn bộ Story Bible mặc định.
- Có thể giải thích AI được cấp những gì.

---

## Milestone E2 — Author Intent Parser / Expansion Plan

### Input
5–15 dòng tự nhiên của Author.

### Structured result
- required beats;
- desired ending;
- tone;
- forbidden outcomes;
- unknowns AI không được tự quyết;
- AI freedom;
- estimated scene structure;
- word budget.

### Quy tắc
Không tự tạo quyết định plot cấp cao.

### Acceptance
- 10 dòng đầu vào -> expansion plan hợp lý.
- Phân biệt `must happen` và `may invent`.
- Có chế độ Low/Medium/High AI Freedom; Writer mode mặc định Low.

---

## Milestone E3 — Chapter/Scene Expansion

### Pipeline
Author notes
-> Intent Parser
-> Expansion Plan
-> Context Builder
-> Writer
-> Draft

### Writer constraints
AI được phép phát triển:
- prose;
- dialogue;
- movement;
- sensory detail;
- micro-actions;
- transitions.

AI mặc định không được tự quyết:
- major reveal;
- identity secret;
- death;
- new major power;
- canonical relationship change;
- thread resolution;
- major world rule.

### Acceptance
- Generate 1.000–3.000 từ theo target.
- Không bỏ beat bắt buộc.
- Không vượt ending state rõ ràng.
- Streaming vào editor hoặc preview.
- Author có thể accept toàn bộ hoặc từng phần sau này.

---

# GIAI ĐOẠN F — MEMORY V1

## Milestone F1 — Suggested Changes Framework

### Mục tiêu
Tạo một cổng duy nhất cho mọi dữ liệu AI muốn đề xuất vào Story DB.

### SuggestedChange
- type;
- payload;
- source scene/message;
- confidence;
- reasoning summary;
- status: pending/approved/rejected.

### Acceptance
- AI không gọi repository Canon/State trực tiếp.
- Approve/reject có audit.

---

## Milestone F2 — After-write Extraction

### Sau khi scene được Author xác nhận/save
AI đề xuất:
- important events;
- entity mentions/new entities;
- potential new canon facts;
- relationship changes;
- new/open/resolved thread;
- item/ability changes;
- knowledge changes.

### Acceptance
- Extraction không tự update Canon.
- Review UI theo batch.
- Author có thể sửa suggestion trước khi approve.

---

## Milestone F3 — Current Story State v1

### State tối thiểu
- character current location/status;
- physical notes;
- current goals;
- inventory/current item holder;
- current ability stage;
- important current relationships.

### Acceptance
- State được cập nhật từ approved change.
- Before-write context lấy current state.
- Chưa cần full temporal query ở bước này.

---

## Milestone F4 — Knowledge State v1

### States
- KNOWS
- BELIEVES
- SUSPECTS
- DOES_NOT_KNOW
- FALSE_BELIEF

### Subjects
- characters;
- Reader như virtual subject nếu cần.

### Acceptance
- Writer context cho POV character không vô tình cấp knowledge bị cấm nếu policy yêu cầu.
- Có thể xem “Ai biết gì về fact X?”.

---

# GIAI ĐOẠN G — REVIEW / CONTINUITY

## Milestone G1 — Before-write Briefing

Khi mở chapter/scene, sinh brief từ dữ liệu thật:
- current location;
- present characters;
- current state;
- active relevant threads;
- knowledge restrictions;
- ability/item warnings;
- previous scene summary.

Không cần AI cho mọi field; ưu tiên query deterministic.

---

## Milestone G2 — Review Pipeline v1

Checker tách riêng:
- Canon conflict;
- Knowledge leakage;
- Ability rules;
- Timeline basic;
- Thread boundary;
- Character voice;
- Style rules.

### Output
Warnings, không auto rewrite.

### Acceptance
- Mỗi warning có source/evidence.
- Ignore/accept/fix suggestion.
- Không trộn review với Canon mutation.

---

## Milestone G3 — Style Review

### Chức năng
- compare với Style Profile;
- retrieve đúng sample theo scene type;
- banned/preferred expressions;
- character voice;
- style drift cơ bản.

### UX
Diff/annotation thay vì chỉ trả một bản “improved”.

---

# GIAI ĐOẠN H — TRUYỆN SIÊU DÀI

## Milestone H1 — Hierarchical Summaries + Retrieval

Hierarchy:
- Scene summary
- Chapter summary
- Arc summary
- Volume summary
- Story summary

### Quy tắc
Summary không phải Canon.

### Retrieval
- pgvector cho prose/notes/discussions;
- structured DB cho facts/state/threads.

### Acceptance
- Truyện giả lập hàng trăm chapter vẫn build context không phải nhét toàn bộ manuscript.

---

## Milestone H2 — Temporal State / History

Mở rộng current state thành history:
- valid_from_event;
- valid_to_event;
- query `state_at(chapter/event)`.

Áp dụng dần cho:
- character state;
- relationship;
- item ownership;
- ability progression;
- faction/world state;
- knowledge.

### Acceptance
- Hỏi trạng thái một nhân vật ở chương 100 và chương 300 trả khác nhau đúng lịch sử.

---

## Milestone H3 — Snapshot

Snapshot theo checkpoint chapter/arc:
- current state;
- open threads;
- important knowledge;
- world state.

Dùng để:
- recovery;
- context speed;
- impact analysis.

---

## Milestone H4 — Retcon + Impact Analysis

### Retcon
- old fact;
- new fact;
- reason;
- effective point.

### Impact Analyzer
Kết hợp:
- structured dependencies;
- references;
- semantic search;
- AI reasoning.

### Output
Danh sách downstream chapters/events/threads/decisions có thể bị ảnh hưởng.

### Quy tắc
Không auto sửa hàng loạt.

---

## Milestone H5 — Reader Memory / Dormancy

Theo dõi:
- last character appearance;
- last meaningful appearance;
- last thread reinforcement;
- dormant duration;
- reader-likely-memory heuristic.

Mục đích:
- gợi ý tái giới thiệu nhẹ;
- cảnh báo payoff quá xa setup mà không reinforcement.

---

# GIAI ĐOẠN I — ADVANCED PLANNING

## Milestone I1 — What-if / Branches

- Base story không đổi.
- Branch lưu overrides/proposals.
- AI phân tích hệ quả.
- Merge chỉ sau Author approval.

Use cases:
- “Nếu giết nhân vật X ở chương 320 thì sao?”
- so sánh hai hướng plot mà chưa chốt.

---

## Milestone I2 — Advanced timelines

- concurrent character/faction timelines;
- information travel delay;
- geography/travel time;
- flashback/narrative timeline;
- story-time validation.

---

## Milestone I3 — Long-novel analytics

Chỉ cung cấp dữ liệu, không phán xét văn chương:
- thread open/resolution rate;
- arc length planned vs actual;
- state-change density;
- repeated scene/motif similarity;
- cast explosion/dormancy;
- power scale/ability usage history.

---

# 1. Thứ tự triển khai thực tế đề nghị

Không làm song song tất cả. Thứ tự coding:

1. A0 Repo/runtime.
2. A1 Project.
3. A2 Manuscript editor.
4. B1 Story Design.
5. B2 Characters.
6. B3 World.
7. B4 Abilities.
8. B5 Style data.
9. C1 Threads/Hố.
10. C2 Timeline/events.
11. C3 Canon/Decisions.
12. D1 Model Router/provider.
13. D2 Discussion memory.
14. D3 Contextual Discuss-with-AI.
15. E1 Context Builder.
16. E2 Intent/Expansion Plan.
17. E3 AI Expand chapter.
18. F1 Suggestion framework.
19. F2 After-write extraction.
20. F3 Story State.
21. F4 Knowledge.
22. G1 Before-write brief.
23. G2 Continuity review.
24. G3 Style review.
25. H1 Hierarchical memory/retrieval.
26. H2 Temporal state.
27. H3 Snapshot.
28. H4 Retcon/impact.
29. H5 Reader memory.
30. I1+ Advanced features.

---

# 2. Quy tắc cho mỗi coding increment

Mỗi increment nên nhỏ, ví dụ:
- thêm 1 model + migration;
- thêm repository/service;
- thêm API;
- thêm UI;
- thêm test.

Không viết một lúc cả module lớn mà chưa chạy.

Trước khi đánh dấu một increment hoàn thành phải:
1. chạy test liên quan;
2. chạy lint/type-check nếu đã thiết lập;
3. kiểm tra migration;
4. kiểm tra API contract;
5. nếu có UI, test luồng cơ bản;
6. cập nhật `docs/STATUS.md`.

---

# 3. Definition of Done cho một module

Một module chỉ được coi là “done ở version hiện tại” khi có:
- domain model/schema;
- migration nếu có persistence;
- repository/service tách khỏi router;
- validation;
- API contract;
- permission/project scoping tối thiểu;
- unit test core logic;
- integration test happy path quan trọng;
- frontend flow nếu module cần UI;
- docs ngắn cho hành vi đặc biệt.

---

# 4. Những thứ chủ động trì hoãn

Không làm sớm nếu chưa có bằng chứng cần thiết:
- microservices;
- graph database riêng;
- Kubernetes;
- multi-agent orchestration phức tạp;
- automatic rewrite toàn manuscript;
- tự động mutate Canon;
- quá nhiều metrics/analytics;
- mobile app native;
- collaboration multi-user real-time;
- marketplace prompt/model.

---

# 5. Các quyết định kiến trúc phải giữ trong suốt quá trình

1. `Project` là boundary dữ liệu chính.
2. Scene là đơn vị prose nhỏ nhất cho AI pipeline.
3. Event là đơn vị thay đổi story-state quan trọng.
4. Canon/Plan/Inference/Rumor không được trộn.
5. Discussion idea không phải Story truth.
6. AI-generated structured changes đi qua Suggestions.
7. Context selection phải traceable.
8. Structured facts ưu tiên database; semantic retrieval ưu tiên manuscript/notes.
9. Long-term state cần đường nâng cấp thành temporal history.
10. Model/provider phải thay thế được mà Story Memory không bị mất.

---

# 6. Mốc đóng gói dự án

Không tạo ZIP sau từng increment.

Chỉ nên đóng gói khi đạt một trong các mốc:
- **Checkpoint 1:** A0–A2 — editor cơ bản chạy được.
- **Checkpoint 2:** B1–C3 — quản lý tác phẩm đầy đủ ở mức MVP.
- **Checkpoint 3:** D1–E3 — AI Discussion + AI Expand dùng được.
- **Checkpoint 4:** F1–G3 — Story Memory + Review V1.
- **Checkpoint 5:** H1–H5 — nền tảng truyện siêu dài.

Hoặc khi Author yêu cầu bản trung gian.

---

# 7. Milestone kế tiếp để bắt đầu code

**Bắt đầu với Milestone A0 — Chuẩn hóa repo/runtime.**

Thứ tự nhỏ trong A0:
1. kiểm tra/cập nhật package manifests;
2. backend settings + DB session;
3. Alembic setup;
4. health endpoint;
5. PostgreSQL/pgvector Docker;
6. frontend Next.js bootstrapping;
7. frontend gọi health endpoint;
8. basic test/lint scripts;
9. verify toàn bộ local stack;
10. cập nhật STATUS.

Sau khi A0 verified mới sang A1 Project persistence.
