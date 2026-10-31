"""SCRUM-17: GET and PATCH /me/profile feed the profile page (P18).

Runs on SQLite like test_home.py. The byline-consent stamp is written with
sessions.now(), which the clock fixture replaces so the tests can move time.
"""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import assignments
import ratelimit
import sessions
from db import Base, get_db
from main import app
from models import AuthSession, Cohort, Membership, Organization, Person, Team, Track
from routers.me import NO_MEMBERSHIP
from security import hash_password

PASSWORD = "correct horse battery staple"
INTERN = "amara.okafor@example.com"
LONER = "no.org@example.com"

# What a fresh member sees: the database defaults, plus the person's own name and zone.
DEFAULT_PROFILE = {
    "full_name": "Amara Okafor",
    "email": INTERN,
    "photo_url": None,
    "timezone": "Africa/Lagos",
    "contact_preference": "email",
    "contact_detail": None,
    "email_assignments": True,
    "email_reminders": True,
    "email_digest": True,
    "public_byline_consent": False,
    "public_byline_consent_at": None,
}


@pytest.fixture
def factory() -> sessionmaker[Session]:
    """One organization with one intern, plus a person who belongs to nothing."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    tables = [Organization, Person, Team, Cohort, Track, Membership, AuthSession]
    Base.metadata.create_all(engine, tables=[model.__table__ for model in tables])
    factory = sessionmaker(bind=engine)
    with factory() as db:
        db.add(Organization(id=1, name="The Emerson Empire", slug="emerson"))
        db.add_all(
            [
                Person(
                    id=1,
                    email=INTERN,
                    full_name="Amara Okafor",
                    timezone="Africa/Lagos",
                    password_hash=hash_password(PASSWORD),
                ),
                Person(
                    id=2,
                    email=LONER,
                    full_name="No Org",
                    timezone="UTC",
                    password_hash=hash_password(PASSWORD),
                ),
            ]
        )
        db.add(Membership(id=1, person_id=1, organization_id=1, role="member"))
        db.commit()
    return factory


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


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> dict[str, datetime]:
    """Move sessions.now(). Starts a minute ahead so a sign-in stays inside the idle limit."""
    state = {"now": datetime.now(UTC) + timedelta(minutes=1)}
    monkeypatch.setattr(sessions, "now", lambda: state["now"])
    return state


def sign_in(client: TestClient, email: str = INTERN) -> None:
    r = client.post("/auth/sign-in", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200


def moment(value: str) -> datetime:
    return datetime.fromisoformat(value)


def test_profile_returns_every_field(client: TestClient) -> None:
    sign_in(client)
    r = client.get("/me/profile")
    assert r.status_code == 200
    assert r.json() == DEFAULT_PROFILE
    assert r.headers["cache-control"] == "no-store"


def test_profile_needs_a_session(client: TestClient) -> None:
    assert client.get("/me/profile").status_code == 401
    assert client.patch("/me/profile", json={"full_name": "Someone"}).status_code == 401


def test_someone_with_no_organization_gets_a_plain_404(client: TestClient) -> None:
    sign_in(client, LONER)
    for r in (
        client.get("/me/profile"),
        client.patch("/me/profile", json={"full_name": "Nobody"}),
    ):
        assert r.status_code == 404
        assert r.json() == {"detail": NO_MEMBERSHIP}


def test_patch_changes_name_and_timezone(client: TestClient) -> None:
    sign_in(client)
    r = client.patch(
        "/me/profile",
        json={"full_name": "  Amara N. Okafor ", "timezone": "America/Los_Angeles"},
    )
    assert r.status_code == 200
    expected = {
        **DEFAULT_PROFILE,
        "full_name": "Amara N. Okafor",
        "timezone": "America/Los_Angeles",
    }
    assert r.json() == expected
    assert r.headers["cache-control"] == "no-store"
    assert client.get("/me/profile").json() == expected


def test_a_new_timezone_reaches_the_home_screen(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(assignments, "has_assigned_work", lambda db, member: False)
    sign_in(client)
    assert client.get("/me/home").json()["timezone"] == "Africa/Lagos"
    assert client.patch("/me/profile", json={"timezone": "Asia/Tokyo"}).status_code == 200
    assert client.get("/me/home").json()["timezone"] == "Asia/Tokyo"


def test_unknown_timezone_is_422_and_nothing_changes(client: TestClient) -> None:
    sign_in(client)
    r = client.patch("/me/profile", json={"full_name": "Changed", "timezone": "Mars/Olympus_Mons"})
    assert r.status_code == 422
    assert client.get("/me/profile").json() == DEFAULT_PROFILE


def test_consent_on_stamps_and_off_keeps_the_stamp(
    client: TestClient, clock: dict[str, datetime]
) -> None:
    sign_in(client)
    stamp = clock["now"]
    on = client.patch("/me/profile", json={"public_byline_consent": True}).json()
    assert on["public_byline_consent"] is True
    assert moment(on["public_byline_consent_at"]) == stamp

    clock["now"] = stamp + timedelta(minutes=5)
    off = client.patch("/me/profile", json={"public_byline_consent": False}).json()
    assert off["public_byline_consent"] is False
    assert moment(off["public_byline_consent_at"]) == stamp

    after = client.get("/me/profile").json()
    assert after["public_byline_consent"] is False
    assert moment(after["public_byline_consent_at"]) == stamp


def test_consent_sent_twice_does_not_move_the_stamp(
    client: TestClient, clock: dict[str, datetime]
) -> None:
    sign_in(client)
    first = clock["now"]
    client.patch("/me/profile", json={"public_byline_consent": True})
    clock["now"] = first + timedelta(minutes=5)
    again = client.patch("/me/profile", json={"public_byline_consent": True}).json()
    assert again["public_byline_consent"] is True
    assert moment(again["public_byline_consent_at"]) == first


def test_contact_preference_outside_the_three_is_422(client: TestClient) -> None:
    sign_in(client)
    r = client.patch("/me/profile", json={"contact_preference": "carrier pigeon"})
    assert r.status_code == 422
    assert client.get("/me/profile").json()["contact_preference"] == "email"


def test_discord_and_a_trimmed_detail_are_saved(client: TestClient) -> None:
    sign_in(client)
    r = client.patch(
        "/me/profile",
        json={"contact_preference": "discord", "contact_detail": "  amara_o  "},
    )
    assert r.status_code == 200
    assert r.json()["contact_preference"] == "discord"
    assert r.json()["contact_detail"] == "amara_o"


def test_email_cannot_be_changed_through_patch(client: TestClient) -> None:
    sign_in(client)
    r = client.patch(
        "/me/profile", json={"email": "someone.else@example.com", "full_name": "Amara O."}
    )
    assert r.status_code == 200
    assert r.json()["email"] == INTERN
    assert r.json()["full_name"] == "Amara O."
    assert client.get("/me/profile").json()["email"] == INTERN


def test_a_partial_patch_leaves_other_fields_alone(client: TestClient) -> None:
    sign_in(client)
    client.patch(
        "/me/profile",
        json={
            "photo_url": "https://example.com/amara.png",
            "email_digest": False,
            "contact_preference": "phone",
            "contact_detail": "555-0100",
        },
    )
    r = client.patch("/me/profile", json={"timezone": "Asia/Tokyo"})
    assert r.status_code == 200
    assert r.json() == {
        **DEFAULT_PROFILE,
        "photo_url": "https://example.com/amara.png",
        "email_digest": False,
        "contact_preference": "phone",
        "contact_detail": "555-0100",
        "timezone": "Asia/Tokyo",
    }


def test_photo_must_be_https_and_null_clears_it(client: TestClient) -> None:
    sign_in(client)
    for bad in ("http://example.com/a.png", "not a link", "https://", ""):
        assert client.patch("/me/profile", json={"photo_url": bad}).status_code == 422
    r = client.patch("/me/profile", json={"photo_url": "https://example.com/a.png"})
    assert r.json()["photo_url"] == "https://example.com/a.png"
    cleared = client.patch("/me/profile", json={"photo_url": None})
    assert cleared.status_code == 200
    assert cleared.json()["photo_url"] is None


def test_a_blank_or_null_name_is_422(client: TestClient) -> None:
    sign_in(client)
    for bad in ("", "   ", None, "x" * 201):
        assert client.patch("/me/profile", json={"full_name": bad}).status_code == 422
    assert client.get("/me/profile").json()["full_name"] == "Amara Okafor"


def test_email_preferences_toggle_and_must_be_true_or_false(client: TestClient) -> None:
    sign_in(client)
    r = client.patch("/me/profile", json={"email_assignments": False, "email_reminders": False})
    assert r.status_code == 200
    body = r.json()
    assert (body["email_assignments"], body["email_reminders"], body["email_digest"]) == (
        False,
        False,
        True,
    )
    assert client.patch("/me/profile", json={"email_digest": "maybe"}).status_code == 422
