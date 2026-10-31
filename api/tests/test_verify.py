"""SCRUM-12: an email verification link lands on one of three clear screens.

Runs on SQLite like test_invites.py. The clock is the one sessions.py uses,
so moving it ages the link.
"""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import sessions
import verifications
from db import Base, get_db
from main import app
from models import EmailVerification, Person
from routers.verify import NOT_FOUND, NOTHING_TO_RESEND
from security import hash_password
from verifications import VERIFICATION_LIFETIME, create_verification

START = datetime(2026, 10, 31, 9, 0, tzinfo=UTC)
EMAIL = "amara.okafor@example.com"


class Clock:
    def __init__(self) -> None:
        self.time = START

    def advance(self, by: timedelta) -> None:
        self.time += by


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    fake = Clock()
    monkeypatch.setattr(sessions, "now", lambda: fake.time)
    return fake


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """Every link 'emailed' by a resend, as (email, token)."""
    outbox: list[tuple[str, str]] = []
    monkeypatch.setattr(
        verifications, "deliver", lambda email, token: outbox.append((email, token))
    )
    return outbox


@pytest.fixture
def factory(clock: Clock) -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine, tables=[Person.__table__, EmailVerification.__table__])
    factory = sessionmaker(bind=engine)
    with factory() as db:
        db.add(
            Person(
                id=1, email=EMAIL, full_name="Amara Okafor", password_hash=hash_password("x" * 12)
            )
        )
        db.commit()
    return factory


def new_link(factory: sessionmaker[Session]) -> str:
    with factory() as db:
        _, token = create_verification(db, db.get(Person, 1))
    return token


@pytest.fixture
def token(factory: sessionmaker[Session]) -> str:
    return new_link(factory)


@pytest.fixture
def client(factory: sessionmaker[Session]) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app, base_url="https://testserver")
    finally:
        app.dependency_overrides.clear()


def verified_at(factory: sessionmaker[Session]) -> datetime | None:
    with factory() as db:
        stamp = db.get(Person, 1).email_verified_at
    return stamp.replace(tzinfo=UTC) if stamp and stamp.tzinfo is None else stamp


# Success


def test_a_good_link_confirms_the_address(
    client: TestClient, token: str, factory: sessionmaker[Session]
) -> None:
    r = client.post(f"/verify/{token}")
    assert r.status_code == 200
    assert r.json() == {"state": "verified", "email": EMAIL, "verified_at": "2026-10-31T09:00:00Z"}
    assert r.headers["cache-control"] == "no-store"
    assert verified_at(factory) == START


def test_only_the_hash_of_the_token_is_stored(token: str, factory: sessionmaker[Session]) -> None:
    with factory() as db:
        stored = db.scalar(select(EmailVerification.token_hash))
    assert token not in stored


# Single use


def test_a_link_works_once_then_says_already_verified(
    client: TestClient, token: str, clock: Clock
) -> None:
    assert client.post(f"/verify/{token}").json()["state"] == "verified"
    clock.advance(timedelta(days=3))
    r = client.post(f"/verify/{token}")
    assert r.status_code == 200
    assert r.json() == {
        "state": "already_verified",
        "email": EMAIL,
        "verified_at": "2026-10-31T09:00:00Z",
    }


def test_a_second_link_after_confirming_says_already_verified(
    client: TestClient, factory: sessionmaker[Session]
) -> None:
    first, second = new_link(factory), new_link(factory)
    assert client.post(f"/verify/{first}").json()["state"] == "verified"
    assert client.post(f"/verify/{second}").json()["state"] == "already_verified"


def test_a_lost_race_is_already_verified_not_an_error(
    token: str, factory: sessionmaker[Session]
) -> None:
    """Two requests both read the link as unused; only one may use it."""
    with factory() as first, factory() as second:
        a = verifications.find_verification(first, token)
        b = verifications.find_verification(second, token)
        assert verifications.confirm(first, a).state == "verified"
        assert verifications.confirm(second, b).state == "already_verified"


# Expiry


def test_a_link_still_works_just_before_24_hours(
    client: TestClient, token: str, clock: Clock
) -> None:
    clock.advance(VERIFICATION_LIFETIME - timedelta(minutes=1))
    assert client.post(f"/verify/{token}").json()["state"] == "verified"


def test_a_link_expires_after_24_hours(
    client: TestClient, token: str, clock: Clock, factory: sessionmaker[Session]
) -> None:
    clock.advance(VERIFICATION_LIFETIME)
    r = client.post(f"/verify/{token}")
    assert r.status_code == 200
    assert r.json() == {"state": "expired", "email": EMAIL, "verified_at": None}
    assert verified_at(factory) is None


def test_a_link_for_an_old_address_counts_as_expired(
    client: TestClient, token: str, factory: sessionmaker[Session]
) -> None:
    with factory() as db:
        db.get(Person, 1).email = "amara@new.example.com"
        db.commit()
    body = client.post(f"/verify/{token}").json()
    assert body["state"] == "expired"
    assert body["email"] == "amara@new.example.com"
    assert verified_at(factory) is None


# Resend


def test_an_expired_link_can_send_a_new_one_that_works(
    client: TestClient, token: str, clock: Clock, sent: list[tuple[str, str]]
) -> None:
    clock.advance(VERIFICATION_LIFETIME + timedelta(hours=1))
    r = client.post(f"/verify/{token}/resend")
    assert r.status_code == 202
    assert r.json() == {"email": EMAIL}
    assert len(sent) == 1
    email, fresh = sent[0]
    assert email == EMAIL
    assert fresh != token
    assert client.post(f"/verify/{fresh}").json()["state"] == "verified"


def test_resending_twice_keeps_only_one_live_link(
    client: TestClient,
    token: str,
    clock: Clock,
    sent: list[tuple[str, str]],
    factory: sessionmaker[Session],
) -> None:
    clock.advance(VERIFICATION_LIFETIME)
    client.post(f"/verify/{token}/resend")
    client.post(f"/verify/{token}/resend")
    assert len(sent) == 1
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(EmailVerification)) == 2


def test_a_live_or_used_link_has_nothing_to_resend(
    client: TestClient, token: str, sent: list[tuple[str, str]]
) -> None:
    r = client.post(f"/verify/{token}/resend")
    assert r.status_code == 409
    assert r.json()["detail"] == NOTHING_TO_RESEND
    client.post(f"/verify/{token}")
    assert client.post(f"/verify/{token}/resend").status_code == 409
    assert sent == []


# Unknown links


def test_an_unknown_link_is_404(client: TestClient, factory: sessionmaker[Session]) -> None:
    for path in ("/verify/not-a-real-token", "/verify/not-a-real-token/resend"):
        r = client.post(path)
        assert r.status_code == 404
        assert r.json()["detail"] == NOT_FOUND
