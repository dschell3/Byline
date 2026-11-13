"""SCRUM-22: the submission history endpoint and its comment thread.

These need Postgres (the seed writes an assignment, whose picked-members
column is an array), so they run when DATABASE_URL is set and skip otherwise,
like test_ledger.py. Everything happens inside one transaction that is rolled
back, so the database is left as it was.
"""

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import ratelimit
from db import as_psycopg_url, get_db
from main import app
from models import Membership, Organization, Person, Review, Team
from scripts import seed_submission as seeding
from scripts.seed_submission import Seeded
from security import hash_password
from sessions import NOT_ALLOWED

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"), reason="needs a Postgres at DATABASE_URL"
)

PASSWORD = "correct horse battery staple"

MEMBER = "amara.scrum22@example.com"
OTHER_MEMBER = "bola.scrum22@example.com"
SUPERVISOR = "marguerite.scrum22@example.com"
ADMIN = "ada.scrum22@example.com"
OUTSIDER = "other.lead.scrum22@example.com"


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
def seeded(db: Session) -> Seeded:
    """One org with the seeded history, plus an admin, a second member and an outsider."""
    org = Organization(name="Seeded Org", slug="seeded-org-scrum22")
    db.add(org)
    db.flush()
    team = Team(organization_id=org.id, name="Design")
    db.add(team)
    db.flush()
    supervisor = _person(db, org, team, SUPERVISOR, "supervisor")
    member = _person(db, org, team, MEMBER, "member")
    _person(db, org, team, OTHER_MEMBER, "member")
    _person(db, org, None, ADMIN, "admin")
    elsewhere = Organization(name="Elsewhere", slug="elsewhere-scrum22")
    db.add(elsewhere)
    db.flush()
    _person(db, elsewhere, None, OUTSIDER, "supervisor")
    result = seeding.seed(db, org, team, supervisor, member)
    db.flush()
    return result


@pytest.fixture
def client(db: Session, seeded: Seeded) -> Iterator[TestClient]:
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


# --- reading ------------------------------------------------------------------------------


def test_the_member_sees_every_version_oldest_first(client: TestClient, seeded: Seeded) -> None:
    sign_in(client, MEMBER)
    r = client.get(f"/submissions/{seeded.version2_id}")
    assert r.status_code == 200
    assert r.headers["cache-control"] == "no-store"
    body = r.json()
    assert body["id"] == seeded.version2_id
    assert body["assignment"]["title"] == seeding.ASSIGNMENT_TITLE
    assert [v["version"] for v in body["versions"]] == [1, 2]
    assert [v["id"] for v in body["versions"]] == [seeded.version1_id, seeded.version2_id]
    assert [v["status"] for v in body["versions"]] == ["changes_requested", "submitted"]


def test_asking_for_version_one_gives_the_same_history(client: TestClient, seeded: Seeded) -> None:
    sign_in(client, MEMBER)
    one = client.get(f"/submissions/{seeded.version1_id}").json()
    two = client.get(f"/submissions/{seeded.version2_id}").json()
    assert one["versions"] == two["versions"]
    assert one["id"] == seeded.version1_id


def test_a_review_carries_who_what_when_why_and_the_scores(
    client: TestClient, seeded: Seeded
) -> None:
    sign_in(client, MEMBER)
    versions = client.get(f"/submissions/{seeded.version1_id}").json()["versions"]
    (review,) = versions[0]["reviews"]
    assert review["decision"] == "changes_requested"
    assert review["reason"] == seeding.REASON
    assert review["is_final"] is True
    assert review["actor_name"] == SUPERVISOR.split("@")[0]
    assert [s["position"] for s in review["scores"]] == [1, 2, 3, 4]
    assert [s["score"] for s in review["scores"]] == seeding.SCORES
    assert [s["max_points"] for s in review["scores"]] == [5, 5, 5, 5]
    assert review["scores"][1]["note"] == "Stops at sign-up"
    assert versions[1]["reviews"] == []


def test_comments_come_oldest_first_with_their_parent(client: TestClient, seeded: Seeded) -> None:
    sign_in(client, MEMBER)
    versions = client.get(f"/submissions/{seeded.version1_id}").json()["versions"]
    first, reply = versions[0]["comments"]
    assert first["parent_comment_id"] is None
    assert reply["parent_comment_id"] == first["id"]
    assert first["author_name"] == MEMBER.split("@")[0]
    assert reply["author_name"] == SUPERVISOR.split("@")[0]
    assert versions[1]["comments"] == []


def test_a_draft_review_is_hidden_from_the_member_until_a_person_acts(
    client: TestClient, seeded: Seeded, db: Session
) -> None:
    """An AI draft (is_final = false) is for the supervisor; the member sees finals only."""
    db.add(
        Review(
            submission_id=seeded.version2_id,
            actor_type="system",
            actor_id=None,
            decision="approved",
            reason="Draft: looks complete.",
            is_final=False,
        )
    )
    db.flush()
    sign_in(client, MEMBER)
    versions = client.get(f"/submissions/{seeded.version2_id}").json()["versions"]
    assert versions[1]["reviews"] == []
    sign_in(client, SUPERVISOR)
    versions = client.get(f"/submissions/{seeded.version2_id}").json()["versions"]
    (draft,) = versions[1]["reviews"]
    assert draft["is_final"] is False
    assert draft["actor_type"] == "system"
    assert draft["actor_name"] is None


# --- who may look -------------------------------------------------------------------------


@pytest.mark.parametrize("email", [SUPERVISOR, ADMIN])
def test_a_supervisor_or_admin_in_the_same_org_can_read_it(
    client: TestClient, seeded: Seeded, email: str
) -> None:
    sign_in(client, email)
    assert client.get(f"/submissions/{seeded.version1_id}").status_code == 200


@pytest.mark.parametrize("email", [OTHER_MEMBER, OUTSIDER])
def test_another_member_or_an_outside_supervisor_gets_403(
    client: TestClient, seeded: Seeded, email: str
) -> None:
    sign_in(client, email)
    r = client.get(f"/submissions/{seeded.version1_id}")
    assert r.status_code == 403
    assert r.json() == {"detail": NOT_ALLOWED}


def test_a_missing_id_looks_exactly_like_forbidden(client: TestClient, seeded: Seeded) -> None:
    sign_in(client, MEMBER)
    r = client.get("/submissions/999999999")
    assert r.status_code == 403
    assert r.json() == {"detail": NOT_ALLOWED}


def test_signed_out_gets_401(client: TestClient, seeded: Seeded) -> None:
    assert client.get(f"/submissions/{seeded.version1_id}").status_code == 401


# --- commenting ---------------------------------------------------------------------------


def test_a_posted_comment_shows_up_in_the_next_read(client: TestClient, seeded: Seeded) -> None:
    sign_in(client, SUPERVISOR)
    r = client.post(
        f"/submissions/{seeded.version2_id}/comments", json={"body": "  Looks complete now. "}
    )
    assert r.status_code == 201
    posted = r.json()
    assert posted["body"] == "Looks complete now."
    assert posted["parent_comment_id"] is None
    assert posted["author_name"] == SUPERVISOR.split("@")[0]
    versions = client.get(f"/submissions/{seeded.version2_id}").json()["versions"]
    assert [c["id"] for c in versions[1]["comments"]] == [posted["id"]]


def test_a_reply_points_at_a_top_level_comment_on_the_same_version(
    client: TestClient, seeded: Seeded
) -> None:
    sign_in(client, MEMBER)
    first_id, reply_id = seeded.comment_ids
    ok = client.post(
        f"/submissions/{seeded.version1_id}/comments",
        json={"body": "Got it, thanks.", "parent_comment_id": first_id},
    )
    assert ok.status_code == 201
    assert ok.json()["parent_comment_id"] == first_id

    # A reply to a reply, a parent on another version, and a parent that does not exist.
    for parent in (reply_id, first_id, 999999999):
        target = seeded.version2_id if parent == first_id else seeded.version1_id
        r = client.post(
            f"/submissions/{target}/comments", json={"body": "x", "parent_comment_id": parent}
        )
        assert r.status_code == 422, parent


def test_a_blank_comment_is_refused(client: TestClient, seeded: Seeded) -> None:
    sign_in(client, MEMBER)
    r = client.post(f"/submissions/{seeded.version1_id}/comments", json={"body": "   "})
    assert r.status_code == 422


def test_someone_who_cannot_read_cannot_comment(client: TestClient, seeded: Seeded) -> None:
    sign_in(client, OTHER_MEMBER)
    r = client.post(f"/submissions/{seeded.version1_id}/comments", json={"body": "hi"})
    assert r.status_code == 403


# --- the link from My Work ----------------------------------------------------------------


def test_my_work_links_the_row_to_the_latest_version(client: TestClient, seeded: Seeded) -> None:
    sign_in(client, MEMBER)
    groups = client.get("/me/work").json()["groups"]
    items = [i for g in groups for i in g["items"] if i["title"] == seeding.ASSIGNMENT_TITLE]
    assert len(items) == 1
    assert items[0]["submission_id"] == seeded.version2_id
    assert items[0]["status"] == "submitted"
