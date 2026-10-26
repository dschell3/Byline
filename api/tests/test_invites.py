"""SCRUM-11: an invite link shows what you are joining and creates the account in one step.

Runs on SQLite like test_home.py. The clock is the one sessions.py uses, so
moving it ages both the invite and any session it starts.
"""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import ratelimit
import sessions
from db import Base, get_db
from invites import INVITE_LIFETIME, MIN_PASSWORD_LENGTH, create_invite
from main import app
from models import AuthSession, Cohort, Invite, Membership, Organization, Person, Team, Track
from routers.invites import ALREADY_HAVE_ACCOUNT, GONE, NOT_FOUND
from security import hash_password
from sessions import COOKIE_NAME

START = datetime(2026, 10, 25, 9, 0, tzinfo=UTC)
INVITEE = "Amara.Okafor@example.com"
PASSWORD = "correct horse battery staple"


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
def factory(clock: Clock) -> sessionmaker[Session]:
    """One organization with a cohort, a track, a team and the supervisor who invites."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    tables = [Organization, Person, Team, Cohort, Track, Membership, AuthSession, Invite]
    Base.metadata.create_all(engine, tables=[model.__table__ for model in tables])
    factory = sessionmaker(bind=engine)
    with factory() as db:
        db.add(Organization(id=1, name="The Emerson Empire", slug="emerson"))
        db.add(Team(id=1, organization_id=1, name="Design"))
        db.add(
            Cohort(
                id=1,
                organization_id=1,
                name="Autumn 2026 · Cohort 7",
                starts_on=datetime(2026, 9, 28).date(),
                ends_on=datetime(2026, 12, 18).date(),
            )
        )
        db.add(
            Track(
                id=1, organization_id=1, name="UX/UI", onboarding_pack_url="https://example.com/ux"
            )
        )
        db.add(
            Person(
                id=1,
                email="marguerite@example.com",
                full_name="Marguerite Ellis",
                password_hash=hash_password(PASSWORD),
            )
        )
        db.add(Membership(id=1, person_id=1, organization_id=1, role="supervisor", team_id=1))
        db.commit()
    return factory


@pytest.fixture
def token(factory: sessionmaker[Session]) -> str:
    """An open invite for Amara into cohort 7, UX/UI, on Marguerite's team."""
    with factory() as db:
        _, raw = create_invite(
            db,
            organization_id=1,
            invited_by_membership_id=1,
            email=INVITEE,
            team_id=1,
            cohort_id=1,
            track_id=1,
        )
    return raw


@pytest.fixture
def client(factory: sessionmaker[Session]) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    ratelimit.by_account._events.clear()
    ratelimit.by_ip._events.clear()
    try:
        yield TestClient(app, base_url="https://testserver")
    finally:
        app.dependency_overrides.clear()


def accept(client: TestClient, token: str, **overrides: object) -> object:
    body = {"full_name": "Amara Okafor", "password": PASSWORD, "timezone": "Africa/Lagos"}
    body.update(overrides)
    return client.post(f"/invites/{token}/accept", json=body)


def test_opening_the_link_shows_who_invited_you_and_what_you_join(
    client: TestClient, token: str
) -> None:
    r = client.get(f"/invites/{token}")
    assert r.status_code == 200
    body = r.json()
    assert body["state"] == "open"
    assert body["email"] == "amara.okafor@example.com"
    assert body["role"] == "member"
    assert body["organization"] == {"name": "The Emerson Empire"}
    assert body["cohort"] == {
        "name": "Autumn 2026 · Cohort 7",
        "starts_on": "2026-09-28",
        "ends_on": "2026-12-18",
    }
    assert body["track"] == {"name": "UX/UI", "onboarding_pack_url": "https://example.com/ux"}
    assert body["invited_by"] == {
        "full_name": "Marguerite Ellis",
        "email": "marguerite@example.com",
    }
    assert r.headers["cache-control"] == "no-store"


def test_invites_last_thirty_days(client: TestClient, token: str) -> None:
    assert INVITE_LIFETIME == timedelta(days=30)
    expires = datetime.fromisoformat(client.get(f"/invites/{token}").json()["expires_at"])
    assert expires == START + INVITE_LIFETIME


def test_a_link_nobody_issued_is_not_found(client: TestClient) -> None:
    r = client.get("/invites/not-a-real-token")
    assert r.status_code == 404
    assert r.json() == {"detail": NOT_FOUND}
    assert accept(client, "not-a-real-token").status_code == 404


def test_only_a_hash_of_the_token_is_stored(factory: sessionmaker[Session], token: str) -> None:
    with factory() as db:
        stored = db.scalars(select(Invite.token_hash)).all()
    assert len(stored) == 1
    assert token not in stored[0]


def test_accepting_creates_the_account_and_membership_in_one_action(
    client: TestClient, factory: sessionmaker[Session], token: str
) -> None:
    r = accept(client, token)
    assert r.status_code == 201
    assert r.json() == {"id": 2, "full_name": "Amara Okafor"}
    assert "password_hash" not in r.text
    assert r.headers["cache-control"] == "no-store"

    with factory() as db:
        person = db.scalar(select(Person).where(Person.id == 2))
        membership = db.scalar(select(Membership).where(Membership.person_id == 2))
        invite = db.scalar(select(Invite))
    assert person.email == "amara.okafor@example.com"  # lower-cased from the invite
    assert person.timezone == "Africa/Lagos"
    assert person.password_hash != PASSWORD
    assert (membership.organization_id, membership.role) == (1, "member")
    assert (membership.team_id, membership.cohort_id, membership.track_id) == (1, 1, 1)
    assert invite.accepted_at is not None


def test_accepting_signs_the_person_in(client: TestClient, token: str) -> None:
    """The browser lands on the first-run screen already signed in, no second step."""
    r = accept(client, token)
    cookie = r.headers["set-cookie"].lower()
    assert cookie.startswith(f"{COOKIE_NAME}=")
    for attribute in ("httponly", "secure", "samesite=lax"):
        assert attribute in cookie
    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json() == {"id": 2, "full_name": "Amara Okafor", "roles": ["member"]}


def test_a_link_works_exactly_once(client: TestClient, token: str) -> None:
    assert accept(client, token).status_code == 201
    second = accept(client, token, full_name="Someone Else")
    assert second.status_code == 410
    assert second.json() == {"detail": GONE["used"]}
    assert client.get(f"/invites/{token}").json()["state"] == "used"


def test_an_expired_link_is_refused_but_still_says_who_sent_it(
    client: TestClient, clock: Clock, token: str
) -> None:
    clock.advance(INVITE_LIFETIME + timedelta(seconds=1))
    shown = client.get(f"/invites/{token}")
    assert shown.status_code == 200
    assert shown.json()["state"] == "expired"
    # The page needs the inviter to offer "ask for a new one".
    assert shown.json()["invited_by"]["email"] == "marguerite@example.com"
    r = accept(client, token)
    assert r.status_code == 410
    assert r.json() == {"detail": GONE["expired"]}


def test_a_link_still_works_on_its_last_day(client: TestClient, clock: Clock, token: str) -> None:
    clock.advance(INVITE_LIFETIME - timedelta(minutes=1))
    assert client.get(f"/invites/{token}").json()["state"] == "open"
    assert accept(client, token).status_code == 201


def test_a_withdrawn_link_is_refused(
    client: TestClient, factory: sessionmaker[Session], token: str
) -> None:
    with factory() as db:
        db.execute(update(Invite).values(revoked_at=START))
        db.commit()
    assert client.get(f"/invites/{token}").json()["state"] == "revoked"
    r = accept(client, token)
    assert r.status_code == 410
    assert r.json() == {"detail": GONE["revoked"]}


def test_an_email_that_already_has_an_account_is_sent_to_sign_in(
    client: TestClient, factory: sessionmaker[Session], token: str
) -> None:
    with factory() as db:
        db.add(
            Person(
                id=2,
                email="amara.okafor@example.com",
                full_name="Amara Already",
                password_hash=hash_password(PASSWORD),
            )
        )
        db.commit()
    r = accept(client, token)
    assert r.status_code == 409
    assert r.json() == {"detail": ALREADY_HAVE_ACCOUNT}
    # The link is not spent by a refused attempt.
    assert client.get(f"/invites/{token}").json()["state"] == "open"


def test_a_short_password_is_refused_and_nothing_is_created(
    client: TestClient, factory: sessionmaker[Session], token: str
) -> None:
    r = accept(client, token, password="x" * (MIN_PASSWORD_LENGTH - 1))
    assert r.status_code == 422
    with factory() as db:
        assert db.scalar(select(Person).where(Person.id == 2)) is None
    assert client.get(f"/invites/{token}").json()["state"] == "open"


def test_an_unknown_timezone_falls_back_to_utc(
    client: TestClient, factory: sessionmaker[Session], token: str
) -> None:
    assert accept(client, token, timezone="Mars/Olympus_Mons").status_code == 201
    with factory() as db:
        assert db.scalar(select(Person.timezone).where(Person.id == 2)) == "UTC"
