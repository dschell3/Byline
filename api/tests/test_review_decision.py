"""SCRUM-26: a supervisor approves or requests changes, with a score per criterion.

Needs Postgres like test_submissions.py (the seed writes an array column), so it
skips without DATABASE_URL. Each test runs in one transaction that is rolled back.

The seed gives one member's work in two versions: version 1 already has changes
requested, version 2 is waiting. Four criteria, each out of 5, so 20 in all.
"""

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import ratelimit
import review_decision
from db import as_psycopg_url, get_db
from main import app
from models import Membership, Organization, Person, Review, Submission, Team
from scripts import seed_submission as seeding
from scripts.seed_submission import Seeded
from security import hash_password
from sessions import NOT_ALLOWED

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"), reason="needs a Postgres at DATABASE_URL"
)

PASSWORD = "correct horse battery staple"

MEMBER = "amara.scrum26@example.com"
OTHER_MEMBER = "bola.scrum26@example.com"
SUPERVISOR = "marguerite.scrum26@example.com"
ADMIN = "ada.scrum26@example.com"
OUTSIDER = "other.lead.scrum26@example.com"


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
    org = Organization(name="Seeded Org", slug="seeded-org-scrum26")
    db.add(org)
    db.flush()
    team = Team(organization_id=org.id, name="Design")
    db.add(team)
    db.flush()
    supervisor = _person(db, org, team, SUPERVISOR, "supervisor")
    member = _person(db, org, team, MEMBER, "member")
    _person(db, org, team, OTHER_MEMBER, "member")
    _person(db, org, None, ADMIN, "admin")
    elsewhere = Organization(name="Elsewhere", slug="elsewhere-scrum26")
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


def body(seeded: Seeded, decision: str = "approved", scores=(3, 3, 3, 3), reason=None) -> dict:  # noqa: ANN001
    return {
        "decision": decision,
        "reason": reason,
        "scores": [
            {"criterion_id": cid, "score": score}
            for cid, score in zip(seeded.criterion_ids, scores, strict=True)
        ],
    }


def review_url(seeded: Seeded, version_id: int | None = None) -> str:
    return f"/submissions/{version_id or seeded.version2_id}/review"


# --- the happy paths ------------------------------------------------------------------------


def test_approving_writes_a_final_review_and_moves_the_status(
    client: TestClient, db: Session, seeded: Seeded
) -> None:
    sign_in(client, SUPERVISOR)
    r = client.post(review_url(seeded), json=body(seeded, scores=(5, 3, 2, 2)))
    assert r.status_code == 200
    assert r.headers["cache-control"] == "no-store"
    latest = r.json()["versions"][-1]
    assert latest["status"] == "approved"
    (review,) = latest["reviews"]
    assert review["decision"] == "approved"
    assert review["is_final"] is True
    assert review["actor_type"] == "person"
    assert review["actor_name"] == SUPERVISOR.split("@")[0]
    assert [s["score"] for s in review["scores"]] == [5, 3, 2, 2]
    assert sum(s["score"] for s in review["scores"]) == 12
    assert sum(s["max_points"] for s in review["scores"]) == 20
    assert db.get(Submission, seeded.version2_id).status == "approved"


def test_requesting_changes_keeps_the_reason_and_the_notes(
    client: TestClient, seeded: Seeded
) -> None:
    sign_in(client, SUPERVISOR)
    payload = body(seeded, decision="changes_requested", reason="  Finish the phone frames.  ")
    payload["scores"][1]["note"] = "Stops at sign-up"
    r = client.post(review_url(seeded), json=payload)
    assert r.status_code == 200
    latest = r.json()["versions"][-1]
    assert latest["status"] == "changes_requested"
    (review,) = latest["reviews"]
    assert review["reason"] == "Finish the phone frames."
    assert [s["note"] for s in review["scores"]] == [None, "Stops at sign-up", None, None]


def test_the_reason_is_optional_until_scrum_27(client: TestClient, seeded: Seeded) -> None:
    sign_in(client, SUPERVISOR)
    r = client.post(review_url(seeded), json=body(seeded, decision="changes_requested", reason=" "))
    assert r.status_code == 200
    assert r.json()["versions"][-1]["reviews"][0]["reason"] is None


def test_an_admin_in_the_same_org_can_review(client: TestClient, seeded: Seeded) -> None:
    sign_in(client, ADMIN)
    assert client.post(review_url(seeded), json=body(seeded)).status_code == 200


def test_the_member_sees_the_new_review_on_their_history(
    client: TestClient, seeded: Seeded
) -> None:
    sign_in(client, SUPERVISOR)
    client.post(review_url(seeded), json=body(seeded))
    client.post("/auth/sign-out")
    sign_in(client, MEMBER)
    latest = client.get(f"/submissions/{seeded.version2_id}").json()["versions"][-1]
    assert latest["status"] == "approved"
    assert len(latest["reviews"]) == 1


# --- who may review -------------------------------------------------------------------------


@pytest.mark.parametrize("email", [MEMBER, OTHER_MEMBER, OUTSIDER])
def test_the_member_another_member_or_an_outside_supervisor_gets_403(
    client: TestClient, db: Session, seeded: Seeded, email: str
) -> None:
    sign_in(client, email)
    r = client.post(review_url(seeded), json=body(seeded))
    assert r.status_code == 403
    assert r.json()["detail"] == NOT_ALLOWED
    assert db.get(Submission, seeded.version2_id).status == "submitted"


def test_a_missing_id_looks_exactly_like_forbidden(client: TestClient, seeded: Seeded) -> None:
    sign_in(client, SUPERVISOR)
    r = client.post("/submissions/999999999/review", json=body(seeded))
    assert r.status_code == 403
    assert r.json()["detail"] == NOT_ALLOWED


def test_signed_out_gets_401(client: TestClient, seeded: Seeded) -> None:
    assert client.post(review_url(seeded), json=body(seeded)).status_code == 401


# --- which version --------------------------------------------------------------------------


def test_an_older_version_cannot_be_reviewed(client: TestClient, seeded: Seeded) -> None:
    sign_in(client, SUPERVISOR)
    r = client.post(review_url(seeded, seeded.version1_id), json=body(seeded))
    assert r.status_code == 409
    assert r.json()["detail"] == review_decision.NOT_LATEST


def test_a_decided_version_cannot_be_decided_again(
    client: TestClient, db: Session, seeded: Seeded
) -> None:
    sign_in(client, SUPERVISOR)
    assert client.post(review_url(seeded), json=body(seeded)).status_code == 200
    r = client.post(review_url(seeded), json=body(seeded, decision="changes_requested"))
    assert r.status_code == 409
    assert r.json()["detail"] == review_decision.NOT_WAITING
    finals = db.scalars(
        select(Review).where(Review.submission_id == seeded.version2_id, Review.is_final.is_(True))
    ).all()
    assert len(finals) == 1


# --- the scores -----------------------------------------------------------------------------


def test_every_criterion_needs_a_score(client: TestClient, db: Session, seeded: Seeded) -> None:
    sign_in(client, SUPERVISOR)
    payload = body(seeded)
    payload["scores"].pop()
    r = client.post(review_url(seeded), json=payload)
    assert r.status_code == 422
    assert "Missing" in r.json()["detail"]
    assert db.get(Submission, seeded.version2_id).status == "submitted"


def test_a_score_above_the_maximum_is_refused(client: TestClient, seeded: Seeded) -> None:
    sign_in(client, SUPERVISOR)
    r = client.post(review_url(seeded), json=body(seeded, scores=(6, 3, 3, 3)))
    assert r.status_code == 422
    assert "out of 5" in r.json()["detail"]


def test_a_negative_score_is_refused(client: TestClient, seeded: Seeded) -> None:
    sign_in(client, SUPERVISOR)
    r = client.post(review_url(seeded), json=body(seeded, scores=(-1, 3, 3, 3)))
    assert r.status_code == 422


def test_a_criterion_scored_twice_is_refused(client: TestClient, seeded: Seeded) -> None:
    sign_in(client, SUPERVISOR)
    payload = body(seeded)
    payload["scores"][1]["criterion_id"] = seeded.criterion_ids[0]
    r = client.post(review_url(seeded), json=payload)
    assert r.status_code == 422


def test_a_criterion_from_another_assignment_is_refused(client: TestClient, seeded: Seeded) -> None:
    sign_in(client, SUPERVISOR)
    payload = body(seeded)
    payload["scores"][0]["criterion_id"] = 999999999
    r = client.post(review_url(seeded), json=payload)
    assert r.status_code == 422


def test_an_unknown_decision_is_refused(client: TestClient, seeded: Seeded) -> None:
    sign_in(client, SUPERVISOR)
    r = client.post(review_url(seeded), json=body(seeded, decision="maybe"))
    assert r.status_code == 422
