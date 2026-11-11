"""SCRUM-76: sessions that ended more than a week ago are deleted; live ones never are.

Runs on SQLite like test_sessions.py. Each test writes session rows with known
times, moves the clock to TODAY, runs the cleanup, and checks which rows are left.
"""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import sessions
from db import Base
from models import AuthSession, Person
from sessions import delete_old_ended_sessions

TODAY = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
ONE_HOUR = timedelta(hours=1)
ONE_DAY = timedelta(days=1)


@pytest.fixture
def database(monkeypatch: pytest.MonkeyPatch) -> Iterator[Session]:
    """An empty SQLite with one person, and the clock stopped at TODAY."""
    monkeypatch.setattr(sessions, "now", lambda: TODAY)
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine, tables=[Person.__table__, AuthSession.__table__])
    with sessionmaker(bind=engine)() as db:
        db.add(Person(id=1, email="amara@example.com", full_name="Amara", password_hash="x"))
        db.commit()
        yield db


def add_session(
    db: Session,
    name: str,
    started: datetime,
    last_used: datetime,
    signed_out: datetime | None = None,
) -> None:
    """Store one session. ``name`` stands in for the token so tests can tell rows apart."""
    db.add(
        AuthSession(
            person_id=1,
            token_hash=name,
            created_at=started,
            last_seen_at=last_used,
            revoked_at=signed_out,
        )
    )
    db.commit()


def sessions_still_stored(db: Session) -> set[str]:
    return set(db.scalars(select(AuthSession.token_hash)))


def test_a_session_in_use_right_now_is_kept(database: Session) -> None:
    add_session(database, "in use", started=TODAY - ONE_DAY, last_used=TODAY - ONE_HOUR)
    delete_old_ended_sessions(database)
    assert sessions_still_stored(database) == {"in use"}


def test_a_session_signed_out_yesterday_is_kept_for_now(database: Session) -> None:
    yesterday = TODAY - ONE_DAY
    add_session(
        database,
        "signed out yesterday",
        started=yesterday,
        last_used=yesterday,
        signed_out=yesterday,
    )
    delete_old_ended_sessions(database)
    assert sessions_still_stored(database) == {"signed out yesterday"}


def test_a_session_signed_out_eight_days_ago_is_deleted(database: Session) -> None:
    eight_days_ago = TODAY - 8 * ONE_DAY
    add_session(
        database,
        "signed out 8 days ago",
        started=eight_days_ago,
        last_used=eight_days_ago,
        signed_out=eight_days_ago,
    )
    delete_old_ended_sessions(database)
    assert sessions_still_stored(database) == set()


def test_a_session_left_idle_three_days_ago_is_kept_for_now(database: Session) -> None:
    three_days_ago = TODAY - 3 * ONE_DAY
    add_session(database, "idle 3 days", started=three_days_ago, last_used=three_days_ago)
    delete_old_ended_sessions(database)
    assert sessions_still_stored(database) == {"idle 3 days"}


def test_a_session_left_idle_eight_days_ago_is_deleted(database: Session) -> None:
    eight_days_ago = TODAY - 8 * ONE_DAY
    add_session(database, "idle 8 days", started=eight_days_ago, last_used=eight_days_ago)
    delete_old_ended_sessions(database)
    assert sessions_still_stored(database) == set()


def test_a_session_that_hit_the_30_day_limit_over_a_week_ago_is_deleted(
    database: Session,
) -> None:
    """Used an hour ago, so it was never idle, but it started 38 days ago."""
    add_session(database, "38 days old", started=TODAY - 38 * ONE_DAY, last_used=TODAY - ONE_HOUR)
    delete_old_ended_sessions(database)
    assert sessions_still_stored(database) == set()


def test_only_the_old_ended_sessions_go_and_the_count_says_how_many(database: Session) -> None:
    eight_days_ago = TODAY - 8 * ONE_DAY
    add_session(database, "in use", started=TODAY - ONE_DAY, last_used=TODAY - ONE_HOUR)
    add_session(database, "idle 8 days", started=eight_days_ago, last_used=eight_days_ago)
    add_session(
        database,
        "signed out 8 days ago",
        started=eight_days_ago,
        last_used=eight_days_ago,
        signed_out=eight_days_ago,
    )

    how_many_deleted = delete_old_ended_sessions(database)

    assert how_many_deleted == 2
    assert sessions_still_stored(database) == {"in use"}
