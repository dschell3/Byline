"""SCRUM-16: GET /me/home feeds the first-run screen (P11).

Runs on SQLite like test_sessions.py. Whether work exists is decided by
assignments.has_assigned_work, which needs Postgres arrays; it is replaced
here and tested on its own in test_assignments.py.
"""

from collections.abc import Iterator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, update
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import assignments
import ratelimit
from db import Base, get_db
from main import app
from models import AuthSession, Cohort, Membership, Organization, Person, Team, Track
from routers.me import NO_MEMBERSHIP
from security import hash_password

PASSWORD = "correct horse battery staple"
INTERN = "amara.okafor@example.com"
LONER = "no.org@example.com"


@pytest.fixture
def factory() -> sessionmaker[Session]:
    """One organization: a supervisor and an intern on the same team, plus a second team."""
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
                Team(id=1, organization_id=1, name="Design"),
                Team(id=2, organization_id=1, name="Web"),
            ]
        )
        db.add(
            Cohort(
                id=1,
                organization_id=1,
                name="Autumn 2026 · Cohort 7",
                starts_on=date(2026, 9, 28),
                ends_on=date(2026, 12, 18),
            )
        )
        db.add(
            Track(
                id=1, organization_id=1, name="UX/UI", onboarding_pack_url="https://example.com/ux"
            )
        )
        people = [
            (1, INTERN, "Amara Okafor", "Africa/Lagos"),
            (2, "marguerite@example.com", "Marguerite Ellis", "UTC"),
            (3, "other.lead@example.com", "Other Lead", "UTC"),
            (4, LONER, "No Org", "UTC"),
        ]
        for person_id, email, name, timezone in people:
            db.add(
                Person(
                    id=person_id,
                    email=email,
                    full_name=name,
                    timezone=timezone,
                    password_hash=hash_password(PASSWORD),
                )
            )
        db.add_all(
            [
                Membership(
                    id=1,
                    person_id=1,
                    organization_id=1,
                    role="member",
                    team_id=1,
                    cohort_id=1,
                    track_id=1,
                ),
                Membership(id=2, person_id=2, organization_id=1, role="supervisor", team_id=1),
                Membership(id=3, person_id=3, organization_id=1, role="supervisor", team_id=2),
            ]
        )
        db.commit()
    return factory


@pytest.fixture
def client(factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        with factory() as db:
            yield db

    monkeypatch.setattr(assignments, "has_assigned_work", lambda db, member: False)
    app.dependency_overrides[get_db] = override_get_db
    ratelimit.by_account._events.clear()
    ratelimit.by_ip._events.clear()
    try:
        yield TestClient(app, base_url="https://testserver")
    finally:
        app.dependency_overrides.clear()


def sign_in(client: TestClient, email: str = INTERN) -> None:
    r = client.post("/auth/sign-in", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200


def test_home_shows_organization_cohort_track_and_supervisor(client: TestClient) -> None:
    sign_in(client)
    r = client.get("/me/home")
    assert r.status_code == 200
    assert r.json() == {
        "full_name": "Amara Okafor",
        "timezone": "Africa/Lagos",
        "organization": {"name": "The Emerson Empire"},
        "cohort": {
            "name": "Autumn 2026 · Cohort 7",
            "starts_on": "2026-09-28",
            "ends_on": "2026-12-18",
        },
        "track": {"name": "UX/UI", "onboarding_pack_url": "https://example.com/ux"},
        "supervisor": {"full_name": "Marguerite Ellis", "email": "marguerite@example.com"},
        "has_work": False,
    }
    assert r.headers["cache-control"] == "no-store"


def test_has_work_comes_from_the_shared_assignment_rule(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(assignments, "has_assigned_work", lambda db, member: member.id == 1)
    sign_in(client)
    assert client.get("/me/home").json()["has_work"] is True


def test_no_team_means_no_supervisor_yet(
    client: TestClient, factory: sessionmaker[Session]
) -> None:
    with factory() as db:
        db.execute(update(Membership).where(Membership.id == 1).values(team_id=None))
        db.commit()
    sign_in(client)
    assert client.get("/me/home").json()["supervisor"] is None


def test_an_inactive_supervisor_is_not_shown(
    client: TestClient, factory: sessionmaker[Session]
) -> None:
    with factory() as db:
        db.execute(update(Membership).where(Membership.id == 2).values(is_active=False))
        db.commit()
    sign_in(client)
    # The other team's supervisor must not be offered in their place.
    assert client.get("/me/home").json()["supervisor"] is None


def test_cohort_and_track_are_optional(client: TestClient, factory: sessionmaker[Session]) -> None:
    with factory() as db:
        db.execute(
            update(Membership).where(Membership.id == 1).values(cohort_id=None, track_id=None)
        )
        db.commit()
    sign_in(client)
    body = client.get("/me/home").json()
    assert body["cohort"] is None
    assert body["track"] is None


def test_someone_with_no_organization_gets_a_plain_404(client: TestClient) -> None:
    sign_in(client, LONER)
    r = client.get("/me/home")
    assert r.status_code == 404
    assert r.json() == {"detail": NO_MEMBERSHIP}


def test_home_needs_a_session(client: TestClient) -> None:
    assert client.get("/me/home").status_code == 401
