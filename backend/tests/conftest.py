import os
os.environ["DATABASE_URL"]="sqlite+aiosqlite:///:memory:"
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.db.base import Base
from app.db.session import engine

@pytest_asyncio.fixture(autouse=True)
async def schema():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app),base_url="http://test") as c:
        yield c

@pytest_asyncio.fixture
async def proj(client):
    p=(await client.post("/api/v1/projects",json={"name":"T"})).json()
    ch=(await client.post(f"/api/v1/projects/{p['id']}/chapters",json={"title":"C1","order_index":1})).json()
    sc=(await client.post(f"/api/v1/projects/{p['id']}/chapters/{ch['id']}/scenes",json={"title":"S1","order_index":1,"prose":"Some prose."})).json()
    return {"project":p,"chapter":ch,"scene":sc}
