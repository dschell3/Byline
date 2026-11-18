"""SCRUM-18: the assignment page endpoint, GET /assignments/{id}.

Needs Postgres (picked recipients are a Postgres array), so these run when
DATABASE_URL is set and skip otherwise, like test_submissions.py. Everything
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
from scripts import seed_assignment as seeding
from security import hash_password
from sessions import NOT_ALLOWED

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"), reason="needs a Postgres at DATABASE_URL"
)

PASSWORD = "correct horse battery staple"

MEMBER = "amara.scrum18@example.com"
OTHER_TEAM_MEMBER = "bola.scrum18@example.com"
SUPERVISOR = "marguerite.scrum18@example.com"
ADMIN = "ada.scrum18@example.com"
OUTSIDER = "other.intern.scrum18@example.com"


@dataclass
class World:
    assignment: Assignment
    member: Membership
    other_team_member: Membership


def _person(db: Session, org: Organization, team: Team | None, email: str, role: str) -> Membership:
    person = Person(
        email=email, full_name=email.split("@")[0], password_hash=hash_password(PASSWORD)
    )
    db.add(person)
    db.flush()
    membership = Membership(
        person_id=person.id,
        organization_id=org.id,
        role=role,
        team_id=team.id if team else None,
    )
    db.add(membership)
    db.flush()
    return membership


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
    """The seeded assignment, set for team Design; a second team and a second organization."""
    org = Organization(name="Seeded Org", slug="seeded-org-scrum18")
    db.add(org)
    db.flush()
    design, web = (
        Team(organization_id=org.id, name="Design"),
        Team(organization_id=org.id, name="Web"),
    )
    db.add_all([design, web])
    db.flush()
    supervisor = _person(db, org, design, SUPERVISOR, "supervisor")
    member = _person(db, org, design, MEMBER, "member")
    other_team_member = _person(db, org, web, OTHER_TEAM_MEMBER, "member")
    _person(db, org, None, ADMIN, "admin")
    elsewhere = Organization(name="Elsewhere", slug="elsewhere-scrum18")
    db.add(elsewhere)
    db.flush()
    _person(db, elsewhere, None, OUTSIDER, "member")
    assignment = seeding.seed(db, org, design, supervisor)
    db.flush()
    return World(assignment=assignment, member=member, other_team_member=other_team_member)


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


def get(client: TestClient, world: World) -> dict:
    r = client.get(f"/assignments/{world.assignment.id}")
    assert r.status_code == 200
    return r.json()


# --- what the page shows ------------------------------------------------------------------


def test_the_member_sees_the_heading_facts(client: TestClient, world: World) -> None:
    sign_in(client, MEMBER)
    r = client.get(f"/assignments/{world.assignment.id}")
    assert r.status_code == 200
    assert r.headers["Cache-Control"] == "no-store"
    body = r.json()
    assert body["title"] == seeding.ASSIGNMENT_TITLE
    assert body["set_by"] == SUPERVISOR.split("@")[0]
    assert body["set_at"] is not None
    assert body["due_at"] is not None
    assert body["points"] == seeding.POINTS
    assert body["is_mandatory"] is True
    assert body["description"] == seeding.DESCRIPTION
    assert body["status"] == "due-soon"


def test_criteria_come_as_a_checklist_in_position_order(client: TestClient, world: World) -> None:
    sign_in(client, MEMBER)
    criteria = get(client, world)["criteria"]
    assert [c["position"] for c in criteria] == [1, 2, 3, 4]
    assert [(c["text"], c["detail"], c["max_points"]) for c in criteria] == seeding.CRITERIA
    assert sum(c["max_points"] for c in criteria) == seeding.POINTS


def test_reference_links_and_attachments_are_listed(client: TestClient, world: World) -> None:
    sign_in(client, MEMBER)
    body = get(client, world)
    assert body["reference_links"] == seeding.REFERENCE_LINKS
    assert body["attachments"] == [
        {"name": a["name"], "size_bytes": a["size_bytes"]} for a in seeding.ATTACHMENTS
    ]


def test_a_link_that_is_not_http_never_reaches_the_page(
    client: TestClient, world: World, db: Session
) -> None:
    world.assignment.reference_links = [
        {"label": "Bad", "url": "javascript:alert(1)"},
        {"label": "", "url": "https://example.org/brief"},
    ]
    db.flush()
    sign_in(client, MEMBER)
    assert get(client, world)["reference_links"] == [
        {"label": "https://example.org/brief", "url": "https://example.org/brief"}
    ]


def test_an_assignment_with_nothing_extra_sends_empty_lists(
    client: TestClient, world: World, db: Session
) -> None:
    world.assignment.description = None
    world.assignment.reference_links = None
    world.assignment.attachments = None
    db.flush()
    sign_in(client, MEMBER)
    body = get(client, world)
    assert body["description"] is None
    assert body["reference_links"] == []
    assert body["attachments"] == []


def test_the_late_policy_fields_are_the_ones_my_work_carries(
    client: TestClient, world: World
) -> None:
    sign_in(client, MEMBER)
    body = get(client, world)
    assert body["late_policy"] == "accepted_half_points"
    assert body["late_cutoff_hours"] == seeding.LATE_CUTOFF_HOURS
    work_item = next(
        item
        for group in client.get("/me/work").json()["groups"]
        for item in group["items"]
        if item["id"] == world.assignment.id
    )
    for field in ("due_at", "late_policy", "late_cutoff_hours", "status", "points"):
        assert body[field] == work_item[field]


# --- which button -------------------------------------------------------------------------


def test_the_submit_kind_the_supervisor_asked_for_is_on_the_page(
    client: TestClient, db: Session, world: World
) -> None:
    sign_in(client, MEMBER)
    assert client.get(f"/assignments/{world.assignment.id}").json()["submission_kind"] is None
    world.assignment.submission_kind = "file"
    db.flush()
    assert client.get(f"/assignments/{world.assignment.id}").json()["submission_kind"] == "file"


def test_with_no_submission_the_page_offers_submit(client: TestClient, world: World) -> None:
    sign_in(client, MEMBER)
    body = get(client, world)
    assert body["submission_id"] is None
    assert body["can_submit"] is True


def test_with_a_submission_the_page_links_to_the_latest_version(
    client: TestClient, world: World, db: Session
) -> None:
    for version in (1, 2):
        db.add(
            Submission(
                assignment_id=world.assignment.id,
                membership_id=world.member.id,
                version=version,
                status="submitted",
            )
        )
    db.flush()
    latest = db.query(Submission).filter_by(membership_id=world.member.id, version=2).one()
    sign_in(client, MEMBER)
    body = get(client, world)
    assert body["submission_id"] == latest.id
    assert body["status"] == "submitted"


def test_once_the_late_cutoff_has_passed_it_cannot_be_submitted(
    client: TestClient, world: World, db: Session
) -> None:
    world.assignment.due_at = datetime.now(UTC) - timedelta(hours=seeding.LATE_CUTOFF_HOURS + 1)
    db.flush()
    sign_in(client, MEMBER)
    body = get(client, world)
    assert body["status"] == "overdue"
    assert body["can_submit"] is False


def test_overdue_inside_the_late_window_can_still_be_submitted(
    client: TestClient, world: World, db: Session
) -> None:
    world.assignment.due_at = datetime.now(UTC) - timedelta(hours=1)
    db.flush()
    sign_in(client, MEMBER)
    body = get(client, world)
    assert body["status"] == "overdue"
    assert body["can_submit"] is True


# --- who may look -------------------------------------------------------------------------


# The supervisor is left out: they are on team Design, so the shared assigned_to rule reaches
# them too, exactly as it does on My Work.
@pytest.mark.parametrize("email", [OTHER_TEAM_MEMBER, OUTSIDER, ADMIN])
def test_anyone_it_was_not_targeted_at_gets_403(
    client: TestClient, world: World, email: str
) -> None:
    sign_in(client, email)
    r = client.get(f"/assignments/{world.assignment.id}")
    assert r.status_code == 403
    assert r.json()["detail"] == NOT_ALLOWED


def test_a_picked_recipient_on_another_team_can_open_it(
    client: TestClient, world: World, db: Session
) -> None:
    world.assignment.recipient_membership_ids = [world.other_team_member.id]
    db.flush()
    sign_in(client, OTHER_TEAM_MEMBER)
    assert client.get(f"/assignments/{world.assignment.id}").status_code == 200


def test_a_missing_id_looks_exactly_like_forbidden(client: TestClient, world: World) -> None:
    sign_in(client, MEMBER)
    r = client.get("/assignments/999999999")
    assert r.status_code == 403
    assert r.json()["detail"] == NOT_ALLOWED


def test_signed_out_gets_401(client: TestClient, world: World) -> None:
    assert client.get(f"/assignments/{world.assignment.id}").status_code == 401
