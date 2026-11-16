"""SCRUM-19: real submission API tests against PostgreSQL.

Each test runs inside a transaction that is rolled back afterward.
"""

import os
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import ratelimit
import sessions
from db import as_psycopg_url, get_db
from main import app
from models import Assignment, Membership, Organization, Person, Submission, Team
from security import hash_password
from sessions import NOT_ALLOWED

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="needs PostgreSQL at DATABASE_URL",
)

PASSWORD = "correct horse battery staple"
MEMBER = "member.scrum19@example.com"
OTHER_MEMBER = "other.scrum19@example.com"
SUPERVISOR = "supervisor.scrum19@example.com"
OUTSIDER = "outsider.scrum19@example.com"


@dataclass(frozen=True)
class World:
    assignment_id: int
    member_id: int


@pytest.fixture
def db() -> Iterator[Session]:
    engine = create_engine(as_psycopg_url(os.environ["DATABASE_URL"]))

    with engine.connect() as connection:
        outer = connection.begin()
        session = Session(
            bind=connection,
            join_transaction_mode="create_savepoint",
        )

        try:
            yield session
        finally:
            session.close()
            outer.rollback()

    engine.dispose()


def create_membership(
    db: Session,
    org: Organization,
    email: str,
    role: str,
    team: Team | None = None,
) -> Membership:
    person = Person(
        email=email,
        full_name=email.split("@")[0],
        password_hash=hash_password(PASSWORD),
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
def world(db: Session) -> World:
    org = Organization(name="SCRUM-19 Test Org", slug="scrum19-test")
    outside_org = Organization(
        name="SCRUM-19 Outside Org",
        slug="scrum19-outside",
    )
    db.add_all([org, outside_org])
    db.flush()

    team = Team(organization_id=org.id, name="Design")
    db.add(team)
    db.flush()

    supervisor = create_membership(db, org, SUPERVISOR, "supervisor", team)
    member = create_membership(db, org, MEMBER, "member", team)
    create_membership(db, org, OTHER_MEMBER, "member", team)
    create_membership(db, outside_org, OUTSIDER, "member")

    assignment = Assignment(
        organization_id=org.id,
        created_by_membership_id=supervisor.id,
        recipient_membership_ids=[member.id],
        title="SCRUM-19 Test Assignment",
        points_value=15,
        is_mandatory=True,
        late_policy="accepted_full_points",
        due_at=sessions.now() + timedelta(days=1),
    )
    db.add(assignment)
    db.flush()

    return World(
        assignment_id=assignment.id,
        member_id=member.id,
    )


@pytest.fixture
def client(db: Session, world: World) -> Iterator[TestClient]:
    def override_db() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_db] = override_db
    ratelimit.by_account._events.clear()
    ratelimit.by_ip._events.clear()

    try:
        with TestClient(app, base_url="https://testserver") as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def sign_in(client: TestClient, email: str = MEMBER) -> None:
    response = client.post(
        "/auth/sign-in",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 200


def submit(
    client: TestClient,
    world: World,
    kind: str = "text",
    content: str = "My completed assignment",
) -> Response:
    return client.post(
        f"/assignments/{world.assignment_id}/submissions",
        json={"kind": kind, "content": content},
    )


@pytest.mark.parametrize(
    ("kind", "content"),
    [
        ("text", "My completed assignment"),
        ("link", "https://example.com/my-work"),
        ("pr", "https://github.com/owner/repo/pull/123"),
    ],
)
def test_successful_submission_is_saved(
    client: TestClient,
    db: Session,
    world: World,
    kind: str,
    content: str,
) -> None:
    sign_in(client)
    response = submit(client, world, kind, content)

    assert response.status_code == 201, response.text

    result = response.json()
    assert result["assignment_id"] == world.assignment_id
    assert result["version"] == 1
    assert result["kind"] == kind
    assert result["content"] == content
    assert result["status"] == "submitted"
    assert response.headers["cache-control"] == "no-store"

    saved = db.get(Submission, result["id"])
    assert saved is not None
    assert saved.membership_id == world.member_id
    assert saved.assignment_id == world.assignment_id
    assert saved.submission_kind == kind
    assert saved.content == content

    history = client.get(f"/submissions/{result['id']}")
    assert history.status_code == 200, history.text
    version = history.json()["versions"][0]
    assert version["submission_kind"] == kind
    assert version["content"] == content


def test_submission_updates_my_work(
    client: TestClient,
    world: World,
) -> None:
    sign_in(client)
    submitted = submit(client, world)
    assert submitted.status_code == 201

    response = client.get("/me/work")
    assert response.status_code == 200

    items = [
        item
        for group in response.json()["groups"]
        for item in group["items"]
        if item["id"] == world.assignment_id
    ]

    assert len(items) == 1
    assert items[0]["status"] == "submitted"
    assert items[0]["submission_id"] == submitted.json()["id"]


def test_duplicate_submission_is_rejected(
    client: TestClient,
    db: Session,
    world: World,
) -> None:
    sign_in(client)

    first = submit(client, world)
    second = submit(client, world)

    assert first.status_code == 201
    assert second.status_code == 409

    saved = db.scalars(
        select(Submission).where(Submission.assignment_id == world.assignment_id)
    ).all()
    assert len(saved) == 1


def test_signed_out_user_cannot_submit(
    client: TestClient,
    world: World,
) -> None:
    response = submit(client, world)
    assert response.status_code == 401


@pytest.mark.parametrize(
    "email",
    [OTHER_MEMBER, SUPERVISOR, OUTSIDER],
)
def test_unassigned_users_cannot_submit(
    client: TestClient,
    world: World,
    email: str,
) -> None:
    sign_in(client, email)
    response = submit(client, world)

    assert response.status_code == 403
    assert response.json() == {"detail": NOT_ALLOWED}


def test_missing_assignment_is_forbidden(
    client: TestClient,
) -> None:
    sign_in(client)

    response = client.post(
        "/assignments/999999999/submissions",
        json={"kind": "text", "content": "Hello"},
    )
    assert response.status_code == 403


def test_closed_deadline_rejects_submission(
    client: TestClient,
    db: Session,
    world: World,
) -> None:
    assignment = db.get(Assignment, world.assignment_id)
    assignment.due_at = sessions.now() - timedelta(days=1)
    assignment.late_policy = "not_accepted"
    db.flush()

    sign_in(client)
    response = submit(client, world)

    assert response.status_code == 409


def test_allowed_late_work_is_accepted(
    client: TestClient,
    db: Session,
    world: World,
) -> None:
    assignment = db.get(Assignment, world.assignment_id)
    assignment.due_at = sessions.now() - timedelta(hours=1)
    assignment.late_policy = "accepted_half_points"
    assignment.late_cutoff_hours = 48
    db.flush()

    sign_in(client)
    response = submit(client, world)

    assert response.status_code == 201, response.text

    groups = client.get("/me/work").json()["groups"]
    item = next(
        item for group in groups for item in group["items"] if item["id"] == world.assignment_id
    )
    assert item["handed_in_late"] is True


@pytest.mark.parametrize(
    ("kind", "content"),
    [
        ("text", "  "),
        ("text", "a" * 20001),
        ("link", "not-a-url"),
        ("pr", "https://github.com/owner/repo/issues/12"),
        ("file", "assignment.pdf"),
    ],
)
def test_invalid_payloads_are_rejected(
    client: TestClient,
    db: Session,
    world: World,
    kind: str,
    content: str,
) -> None:
    sign_in(client)
    response = submit(client, world, kind, content)

    assert response.status_code == 422

    saved = db.scalars(
        select(Submission).where(Submission.assignment_id == world.assignment_id)
    ).all()
    assert saved == []
