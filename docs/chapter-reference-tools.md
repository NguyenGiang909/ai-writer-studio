# Chapter references and thread priorities

Threads expose independent `must_resolve` and `important` booleans through create, patch and list APIs. Existing rows default to false. Neither flag changes thread status. Open-thread prompt context ranks chapter-pinned threads, mandatory payoffs, then important threads; mandatory payoff means before the story ends, not immediately.

`PUT /api/v1/projects/{pid}/chapters/{chapter_id}/cast` accepts partial category updates. Categories: characters, threads, abilities, world (world-entities), locations, timeline (story-events), styles (style-profiles). Each list is bounded to 60 IDs, deduplicated and validated against the project before saving. Omitted categories are preserved. The response includes the persisted cast.

The editor shows selectable reference groups in the right rail, or an inline expandable panel on narrower layouts. Checked entries display their details. Selection is chapter-scoped and survives reload. Writing, expansion, revision, skeleton and chapter-outline prompts include the selected references; selected timeline events are explicit author references, not automatic character knowledge. No automatic canon edits or thread closure occur.

SQLite development uses the existing `ensure_schema` startup mechanism; Alembic installations use migration 0029. Tests: test_chapter_tools.py covers persistence, independent flags, reference preservation, project isolation and actual composed prompt content. Browser verification uses an isolated temporary project and never calls paid AI providers.
