"""SCRUM-14: My Work grouping, and who may ask for whose work.

Runs on SQLite like test_home.py. Finding the assignments that reach a member
needs Postgres arrays, so ``work.load_rows`` is replaced here with fixed rows;
the grouping and the access rule are what these tests are about.
"""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import ratelimit
import work
from db import Base, get_db
from main import app
from models import AuthSession, Cohort, Membership, Organization, Person, Team, Track
from security import hash_password
from sessions import NOT_ALLOWED
from work import Row, group_rows, status_of

PASSWORD = "correct horse battery staple"
NOW = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)

GROUP_ORDER = ["due-soon", "optional", "submitted", "changes", "overdue", "approved"]


def row(
    id: int,
    due_in_days: float | None = 3,
    mandatory: bool = True,
    submission: str | None = None,
    title: str = "Task",
) -> Row:
    due = NOW + timedelta(days=due_in_days) if due_in_days is not None else None
    return Row(id, title, "Marguerite Ellis", due, 10, mandatory, submission)


# --- grouping -----------------------------------------------------------------------------


def test_groups_come_in_the_card_order_even_when_empty() -> None:
    result = group_rows([], NOW)
    assert [g.key for g in result.groups] == GROUP_ORDER
    assert [g.label for g in result.groups] == [
        "Due soon",
        "Optional",
        "Submitted",
        "Changes requested",
        "Overdue",
        "Approved",
    ]
    assert all(g.items == [] for g in result.groups)


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({}, "due-soon"),
        ({"mandatory": False}, "optional"),
        ({"due_in_days": None}, "due-soon"),
        ({"due_in_days": -1}, "overdue"),
        ({"due_in_days": -1, "mandatory": False}, "overdue"),
        ({"submission": "submitted"}, "submitted"),
        ({"submission": "changes_requested"}, "changes"),
        ({"submission": "approved"}, "approved"),
        # Once handed in, being late no longer matters.
        ({"due_in_days": -5, "submission": "submitted"}, "submitted"),
        ({"due_in_days": -5, "submission": "approved"}, "approved"),
        ({"due_in_days": -5, "submission": "changes_requested"}, "changes"),
    ],
)
def test_which_group_each_assignment_lands_in(kwargs: dict, expected: str) -> None:
    assert status_of(row(1, **kwargs), NOW) == expected


def test_each_group_is_sorted_by_due_date_with_undated_work_last() -> None:
    rows = [
        row(1, due_in_days=5),
        row(2, due_in_days=None),
        row(3, due_in_days=1),
        row(4, due_in_days=3),
    ]
    due_soon = group_rows(rows, NOW).groups[0]
    assert [item.id for item in due_soon.items] == [3, 4, 1, 2]


def test_every_group_sorts_not_just_the_first() -> None:
    rows = [
        row(1, due_in_days=-1),
        row(2, due_in_days=-9),
        row(3, due_in_days=-4, submission="approved"),
        row(4, due_in_days=-8, submission="approved"),
    ]
    groups = {g.key: g for g in group_rows(rows, NOW).groups}
    assert [i.id for i in groups["overdue"].items] == [2, 1]
    assert [i.id for i in groups["approved"].items] == [4, 3]


def test_an_item_carries_what_the_row_shows() -> None:
    item = group_rows([row(7, title="Competitor audit")], NOW).groups[0].items[0]
    assert item.model_dump() == {
        "id": 7,
        "title": "Competitor audit",
        "set_by": "Marguerite Ellis",
        "due_at": NOW + timedelta(days=3),
        "points": 10,
        "status": "due-soon",
    }


def test_a_due_date_from_sqlite_without_a_timezone_still_compares() -> None:
    naive = Row(1, "T", "S", datetime(2026, 10, 25, 12, 0), 5, True, None)
    assert status_of(naive, NOW) == "overdue"


# --- who may ask for whose work -----------------------------------------------------------


@pytest.fixture
def factory() -> sessionmaker[Session]:
    """Org 1: Amara and Bola (interns), Marguerite (supervisor), Ada (admin). Org 2: Other Lead."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    tables = [Organization, Person, Team, Cohort, Track, Membership, AuthSession]
    Base.metadata.create_all(engine, tables=[model.__table__ for model in tables])
    factory = sessionmaker(bind=engine)
    with factory() as db:
        db.add_all(
            [
                Organization(id=1, name="The Emerson Empire", slug="emerson"),
                Organization(id=2, name="Elsewhere", slug="elsewhere"),
            ]
        )
        people = [
            (1, "amara@example.com", "Amara Okafor"),
            (2, "bola@example.com", "Bola Adeyemi"),
            (3, "marguerite@example.com", "Marguerite Ellis"),
            (4, "ada@example.com", "Ada Admin"),
            (5, "other.lead@example.com", "Other Lead"),
            (6, "no.org@example.com", "No Org"),
        ]
        for person_id, email, name in people:
            db.add(
                Person(
                    id=person_id,
                    email=email,
                    full_name=name,
                    password_hash=hash_password(PASSWORD),
                )
            )
        db.add_all(
            [
                Membership(id=1, person_id=1, organization_id=1, role="member"),
                Membership(id=2, person_id=2, organization_id=1, role="member"),
                Membership(id=3, person_id=3, organization_id=1, role="supervisor"),
                Membership(id=4, person_id=4, organization_id=1, role="admin"),
                Membership(id=5, person_id=5, organization_id=2, role="supervisor"),
            ]
        )
        db.commit()
    return factory


@pytest.fixture
def loaded_for(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Replaces the Postgres-only lookup; records whose work was loaded."""
    asked: list[int] = []

    def fake_load_rows(db: Session, member: Membership) -> list[Row]:
        asked.append(member.id)
        return [row(member.id, title=f"Work for membership {member.id}")]

    monkeypatch.setattr(work, "load_rows", fake_load_rows)
    return asked


@pytest.fixture
def client(factory: sessionmaker[Session], loaded_for: list[int]) -> Iterator[TestClient]:
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


def sign_in(client: TestClient, email: str) -> None:
    r = client.post("/auth/sign-in", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200


def titles(response: object) -> list[str]:
    return [i["title"] for g in response.json()["groups"] for i in g["items"]]  # type: ignore[attr-defined]


def test_a_member_asking_for_another_members_work_gets_403(
    client: TestClient, loaded_for: list[int]
) -> None:
    """The card's proof: member A requests member B -> 403, and B's work is never loaded."""
    sign_in(client, "amara@example.com")
    r = client.get("/members/2/work")
    assert r.status_code == 403
    assert r.json() == {"detail": NOT_ALLOWED}
    assert loaded_for == []


def test_a_member_can_ask_for_their_own_work(client: TestClient) -> None:
    sign_in(client, "amara@example.com")
    r = client.get("/members/1/work")
    assert r.status_code == 200
    assert titles(r) == ["Work for membership 1"]
    assert [g["key"] for g in r.json()["groups"]] == GROUP_ORDER
    assert r.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("email", ["marguerite@example.com", "ada@example.com"])
def test_a_supervisor_or_admin_in_the_same_org_can_ask_for_a_member(
    client: TestClient, email: str
) -> None:
    sign_in(client, email)
    r = client.get("/members/2/work")
    assert r.status_code == 200
    assert titles(r) == ["Work for membership 2"]


def test_a_supervisor_from_another_org_gets_403(client: TestClient) -> None:
    sign_in(client, "other.lead@example.com")
    assert client.get("/members/2/work").status_code == 403


def test_a_missing_membership_gets_the_same_403(client: TestClient) -> None:
    sign_in(client, "marguerite@example.com")
    r = client.get("/members/999/work")
    assert r.status_code == 403
    assert r.json() == {"detail": NOT_ALLOWED}


def test_work_needs_a_session(client: TestClient) -> None:
    assert client.get("/members/1/work").status_code == 401
    assert client.get("/me/work").status_code == 401


def test_me_work_is_the_same_call_with_your_own_membership(
    client: TestClient, loaded_for: list[int]
) -> None:
    sign_in(client, "amara@example.com")
    mine = client.get("/me/work")
    assert mine.status_code == 200
    assert loaded_for == [1]
    assert mine.json() == client.get("/members/1/work").json()
    assert mine.headers["cache-control"] == "no-store"


def test_me_work_never_shows_someone_elses_work(client: TestClient) -> None:
    sign_in(client, "bola@example.com")
    assert titles(client.get("/me/work")) == ["Work for membership 2"]


def test_someone_with_no_membership_gets_404_from_me_work(client: TestClient) -> None:
    sign_in(client, "no.org@example.com")
    assert client.get("/me/work").status_code == 404
