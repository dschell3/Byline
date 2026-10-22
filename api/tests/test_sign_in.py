"""SCRUM-9: sign-in fails safely.

Runs without Postgres. The person table has no Postgres-only column types,
so these tests build just that table in an in-memory SQLite and hand it to
the app in place of the real database.
"""

import statistics
import time
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import ratelimit
from db import get_db
from main import app
from models import Person
from routers.auth import INVALID_CREDENTIALS
from security import hash_password

SIGN_IN = "/auth/sign-in"
EMAIL = "amara.okafor@example.com"
PASSWORD = "correct horse battery staple"


@pytest.fixture
def client() -> Iterator[TestClient]:
    """App wired to a fresh SQLite with one known account, limiters reset."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Person.__table__.create(engine)
    factory = sessionmaker(bind=engine)
    with factory() as session:
        # SQLite does not auto-number a BigInteger primary key, so set it here.
        session.add(
            Person(
                id=1,
                email=EMAIL,
                full_name="Amara Okafor",
                password_hash=hash_password(PASSWORD),
            )
        )
        session.commit()

    def override_get_db() -> Iterator[Session]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    ratelimit.by_account._events.clear()
    ratelimit.by_ip._events.clear()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def attempt(client: TestClient, email: str, password: str, ip: str = "203.0.113.10") -> object:
    return client.post(
        SIGN_IN, json={"email": email, "password": password}, headers={"x-forwarded-for": ip}
    )


def test_correct_credentials_return_the_person(client: TestClient) -> None:
    """Success returns id and name only; never the hash."""
    r = attempt(client, EMAIL, PASSWORD)
    assert r.status_code == 200
    assert r.json() == {"id": 1, "full_name": "Amara Okafor"}
    assert "password_hash" not in r.text
    assert r.headers["cache-control"] == "no-store"


def test_email_lookup_is_case_insensitive(client: TestClient) -> None:
    assert attempt(client, "Amara.Okafor@Example.com", PASSWORD).status_code == 200


def test_wrong_password_and_unknown_email_are_indistinguishable(client: TestClient) -> None:
    """The card's core requirement: same status code, same body, both paths."""
    wrong_password = attempt(client, EMAIL, "not it")
    unknown_email = attempt(client, "nobody@example.com", PASSWORD)
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json() == {"detail": INVALID_CREDENTIALS}


def test_unknown_email_still_runs_a_hash_verification(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Timing can only match if the expensive step runs on both paths."""
    calls: list[str | None] = []
    import routers.auth as auth

    real = auth.verify_password
    monkeypatch.setattr(auth, "verify_password", lambda pw, h: calls.append(h) or real(pw, h))
    attempt(client, EMAIL, "not it")
    attempt(client, "nobody@example.com", "not it")
    assert len(calls) == 2
    assert calls[0] is not None and calls[1] is None


def test_failure_paths_take_about_the_same_time(client: TestClient) -> None:
    """Loose check, wide tolerance: the unknown-email path must not be the fast one."""

    def median_ms(email: str) -> float:
        samples = []
        for i in range(7):
            start = time.perf_counter()
            attempt(client, email, "not it", ip=f"198.51.100.{i}")
            samples.append(time.perf_counter() - start)
            ratelimit.by_account._events.clear()
        return statistics.median(samples) * 1000

    wrong_password = median_ms(EMAIL)
    unknown_email = median_ms("nobody@example.com")
    assert unknown_email > 0.5 * wrong_password


def test_stored_hash_is_argon2_and_not_the_password() -> None:
    h = hash_password(PASSWORD)
    assert h.startswith("$argon2id$")
    assert PASSWORD not in h


def test_account_is_limited_after_five_failures(client: TestClient) -> None:
    for i in range(5):
        assert attempt(client, EMAIL, "not it", ip=f"198.51.100.{i}").status_code == 401
    blocked = attempt(client, EMAIL, PASSWORD, ip="198.51.100.99")
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0


def test_ip_is_limited_after_twenty_failures(client: TestClient) -> None:
    for i in range(20):
        assert attempt(client, f"user{i}@example.com", "not it").status_code == 401
    assert attempt(client, "user99@example.com", "not it").status_code == 429


def test_success_clears_the_account_counter(client: TestClient) -> None:
    for i in range(4):
        attempt(client, EMAIL, "not it", ip=f"198.51.100.{i}")
    assert attempt(client, EMAIL, PASSWORD).status_code == 200
    for i in range(4):
        assert attempt(client, EMAIL, "not it", ip=f"198.51.100.{i + 10}").status_code == 401


def test_limiter_window_expires() -> None:
    now = [1000.0]
    limiter = ratelimit.FailureLimiter(limit=2, window=60, clock=lambda: now[0])
    limiter.record_failure("k")
    limiter.record_failure("k")
    assert limiter.retry_after("k") == 61
    now[0] += 61
    assert limiter.retry_after("k") == 0
