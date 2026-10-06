from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.db.base import Base
from app.db.session import engine
import app.models
from app.api.routes.health import router as health_router
from app.api.routes.manuscript import router as manuscript_router
from app.api.routes.story import router as story_router
from app.api.routes.truth import router as truth_router
from app.api.routes.narrative import router as narrative_router
from app.api.routes.discussion import router as discussion_router
from app.api.routes.review import router as review_router
from app.api.routes.memory import router as memory_router
from app.api.routes.account import router as account_router
from app.api.routes.ai import router as ai_router
from app.api.routes.signals import router as signals_router
from app.api.routes.export import router as export_router
from app.api.routes.search import router as search_router
from app.api.routes.authoring import router as authoring_router

app = FastAPI(title="AI Writer Studio", version="recovery-m1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000",
                   "http://localhost:3001", "http://127.0.0.1:3001"],
    # app local-first: cho phép mọi origin nội bộ (localhost/127.x/LAN/Tauri webview)
    # — trình duyệt mở qua preview proxy hay IP LAN cũng gọi API được
    allow_origin_regex=(r"^(https?://(localhost|127\.0\.0\.1|\[::1\]"
                        r"|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
                        r"|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
                        r"|192\.168\.\d{1,3}\.\d{1,3})(:\d+)?"
                        r"|tauri://localhost|app://-)$"),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(manuscript_router, prefix="/api/v1")
app.include_router(story_router, prefix="/api/v1")
app.include_router(truth_router, prefix="/api/v1")
app.include_router(narrative_router, prefix="/api/v1")
app.include_router(discussion_router, prefix="/api/v1")
app.include_router(review_router, prefix="/api/v1")
app.include_router(memory_router, prefix="/api/v1")
app.include_router(account_router, prefix="/api/v1")
app.include_router(ai_router, prefix="/api/v1")
app.include_router(signals_router, prefix="/api/v1")
app.include_router(export_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")
app.include_router(authoring_router, prefix="/api/v1")


@app.on_event("startup")
async def ensure_schema():
    """Dev-mode schema ensure: create missing tables and add missing columns.

    Production deployments should run Alembic migrations instead; this keeps
    the local SQLite dev database in sync without a manual step.
    """
    if not engine.url.get_backend_name().startswith("sqlite"):
        return
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for table in Base.metadata.sorted_tables:
            rows = (await conn.execute(text(f"PRAGMA table_info({table.name})"))).fetchall()
            existing = {r[1] for r in rows}
            for col in table.columns:
                if col.name in existing:
                    continue
                ddl = str(col.type.compile(dialect=engine.sync_engine.dialect))
                if col.default is not None and col.default.is_scalar:
                    ddl += f" DEFAULT {col.default.arg!r}"
                await conn.execute(
                    text(f"ALTER TABLE {table.name} ADD COLUMN {col.name} {ddl}"))
