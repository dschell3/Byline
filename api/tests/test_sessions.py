"""SCRUM-13: sessions live server-side, expire, and decide roles per request.

Runs without Postgres, like test_sign_in.py: the four tables involved have no
Postgres-only column types, so an in-memory SQLite stands in for the database.
The client talks to https://testserver because the session cookie is Secure
and is never sent over plain http.
"""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import ratelimit
import sessions
from db import Base, get_db
from models import AuthSession, Membership, Organization, Person
from routers import auth
from security import hash_password
from sessions import ABSOLUTE_TIMEOUT, COOKIE_NAME, IDLE_TIMEOUT, CurrentUser, require_role

PASSWORD = "correct horse battery staple"
MEMBER = "amara.okafor@example.com"
SUPERVISOR = "lyric.james@example.com"
START = datetime(2026, 10, 25, 9, 0, tzinfo=UTC)


class Clock:
    """A clock the test moves by hand."""

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
def factory() -> sessionmaker[Session]:
    """A fresh SQLite holding one member and one supervisor in one organization."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    tables = [Organization, Person, Membership, AuthSession]
    Base.metadata.create_all(engine, tables=[model.__table__ for model in tables])
    factory = sessionmaker(bind=engine)
    with factory() as db:
        db.add(Organization(id=1, name="The Emerson Empire", slug="emerson"))
        for person_id, email, name, role in [
            (1, MEMBER, "Amara Okafor", "member"),
            (2, SUPERVISOR, "Lyric James", "supervisor"),
        ]:
            db.add(
                Person(
                    id=person_id,
                    email=email,
                    full_name=name,
                    password_hash=hash_password(PASSWORD),
                )
            )
            db.add(Membership(id=person_id, person_id=person_id, organization_id=1, role=role))
        db.commit()
    return factory


@pytest.fixture
def client(factory: sessionmaker[Session], clock: Clock) -> Iterator[TestClient]:
    """The auth routes plus one supervisor-only route, on the SQLite above."""
    app = FastAPI()
    app.include_router(auth.router)

    @app.get("/review-queue")
    def review_queue(
        user: CurrentUser = Depends(require_role("supervisor", "admin")),
    ) -> dict[str, str]:
        return {"reviewer": user.person.full_name}

    def override_get_db() -> Iterator[Session]:
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    ratelimit.by_account._events.clear()
    ratelimit.by_ip._events.clear()
    yield TestClient(app, base_url="https://testserver")


def sign_in(client: TestClient, email: str) -> object:
    return client.post("/auth/sign-in", json={"email": email, "password": PASSWORD})


def test_sign_in_sets_an_http_only_secure_same_site_cookie(client: TestClient) -> None:
    r = sign_in(client, MEMBER)
    assert r.status_code == 200
    cookie = r.headers["set-cookie"].lower()
    assert cookie.startswith(f"{COOKIE_NAME}=")
    for attribute in ("httponly", "secure", "samesite=lax", "path=/"):
        assert attribute in cookie
    # The token travels only in the cookie, never in a body a script could read.
    assert client.cookies[COOKIE_NAME] not in r.text


def test_only_a_hash_of_the_token_is_stored(
    client: TestClient, factory: sessionmaker[Session]
) -> None:
    sign_in(client, MEMBER)
    token = client.cookies[COOKIE_NAME]
    with factory() as db:
        stored = db.scalars(select(AuthSession.token_hash)).all()
    assert len(stored) == 1
    assert token not in stored[0]


def test_me_returns_the_person_and_their_roles(client: TestClient) -> None:
    sign_in(client, SUPERVISOR)
    r = client.get("/auth/me")
    assert r.status_code == 200
    assert r.json() == {"id": 2, "full_name": "Lyric James", "roles": ["supervisor"]}
    assert r.headers["cache-control"] == "no-store"


def test_no_cookie_means_signed_out(client: TestClient) -> None:
    r = client.get("/auth/me")
    assert r.status_code == 401
    assert r.json() == {"detail": sessions.SIGN_IN_REQUIRED}


def test_a_forged_cookie_is_rejected(client: TestClient) -> None:
    client.cookies.set(COOKIE_NAME, "not-a-real-token")
    assert client.get("/auth/me").status_code == 401


def test_activity_keeps_the_session_alive(client: TestClient, clock: Clock) -> None:
    sign_in(client, MEMBER)
    for _ in range(5):
        clock.advance(IDLE_TIMEOUT - timedelta(minutes=1))
        assert client.get("/auth/me").status_code == 200


def test_an_idle_session_expires(client: TestClient, clock: Clock) -> None:
    sign_in(client, MEMBER)
    clock.advance(IDLE_TIMEOUT + timedelta(seconds=1))
    assert client.get("/auth/me").status_code == 401


def test_an_active_session_still_ends_at_the_absolute_limit(
    client: TestClient, clock: Clock, factory: sessionmaker[Session]
) -> None:
    sign_in(client, MEMBER)
    clock.advance(ABSOLUTE_TIMEOUT + timedelta(seconds=1))
    with factory() as db:
        # Seen a minute ago, so only the absolute limit can end it.
        db.execute(update(AuthSession).values(last_seen_at=clock.time - timedelta(minutes=1)))
        db.commit()
    assert client.get("/auth/me").status_code == 401


def test_sign_out_revokes_the_session_server_side(client: TestClient) -> None:
    sign_in(client, MEMBER)
    token = client.cookies[COOKIE_NAME]

    r = client.post("/auth/sign-out")
    assert r.status_code == 204
    assert f"{COOKIE_NAME}=" in r.headers["set-cookie"]

    # A browser that ignored the cleared cookie, or a copy of the token, is refused.
    client.cookies.set(COOKIE_NAME, token)
    assert client.get("/auth/me").status_code == 401


def test_sign_out_without_a_session_is_harmless(client: TestClient) -> None:
    assert client.post("/auth/sign-out").status_code == 204


def test_signing_in_again_retires_the_previous_token(client: TestClient) -> None:
    sign_in(client, MEMBER)
    first = client.cookies[COOKIE_NAME]
    sign_in(client, MEMBER)
    assert client.cookies[COOKIE_NAME] != first

    client.cookies.set(COOKIE_NAME, first)
    assert client.get("/auth/me").status_code == 401


def test_a_member_cannot_reach_a_supervisor_only_endpoint(client: TestClient) -> None:
    sign_in(client, MEMBER)
    r = client.get("/review-queue")
    assert r.status_code == 403
    assert r.json() == {"detail": sessions.NOT_ALLOWED}


def test_a_supervisor_can_reach_a_supervisor_only_endpoint(client: TestClient) -> None:
    sign_in(client, SUPERVISOR)
    r = client.get("/review-queue")
    assert r.status_code == 200
    assert r.json() == {"reviewer": "Lyric James"}


def test_a_supervisor_only_endpoint_needs_a_session_first(client: TestClient) -> None:
    assert client.get("/review-queue").status_code == 401


def test_roles_are_read_from_the_database_on_every_request(
    client: TestClient, factory: sessionmaker[Session]
) -> None:
    """Nothing about the role is in the cookie: a demotion applies immediately."""
    sign_in(client, SUPERVISOR)
    assert client.get("/review-queue").status_code == 200

    with factory() as db:
        db.execute(update(Membership).where(Membership.person_id == 2).values(role="member"))
        db.commit()
    assert client.get("/review-queue").status_code == 403


def test_an_inactive_membership_grants_nothing(
    client: TestClient, factory: sessionmaker[Session]
) -> None:
    sign_in(client, SUPERVISOR)
    with factory() as db:
        db.execute(update(Membership).where(Membership.person_id == 2).values(is_active=False))
        db.commit()
    assert client.get("/review-queue").status_code == 403
    assert client.get("/auth/me").json()["roles"] == []
