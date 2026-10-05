# AI Writer Studio

**A writer-first Story OS for long-form fiction — the author stays the authority, AI assists without silently rewriting your canon.**

> Ứng dụng viết tiểu thuyết dài kỳ: tác giả viết trước, AI hỗ trợ thảo luận, mở rộng bản thảo và kiểm tra tính liên tục. Mọi gợi ý của AI là bản nháp — không có gì tự động trở thành Canon.

![Status](https://img.shields.io/badge/status-alpha-orange) ![License](https://img.shields.io/badge/license-MIT-blue) ![Backend](https://img.shields.io/badge/backend-FastAPI-009688) ![Frontend](https://img.shields.io/badge/frontend-Next.js%2015-000)

![Manuscript editor](docs/screenshots/editor.png)

## Why another AI writing tool?

Most AI writing apps make the model the author. This one is built around the opposite assumption:

- **The author is the source of truth.** AI output is always a draft — it only becomes canon through an explicit review/approval step.
- **Continuity is data, not vibes.** Characters, locations, abilities, relationships, canon facts, story states, knowledge states (who knows what, since when) and narrative threads are tracked in a story database that AI is *constrained* by — not trusted to remember.
- **Long-form scale.** Hundreds of chapters stay manageable via a volume → arc → chapter → scene hierarchy, layered summaries, and context manifests that show exactly what the model received.

## Features

- **Manuscript editor** — scene-first writing with skeleton notes, briefs, autosave, POV/temporal metadata
- **Story database** — characters (aliases, arcs), locations, items, factions, abilities, relationships
- **Canon & truth layer** — canon facts with truth status (`CANON`/`RUMOR`/`PLANNED`), secrets, author decisions
- **Continuity engine** — restricted-appearance, knowledge-leak, stale-thread, location and ability checks; post-generation issue flags
- **Timeline** — story-time vs narrative-order events, story states per entity, human-readable state rendering (VI/EN)
- **AI assistant (BYOK)** — provider/model routing per task, usage logging, encrypted credentials
- **AI memory** — every AI call is persisted (`ai_turns`), recent scene turns are re-injected, layered `story_summaries`, relevance-ranked character/canon context with a transparent manifest
- **Author-approved AI workflows** — scene skeleton suggestions, chapter outline generation (edit/approve before scenes are created), expansion & revision drafts, scene summarization
- **What-if branches** — explore alternate storylines, preview impact, merge only through author decisions
- **Review queue** — AI-proposed canon/relationship changes wait for author approval
- **Vietnamese-first UI** with English translation

![AI chapter outline](docs/screenshots/outline-ai.png)
![Timeline](docs/screenshots/timeline.png)

## Architecture

```
frontend/   Next.js 15 + React 19 + TypeScript — 3-pane writer workspace
backend/    FastAPI + SQLAlchemy 2 (async) + Alembic
            SQLite by default (writer.db) · Postgres/pgvector via docker-compose
            Provider adapters: OpenAI-compatible endpoints (OpenAI, OpenRouter,
            DeepSeek, custom base URL) + deterministic FakeProvider for dev
```

Key backend pieces:

| Path | Role |
|---|---|
| `app/ai/compose.py` | Prompt assembly — context manifest, session turns, ranked entities |
| `app/ai/router.py` | Model routing: project pref → account pref → fallback |
| `app/services/continuity.py` | Post-write continuity checks |
| `app/services/memory.py` | Summaries, ancestor chain, AI turn history |
| `app/services/branch.py` | What-if branch diff/merge |

## Quickstart

Requirements: Python 3.12+, Node 20+

```bash
# backend
cd backend
python -m venv .venv && .venv/Scripts/activate   # Windows; source .venv/bin/activate on Unix
pip install -r requirements.txt
uvicorn app.main:app --port 8000

# frontend (new terminal)
cd frontend
cp ../.env.example ../.env   # or set NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
echo NEXT_PUBLIC_API_URL=http://localhost:8000 > .env.local
npm run dev
```

Open http://localhost:3000 → create a project, or seed the demo:

```bash
cd backend
python seed_demo.py   # ~15-chapter demo project via REST API
```

`docker-compose.yml` is included for a Postgres + Redis setup; plain SQLite works out of the box for a single local author.

## AI providers

AI features are BYOK — add a provider key in the **Tài khoản** (Account) page. Keys are Fernet-encrypted at rest; the API only ever returns a masked hint (`••••xxxx`). Without a key, tasks fall back to a deterministic `FakeProvider` so the whole UI stays testable.

## Testing

```bash
cd backend && pytest          # 75 tests — API contracts, memory, continuity
cd frontend && npx tsc --noEmit
```

## Status

Alpha, single-user local (`DEV_USER` — no real auth yet). Active work: layered auto-summarization, provider-held conversation threads, retrieval, packaging (Tauri). See `docs/ROADMAP.md` and `docs/STATUS.md` for the honest state of things.

## License

MIT — see [LICENSE](LICENSE).
