"These tests run in sql database in memory without touching real mbwira.db"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import Base, get_db

from app.main import app
from app.models.db import Base, get_db


@pytest_asyncio.fixture
async def engine():

    eng = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def sessionmaker_(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db(sessionmaker_):
    """Session fixture that yields a database session for testing."""
    async with sessionmaker_() as session:
        yield session


@pytest_asyncio.fixture
async def client(sessionmaker_):
    """An HTTP client wired to the app, with `get_db` pointed at the test DB. using ASGI transport."""


    async def override_get_db():
        async with sessionmaker_() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

