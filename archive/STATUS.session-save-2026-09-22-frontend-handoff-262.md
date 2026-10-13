# AI Writer Studio — Development Status

## Current phase
Incremental implementation and verification.

## Active checkpoint
**Backend Core V1 complete through Group Q: What-if sandbox/preview/compare/explicit merge verified. Next: frontend handoff + end-to-end integration.**

## Verified baseline
- [x] Initial repository skeleton created.
- [x] High-level architecture documented.
- [x] MVP → V4 roadmap drafted.
- [x] Detailed incremental implementation plan created.
- [x] Backend environment/config layer exists.
- [x] Async SQLAlchemy session layer exists.
- [x] Alembic is configured.
- [x] Health endpoint exists and is contract-tested.
- [x] Docker Compose includes PostgreSQL/pgvector, Redis, MinIO, API, worker and web.
- [x] ORM metadata configures successfully (**47 tables** at current checkpoint).
- [x] Alembic chain `0001` → `0033` produces upgrade SQL successfully.
- [x] Backend test suite passes (**262/262** at current checkpoint).
- [x] Project/manuscript/story-design/character/world/ability/style/thread/timeline/canon/decision/discussion modules exist in backend.
- [x] Story-state/knowledge/suggestion/snapshot/retcon/branch/history/jobs/analytics foundations exist in backend.
- [x] Context Builder, AI router, discussion, writer, extraction, reviewer and summary foundations exist.
- [x] Continuity Dashboard is deterministic and read-only.
- [x] Narrative Debt monitoring exists for long-running open threads.
- [x] Reader Memory / Cast Dormancy baseline exists with exposure-distance heuristics.
- [x] Temporal Knowledge State/history prevents future knowledge from leaking into old chapter regeneration.
- [x] Basic Next.js pages/components exist for primary Writer-first workflows.

## Verification gaps
- [ ] Frontend TypeScript check (`node_modules` unavailable in current runtime; install attempt timed out).
- [ ] Frontend production build verification.
- [ ] Python Ruff lint in current runtime (`ruff` not installed).
- [ ] Python mypy in current runtime (`mypy` not installed).
- [ ] Live PostgreSQL integration migration/API test (static migration + SQLite metadata smoke are verified).

## Recently completed
- [x] Cross-project reference integrity hardening.
- [x] AI Suggestion source/reference safety.
- [x] Discussion memory authority + compaction resilience.
- [x] Writer Plot Boundary Manifest.
- [x] POV knowledge leak prevention for suspects/beliefs/false beliefs.
- [x] Relevant entity resolution + Current Story State context.
- [x] Idempotent After-write extraction and author-approved event lifecycle.
- [x] Persisted POV + deterministic continuity checks.
- [x] Project-level Continuity Dashboard.
- [x] Narrative Debt / stale Hố monitoring.
- [x] Reader Memory / Cast Dormancy baseline.

- [x] Reader Memory manuscript-exposure fallback and boundary-aware alias matching.
- [x] Identity/alias continuity analytics.
- [x] Character lifecycle continuity advisories.
- [x] Temporal Knowledge State/history with as-of reads.
- [x] Temporal relationship/item/ability invariants.
- [x] POV Ability context leak prevention.
- [x] Historical snapshots resolve Story State, Knowledge, relationships, item ownership and ability progression as-of chapter order.
- [x] Scene Story-Time Anchor + resolver keeps narrative and in-world chronology separate.
- [x] Context Builder resolves Story State by in-world story order for anchored flashback/history scenes.
- [x] POV Knowledge and reveal-gated identity knowledge resolve by in-world story order for anchored flashbacks.
- [x] Relationship/item/ability histories persist Scene provenance and can reconstruct by in-world story order.
- [x] Writer Ability Progression excludes future upgrades in anchored flashback scenes.
- [x] Scene snapshots resolve story-time vs narrative-time without conflating the axes.
- [x] Snapshot schema persists narrative/story/world-time coordinates independently.
- [x] Mutable World State is separated from static World definitions in snapshots.
- [x] Character lifecycle, item ownership, relationships and ability progression snapshot at the resolved checkpoint.
- [x] Story Event creation is centralized in EventService with conservative chronology handling.
- [x] Event provenance is first-class (author / AI-approved / imported / derived / legacy).
- [x] Event participant roles are normalized into structured rows while retaining legacy participant IDs.
- [x] Event consequences reuse SuggestedChange and require author approval before state mutation.
- [x] Deterministic Event continuity checks cover coordinate, terminal lifecycle and stable-location conflicts.
- [x] Thread lifecycle keeps resolution markers consistent when reopening/abandoning.
- [x] Structured payoff planning supports Arc and chapter windows without forcing an exact chapter.
- [x] Thread dependency graph supports ordering/dependency relations and blocks hard cycles.
- [x] Narrative Debt recognizes structured payoff plans and scene-derived beat chapters.
- [x] Impact Analyzer propagates Thread dependencies downstream and surfaces affected beats.
- [x] Structured payoff-before/payoff-after windows have deterministic conflict/review detection.
- [x] Secret entities wrap Canon facts without duplicating story truth.
- [x] KnowledgeState supports partial disclosure (`disclosure_level`, `known_aspects`) for characters and reader.
- [x] Secret reveals create temporal Knowledge transitions with event/scene provenance.
- [x] Partial `KNOWS` never leaks the full hidden Canon fact into Writer context.
- [x] Knowledge-boundary reviewer treats partial knowledge as partial and respects flashback story-time.
- [x] Deterministic Secret Continuity advisories exist for reveal metadata and reader disclosure state.

- [x] Context Builder V2 central priority policy per task (Writer vs Discussion).
- [x] Per-bucket token caps, required-bucket protection and explainable truncation/omission manifest.
- [x] Boundary-aware entity resolution with POV inclusion and entity-selection provenance.
- [x] Recent prose retrieval follows chapter/scene narrative order rather than database creation time.
- [x] Anchored Writer historical retrieval excludes future chapter/scene summaries and broad summaries that may contain future events.
- [x] Thread and Author Decision selection is relevance-aware and dependency-aware instead of dumping whole-project lists.
- [x] Context Preview API exposes exact context text plus source/priority/truncation/selection trace without calling a model.

- [x] Writer Pipeline V2: deterministic author-input parsing, plan hashing/versioning and exact word budgets.
- [x] Plot Boundary Manifest is derived from the same ExpansionPlan source used by generation.
- [x] Single-scene generation has explicit preflight/context/generation trace and rejects non-beat input before model calls.
- [x] Partial rewrite returns replacement prose plus reconstructable diff and never auto-applies manuscript edits.
- [x] Multi-scene chapter generation is author-planned, sequential and ephemeral; draft prose is never promoted to Canon/Story State automatically.

- [x] Style Engine scope resolution: Scene type, profile inheritance/priority, Character Voice and context-aware samples/preferences.
- [x] Context Builder + Style Reviewer share the same StyleResolver and expose style provenance.

- [x] After-write V2 extractor can propose new entities plus relationship/item/ability changes using only server-exposed stable IDs.
- [x] New entity IDs are allocated only after author approval; character/ability/world minimal profiles are created at approval time.
- [x] Extraction strips model-authored temporal/provenance coordinates for relationship/item/ability history and validates ability IDs through the reference catalog.
- [x] After-write report groups new narrative-control changes for explicit review; no new auto-mutation path was introduced.

- [x] Unified Continuity Report normalizes and deduplicates deterministic findings across Timeline, Character, Arc, Ability, Identity, Secret, Travel, Information and Thread dependency checkers.
- [x] Unified continuity adds explainable Canon/Knowledge/Item/Story-State/POV/Thread integrity advisories that were previously only counters or missing entirely.
- [x] Scene-scoped continuity may include deterministic prose reviewers, while project reports avoid rescanning every scene for style/knowledge text checks.
- [x] Continuity report exposes severity/category/source evidence and remains advisory-only with zero auto-mutation.

- [x] Past-edit Impact Preview supports CanonFact, Thread, Scene and Chapter change descriptors without applying the edit.
- [x] Scene/Chapter impact traces direct source dependencies plus downstream entity/thread/decision candidates and thread dependency propagation.
- [x] Retcon proposal records persist normalized change descriptors and a frozen read-only impact snapshot; proposal creation never rewrites downstream story data.
- [x] Impact candidates carry high/medium/low review strength and explicit evidence, with author review required for every candidate.
- [x] Hierarchical long-novel summaries now build Scene → Chapter → Arc → Volume → Story with explicit source manifests/fingerprints.
- [x] Summary invalidation follows manuscript ancestry; saves mark stale but never call the model inline.
- [x] Bottom-up/background summary rebuild can target one scope or only the ancestor chain touched by an edited Scene.
- [x] Reader Memory exposes explainable exposure-distance pressure without claiming actual human recall probability.
- [x] Cast-dormancy scan uses a combined alias matcher rather than scene × alias nested matching.
- [x] Arc Health reports plan-vs-actual length, event density and Thread balance without a subjective quality score.
- [x] Repetition/been-here-before candidates expose lexical/phrase/scope signals and use a bounded narrative scan window.
- [x] Summary maintenance exposes stale-scope backlog and supports bounded bottom-up worker rebuild batches.

- [x] What-if Branch sandbox has explicit lifecycle (`draft/selected/merged/discarded`) and project-scoped targets.
- [x] Branch changes support read-only Impact Preview and deterministic A/B comparison without mutating main story data.
- [x] Explicit merge is idempotent and promotes selected changes only into AuthorDecision artifacts; Canon/manuscript/temporal state remain untouched.
- [x] BranchChange stores merge provenance to the resulting AuthorDecision.

- [x] Frontend handoff package generated from runtime OpenAPI (118 paths / 156 operations) with screen map, UX rules, builder prompt and mock payloads.
- [x] Project workspace route now composes existing Writer-first panels with view-scoped data fetching.
- [x] Frontend P0 adds Create Project, After-write Review, Context Preview and What-if sandbox screens.
- [x] Verify now checks frontend API path shapes against runtime OpenAPI and runs TS/TSX syntax transpile diagnostics when node_modules are unavailable.

## Next implementation slice
1. Freeze Backend Core V1 contracts and prepare frontend/API handoff documentation.
2. Map Writer-first screens to existing API endpoints and create mock payload examples.
3. Verify frontend against real contracts, then run end-to-end integration with PostgreSQL/AI provider when dependencies are available.

## Working rule
Do not repackage/export a ZIP after small changes. Save changes directly into this repository. Package only at meaningful checkpoints or when explicitly requested.

### Paused / Next
- [x] Group Q — What-if / Branch sandbox implementation.
- [x] Q1 Branch lifecycle + branch-local change persistence.
- [x] Q2 Preview/compare without mutating main story data.
- [x] Q3 Explicit idempotent merge into Author Decision / plan artifacts only.
- [x] Q4 Impact Preview integration for supported branch change types.
- [x] Frontend handoff package + UI/API contract mapping.
- [ ] Frontend production typecheck/build when Node dependencies are available.
- [ ] Live PostgreSQL + provider end-to-end verification.
