"""SQLAlchemy engine and session factory, built from app settings."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import get_settings


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model."""


def as_psycopg_url(database_url: str) -> URL:
    """Pin the Postgres driver to psycopg 3.

    Render and Supabase hand out plain ``postgresql://`` (or legacy
    ``postgres://``) URLs, which SQLAlchemy would otherwise route to
    psycopg2. Any URL that already names a driver is left untouched.
    """
    url = make_url(database_url)
    if url.drivername in {"postgres", "postgresql"}:
        url = url.set(drivername="postgresql+psycopg")
    return url


@lru_cache
def get_engine() -> Engine:
    """Create the engine once per process, on first use.

    No connection is opened here; SQLAlchemy connects lazily.
    """
    url = as_psycopg_url(get_settings().database_url)
    return create_engine(url, pool_pre_ping=True)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """Return the process-wide session factory bound to the engine."""
    return sessionmaker(bind=get_engine())


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
