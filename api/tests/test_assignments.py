"""SCRUM-16: the rule for who an assignment reaches.

Needs Postgres, because picked recipients are a Postgres array. Runs when
DATABASE_URL is set and skips otherwise, like test_ledger.py. Each test runs
inside a transaction that is rolled back.
"""

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from assignments import has_assigned_work
from db import as_psycopg_url
from models import Assignment, Cohort, Membership, Organization, Person, Team, Track

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"), reason="needs a Postgres at DATABASE_URL"
)


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(as_psycopg_url(os.environ["DATABASE_URL"]))
    with engine.connect() as connection:
        outer = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        outer.rollback()
    engine.dispose()


@pytest.fixture
def world(session: Session) -> dict[str, object]:
    """Two organizations; in the first, an intern on team Design, cohort 7, track UX/UI."""
    org, other_org = (
        Organization(name="Emerson Empire", slug="emerson-test"),
        Organization(name="Elsewhere", slug="elsewhere-test"),
    )
    session.add_all([org, other_org])
    session.flush()
    design, web = (
        Team(organization_id=org.id, name="Design"),
        Team(organization_id=org.id, name="Web"),
    )
    cohort7, cohort8 = (
        Cohort(organization_id=org.id, name="Cohort 7"),
        Cohort(organization_id=org.id, name="Cohort 8"),
    )
    ux, sales = (
        Track(organization_id=org.id, name="UX/UI"),
        Track(organization_id=org.id, name="Sales"),
    )
    intern = Person(email="amara.test@example.com", full_name="Amara", password_hash="x")
    boss = Person(email="boss.test@example.com", full_name="Boss", password_hash="x")
    session.add_all([design, web, cohort7, cohort8, ux, sales, intern, boss])
    session.flush()
    member = Membership(
        person_id=intern.id,
        organization_id=org.id,
        role="member",
        team_id=design.id,
        cohort_id=cohort7.id,
        track_id=ux.id,
    )
    supervisor = Membership(person_id=boss.id, organization_id=org.id, role="supervisor")
    session.add_all([member, supervisor])
    session.flush()
    return {
        "org": org,
        "other_org": other_org,
        "design": design,
        "web": web,
        "cohort7": cohort7,
        "cohort8": cohort8,
        "ux": ux,
        "sales": sales,
        "member": member,
        "supervisor": supervisor,
    }


def post(session: Session, world: dict[str, object], **targets: object) -> None:
    """Add one assignment in the first organization with the given targets."""
    session.add(
        Assignment(
            organization_id=world["org"].id,
            created_by_membership_id=world["supervisor"].id,
            title="Homework",
            points_value=10,
            late_policy="accept",
            **targets,
        )
    )
    session.flush()


def test_nothing_assigned_yet(session: Session, world: dict[str, object]) -> None:
    assert has_assigned_work(session, world["member"]) is False


def test_picked_by_name(session: Session, world: dict[str, object]) -> None:
    post(session, world, recipient_membership_ids=[world["member"].id])
    assert has_assigned_work(session, world["member"]) is True


def test_their_team(session: Session, world: dict[str, object]) -> None:
    post(session, world, team_id=world["design"].id)
    assert has_assigned_work(session, world["member"]) is True


def test_their_track(session: Session, world: dict[str, object]) -> None:
    post(session, world, track_id=world["ux"].id)
    assert has_assigned_work(session, world["member"]) is True


def test_another_team(session: Session, world: dict[str, object]) -> None:
    post(session, world, team_id=world["web"].id)
    assert has_assigned_work(session, world["member"]) is False


def test_every_named_group_must_match(session: Session, world: dict[str, object]) -> None:
    """Their team but another cohort: not for them."""
    post(session, world, team_id=world["design"].id, cohort_id=world["cohort8"].id)
    assert has_assigned_work(session, world["member"]) is False


def test_someone_else_picked(session: Session, world: dict[str, object]) -> None:
    post(session, world, recipient_membership_ids=[world["supervisor"].id])
    assert has_assigned_work(session, world["member"]) is False


def test_an_untargeted_assignment_reaches_nobody(
    session: Session, world: dict[str, object]
) -> None:
    post(session, world)
    assert has_assigned_work(session, world["member"]) is False


def test_another_organization_never_counts(session: Session, world: dict[str, object]) -> None:
    other_boss = Person(email="other.boss@example.com", full_name="Other", password_hash="x")
    session.add(other_boss)
    session.flush()
    other_supervisor = Membership(
        person_id=other_boss.id, organization_id=world["other_org"].id, role="supervisor"
    )
    session.add(other_supervisor)
    session.flush()
    session.add(
        Assignment(
            organization_id=world["other_org"].id,
            created_by_membership_id=other_supervisor.id,
            title="Not yours",
            points_value=10,
            late_policy="accept",
            recipient_membership_ids=[world["member"].id],
        )
    )
    session.flush()
    assert has_assigned_work(session, world["member"]) is False
