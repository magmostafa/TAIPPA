"""Database module.

This module provides the SQLAlchemy asynchronous engine and session factory used
throughout the application.  The connection URL is read from the environment
variable `DATABASE_URL`.  In development the default is a local SQLite file.

The database layer uses SQLAlchemy 2.0's asyncio APIs.  When running against
PostgreSQL the `asyncpg` dialect is automatically selected from the connection
URL.
"""

from __future__ import annotations

import os
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models.

    All models should inherit from this base to automatically set up a table
    prefix and to define common methods for serialising to dictionaries.  The
    `metadata` attribute is used by Alembic for autogeneration.
    """

    pass


def get_database_url() -> str:
    """Return the database connection string.

    The URL is read from the `DATABASE_URL` environment variable.  If not
    present, a default SQLite URI pointing to a local file is returned.  In
    production you should set `DATABASE_URL` to a PostgreSQL URL such as
    `postgresql+asyncpg://user:password@host:port/dbname`.
    """
    return os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./taippa.db")


def create_engine() -> AsyncEngine:
    """Create and return the SQLAlchemy async engine.

    The engine is configured with `future=True` to enable SQLAlchemy 2.0 style
    behaviour.  Echo is disabled by default but can be enabled by setting the
    `SQLALCHEMY_ECHO` environment variable to a truthy value.
    """
    url = get_database_url()
    echo = os.getenv("SQLALCHEMY_ECHO", "false").lower() in {"1", "true", "yes"}
    return create_async_engine(url, echo=echo)


# Engine instance used by the application.  Created at import time.
engine: AsyncEngine = create_engine()

# Sessionmaker configured for async sessions.
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> async_sessionmaker:
    """Dependency function for FastAPI that yields a database session.

    This can be used in FastAPI path operations via dependency injection.  It
    yields a new session and ensures it is closed after the request ends.
    """
    async with async_session_factory() as session:
        yield session