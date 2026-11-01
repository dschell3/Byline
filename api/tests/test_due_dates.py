"""SCRUM-15: one deadline, read the same way by people in different timezones.

Runs on SQLite like test_work.py. Finding a member's assignments needs Postgres, so
``work.load_rows`` is replaced with one fixed assignment; what these tests are about is the
deadline the API sends and who it calls late. Amara is a member in India and Marguerite is a
supervisor in California.
"""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import ratelimit
import sessions
import work
from db import Base, get_db
from main import app
from models import AuthSession, Cohort, Membership, Organization, Person, Team, Track
from security import hash_password
from work import Row

PASSWORD = "correct horse battery staple"
MEMBER = "amara.okafor@example.com"  # Asia/Kolkata, UTC+5:30
SUPERVISOR = "marguerite@example.com"  # America/Los_Angeles


@pytest.fixture
def factory() -> sessionmaker[Session]:
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
                    email=MEMBER,
                    full_name="Amara Okafor",
                    timezone="Asia/Kolkata",
                    password_hash=hash_password(PASSWORD),
                ),
                Person(
                    id=2,
                    email=SUPERVISOR,
                    full_name="Marguerite Ellis",
                    timezone="America/Los_Angeles",
                    password_hash=hash_password(PASSWORD),
                ),
            ]
        )
        db.add_all(
            [
                Membership(id=1, person_id=1, organization_id=1, role="member"),
                Membership(id=2, person_id=2, organization_id=1, role="supervisor"),
            ]
        )
        db.commit()
    return factory


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> dict[str, datetime]:
    """Move sessions.now(). Starts a minute ahead so a sign-in stays inside the idle limit."""
    state = {"now": datetime.now(UTC) + timedelta(minutes=1)}
    monkeypatch.setattr(sessions, "now", lambda: state["now"])
    return state


@pytest.fixture
def due_at(clock: dict[str, datetime]) -> datetime:
    """The one deadline, half an hour after the clock's start."""
    return clock["now"] + timedelta(minutes=30)


@pytest.fixture
def client(
    factory: sessionmaker[Session], due_at: datetime, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    def fake_load_rows(db: Session, member: Membership) -> list[Row]:
        return [Row(1, "Competitor audit", "Marguerite Ellis", due_at, 10, True, None)]

    monkeypatch.setattr(work, "load_rows", fake_load_rows)

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


def the_item(response: object) -> dict:
    items = [i for g in response.json()["groups"] for i in g["items"]]  # type: ignore[attr-defined]
    assert len(items) == 1
    return items[0]


def seen_by_member(client: TestClient) -> dict:
    sign_in(client, MEMBER)
    r = client.get("/me/work")
    assert r.status_code == 200
    return the_item(r)


def seen_by_supervisor(client: TestClient) -> dict:
    sign_in(client, SUPERVISOR)
    r = client.get("/members/1/work")
    assert r.status_code == 200
    return the_item(r)


def test_both_people_get_the_same_instant(client: TestClient, due_at: datetime) -> None:
    mine = seen_by_member(client)
    theirs = seen_by_supervisor(client)
    # An explicit UTC offset on the wire, so the browser can place it on the viewer's calendar.
    assert mine["due_at"].endswith(("Z", "+00:00"))
    assert theirs["due_at"].endswith(("Z", "+00:00"))
    assert datetime.fromisoformat(mine["due_at"]) == due_at
    assert datetime.fromisoformat(theirs["due_at"]) == due_at


def test_late_is_decided_once_in_utc_for_both(
    client: TestClient, clock: dict[str, datetime]
) -> None:
    assert seen_by_member(client)["status"] == "due-soon"
    assert seen_by_supervisor(client)["status"] == "due-soon"

    clock["now"] += timedelta(minutes=31)  # a minute past the deadline, in UTC

    assert seen_by_member(client)["status"] == "overdue"
    assert seen_by_supervisor(client)["status"] == "overdue"


def test_changing_timezone_never_changes_whether_something_is_late(
    client: TestClient, clock: dict[str, datetime]
) -> None:
    sign_in(client, MEMBER)
    for zone in ("Pacific/Kiritimati", "Pacific/Pago_Pago"):  # UTC+14 and UTC-11
        assert client.patch("/me/profile", json={"timezone": zone}).status_code == 200
        assert the_item(client.get("/me/work"))["status"] == "due-soon"

    clock["now"] += timedelta(minutes=31)

    for zone in ("Pacific/Kiritimati", "Pacific/Pago_Pago", "Asia/Kolkata"):
        assert client.patch("/me/profile", json={"timezone": zone}).status_code == 200
        assert the_item(client.get("/me/work"))["status"] == "overdue"
