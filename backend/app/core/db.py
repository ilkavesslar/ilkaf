from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings
from app.models.base import Base

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def create_engine(settings: Settings) -> AsyncEngine | None:
    if not settings.resolved_database_url:
        return None
    kwargs: dict = {"pool_pre_ping": True, "echo": False}
    if settings.is_sqlite:
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_size"] = settings.database_pool_size
        kwargs["max_overflow"] = settings.database_max_overflow
        kwargs["connect_args"] = settings.postgres_connect_args
    engine = create_async_engine(settings.sqlalchemy_url, **kwargs)
    if settings.is_sqlite:

        @event.listens_for(engine.sync_engine, "connect")
        def _sqlite_foreign_keys(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def configure_database(settings: Settings) -> AsyncEngine | None:
    global _engine, _session_factory
    _engine = create_engine(settings)
    if _engine is not None:
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_engine() -> AsyncEngine | None:
    return _engine


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("database is not configured")
    async with _session_factory() as session:
        yield session


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields a request-scoped session."""
    async with session_scope() as session:
        yield session


async def check_database() -> bool:
    if _engine is None:
        return False
    async with _engine.connect() as connection:
        await connection.exec_driver_sql("SELECT 1")
    return True


async def create_schema_for_tests() -> None:
    if _engine is None:
        return
    async with _engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
