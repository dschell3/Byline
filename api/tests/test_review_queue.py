"""SCRUM-24: the review queue, GET /review/queue.

Needs Postgres (assignments and submissions use arrays), so these run when
DATABASE_URL is set and skip otherwise, like test_assignment_page.py. Everything
happens inside one transaction that is rolled back.
"""

import os
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import ratelimit
from db import as_psycopg_url, get_db
from main import app
from models import Assignment, Membership, Organization, Person, Submission, Team
from security import hash_password
from sessions import NOT_ALLOWED

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"), reason="needs a Postgres at DATABASE_URL"
)

PASSWORD = "correct horse battery staple"
NOW = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)

SUPERVISOR = "marguerite.scrum24@example.com"
OTHER_SUPERVISOR = "paul.scrum24@example.com"
ADMIN = "ada.scrum24@example.com"
INTERN = "amara.scrum24@example.com"


@dataclass
class World:
    design_work: list[Submission]  # oldest first
    web_work: Submission
    assignment: Assignment


def _member(db: Session, org: Organization, team: Team | None, email: str, role: str) -> Membership:
    person = Person(
        email=email, full_name=email.split("@")[0], password_hash=hash_password(PASSWORD)
    )
    db.add(person)
    db.flush()
    m = Membership(
        person_id=person.id, organization_id=org.id, role=role, team_id=team.id if team else None
    )
    db.add(m)
    db.flush()
    return m


def _submit(
    db: Session, assignment: Assignment, m: Membership, version: int, age_hours: int, status: str
) -> Submission:
    s = Submission(
        assignment_id=assignment.id,
        membership_id=m.id,
        version=version,
        submission_kind="text",
        content="work",
        status=status,
        submitted_at=NOW - timedelta(hours=age_hours),
    )
    db.add(s)
    db.flush()
    return s


@pytest.fixture
def db() -> Iterator[Session]:
    engine = create_engine(as_psycopg_url(os.environ["DATABASE_URL"]))
    with engine.connect() as connection:
        outer = connection.begin()
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            session.close()
            outer.rollback()


@pytest.fixture
def world(db: Session) -> World:
    org = Organization(name="Queue Org", slug="queue-org-scrum24")
    db.add(org)
    db.flush()
    design, web = (
        Team(organization_id=org.id, name="Design"),
        Team(organization_id=org.id, name="Web"),
    )
    db.add_all([design, web])
    db.flush()
    boss = _member(db, org, design, SUPERVISOR, "supervisor")
    _member(db, org, web, OTHER_SUPERVISOR, "supervisor")
    _member(db, org, None, ADMIN, "admin")
    amara = _member(db, org, design, INTERN, "member")
    bola = _member(db, org, design, "bola.scrum24@example.com", "member")
    chidi = _member(db, org, web, "chidi.scrum24@example.com", "member")
    assignment = Assignment(
        organization_id=org.id,
        created_by_membership_id=boss.id,
        title="Landing page copy",
        points_value=20,
        late_policy="accepted_full_points",
    )
    db.add(assignment)
    db.flush()
    # Handed in out of order on purpose: the queue must sort them, not the insert order.
    newer = _submit(db, assignment, bola, 1, 5, "submitted")
    older = _submit(db, assignment, amara, 1, 30, "submitted")
    web_work = _submit(db, assignment, chidi, 1, 10, "submitted")
    return World(design_work=[older, newer], web_work=web_work, assignment=assignment)


@pytest.fixture
def client(db: Session, world: World) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    ratelimit.by_account._events.clear()
    ratelimit.by_ip._events.clear()
    try:
        yield TestClient(app, base_url="https://testserver")
    finally:
        app.dependency_overrides.clear()


def sign_in(client: TestClient, email: str) -> None:
    r = client.post("/auth/sign-in", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200


def ids(body: dict) -> list[int]:
    return [row["submission_id"] for row in body["rows"]]


def test_oldest_waiting_work_comes_first(client: TestClient, world: World) -> None:
    sign_in(client, SUPERVISOR)
    r = client.get("/review/queue")
    assert r.status_code == 200
    assert r.headers["Cache-Control"] == "no-store"
    assert ids(r.json()) == [s.id for s in world.design_work]


def test_each_row_says_who_what_when_and_which_team(client: TestClient, world: World) -> None:
    sign_in(client, SUPERVISOR)
    row = client.get("/review/queue").json()["rows"][0]
    assert row["intern_name"] == "amara.scrum24"
    assert row["assignment_title"] == "Landing page copy"
    assert row["team_name"] == "Design"
    assert row["status"] == "submitted"
    assert row["submitted_at"]


def test_a_supervisor_only_sees_their_own_team(client: TestClient, world: World) -> None:
    sign_in(client, SUPERVISOR)
    assert world.web_work.id not in ids(client.get("/review/queue").json())
    client.post("/auth/sign-out")
    sign_in(client, OTHER_SUPERVISOR)
    assert ids(client.get("/review/queue").json()) == [world.web_work.id]


def test_an_admin_sees_every_team(client: TestClient, world: World) -> None:
    sign_in(client, ADMIN)
    assert len(ids(client.get("/review/queue").json())) == 3


def test_interns_are_turned_away(client: TestClient) -> None:
    sign_in(client, INTERN)
    r = client.get("/review/queue")
    assert r.status_code == 403
    assert r.json()["detail"] == NOT_ALLOWED


def test_signed_out_is_401(client: TestClient) -> None:
    assert client.get("/review/queue").status_code == 401


def test_a_resubmission_replaces_the_old_row(client: TestClient, db: Session, world: World) -> None:
    old = world.design_work[0]
    new = _submit(db, world.assignment, db.get(Membership, old.membership_id), 2, 1, "submitted")
    old.status = "changes_requested"
    db.flush()
    sign_in(client, SUPERVISOR)
    got = ids(client.get("/review/queue").json())
    assert old.id not in got
    assert new.id in got


def test_status_filter_and_default(client: TestClient, db: Session, world: World) -> None:
    approved = world.design_work[1]
    approved.status = "approved"
    db.flush()
    sign_in(client, SUPERVISOR)
    assert ids(client.get("/review/queue").json()) == [world.design_work[0].id]
    assert ids(client.get("/review/queue?status=approved").json()) == [approved.id]
    assert len(ids(client.get("/review/queue?status=all").json())) == 2


def test_other_filters_narrow_the_rows(client: TestClient, world: World) -> None:
    sign_in(client, SUPERVISOR)
    body = client.get("/review/queue").json()
    team_id = body["rows"][0]["team_id"]
    assert len(ids(client.get(f"/review/queue?team_id={team_id}").json())) == 2
    assert ids(client.get(f"/review/queue?assignment_id={world.assignment.id}").json()) == ids(body)
    assert ids(client.get(f"/review/queue?assignment_id={world.assignment.id + 999}").json()) == []


def test_dropdowns_offer_everything_even_when_filtered(client: TestClient, world: World) -> None:
    sign_in(client, SUPERVISOR)
    body = client.get("/review/queue?status=approved").json()
    assert body["rows"] == []
    assert [t["name"] for t in body["filters"]["teams"]] == ["Design"]
    assert [a["name"] for a in body["filters"]["assignments"]] == ["Landing page copy"]
