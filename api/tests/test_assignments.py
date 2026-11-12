"""SCRUM-16: the rule for who an assignment reaches. SCRUM-23: the late policy checks.

Needs Postgres, because picked recipients are a Postgres array. Runs when
DATABASE_URL is set and skips otherwise, like test_ledger.py. Each test runs
inside a transaction that is rolled back.
"""

import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import work
from assignments import has_assigned_work
from db import as_psycopg_url
from late_policy import late_penalty_ledger_row
from models import (
    Assignment,
    Cohort,
    Membership,
    Organization,
    Person,
    PointsLedger,
    Submission,
    Team,
    Track,
)

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


def post(
    session: Session,
    world: dict[str, object],
    late_policy: str = "accepted_full_points",
    **targets: object,
) -> Assignment:
    """Add one assignment in the first organization with the given targets."""
    assignment = Assignment(
        organization_id=world["org"].id,
        created_by_membership_id=world["supervisor"].id,
        title="Homework",
        points_value=10,
        late_policy=late_policy,
        **targets,
    )
    session.add(assignment)
    session.flush()
    return assignment


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
            late_policy="accepted_full_points",
            recipient_membership_ids=[world["member"].id],
        )
    )
    session.flush()
    assert has_assigned_work(session, world["member"]) is False


def test_half_points_up_to_48_hours_late_can_be_stored(
    session: Session, world: dict[str, object]
) -> None:
    post(
        session,
        world,
        late_policy="accepted_half_points",
        late_cutoff_hours=48,
        team_id=world["design"].id,
    )


def test_the_database_refuses_a_late_policy_it_does_not_know(
    session: Session, world: dict[str, object]
) -> None:
    with pytest.raises(IntegrityError, match="ck_assignment_late_policy"):
        post(session, world, late_policy="maybe", team_id=world["design"].id)


def test_the_database_refuses_a_late_cutoff_of_zero_hours(
    session: Session, world: dict[str, object]
) -> None:
    with pytest.raises(IntegrityError, match="ck_assignment_late_cutoff_hours"):
        post(session, world, late_cutoff_hours=0, team_id=world["design"].id)


def test_my_work_rows_carry_the_late_policy_stored_on_the_assignment(
    session: Session, world: dict[str, object]
) -> None:
    post(
        session,
        world,
        late_policy="accepted_half_points",
        late_cutoff_hours=48,
        team_id=world["design"].id,
    )
    [row] = work.load_rows(session, world["member"])
    assert row.late_policy == "accepted_half_points"
    assert row.late_cutoff_hours == 48


DUE = datetime(2026, 11, 13, 23, 59, 59, tzinfo=UTC)


def hand_in(
    session: Session, world: dict[str, object], assignment: Assignment, version: int, at: datetime
) -> Submission:
    """The intern hands in a version of their work at the moment ``at``."""
    submission = Submission(
        assignment_id=assignment.id,
        membership_id=world["member"].id,
        version=version,
        status="submitted",
        submitted_at=at,
    )
    session.add(submission)
    session.flush()
    return submission


def test_work_handed_in_before_the_deadline_is_not_flagged_late(
    session: Session, world: dict[str, object]
) -> None:
    assignment = post(session, world, team_id=world["design"].id, due_at=DUE)
    hand_in(session, world, assignment, version=1, at=DUE - timedelta(hours=1))
    [row] = work.load_rows(session, world["member"])
    assert row.handed_in_late is False


def test_work_handed_in_after_the_deadline_is_flagged_late(
    session: Session, world: dict[str, object]
) -> None:
    assignment = post(session, world, team_id=world["design"].id, due_at=DUE)
    hand_in(session, world, assignment, version=1, at=DUE + timedelta(hours=1))
    [row] = work.load_rows(session, world["member"])
    assert row.handed_in_late is True


def test_a_requested_resubmission_after_the_deadline_does_not_make_it_late(
    session: Session, world: dict[str, object]
) -> None:
    assignment = post(session, world, team_id=world["design"].id, due_at=DUE)
    hand_in(session, world, assignment, version=1, at=DUE - timedelta(hours=1))
    hand_in(session, world, assignment, version=2, at=DUE + timedelta(days=2))
    [row] = work.load_rows(session, world["member"])
    assert row.handed_in_late is False


def test_a_late_penalty_is_its_own_ledger_row_and_the_total_is_half(
    session: Session, world: dict[str, object]
) -> None:
    assignment = post(
        session,
        world,
        late_policy="accepted_half_points",
        late_cutoff_hours=48,
        team_id=world["design"].id,
        due_at=DUE,
    )
    late_by_an_hour = DUE + timedelta(hours=1)
    approved = hand_in(session, world, assignment, version=1, at=late_by_an_hour)

    full_award = PointsLedger(
        membership_id=world["member"].id,
        submission_id=approved.id,
        amount=assignment.points_value,
        reason="Approved",
        actor_type="system",
    )
    penalty = late_penalty_ledger_row(assignment, approved, first_handed_in_at=late_by_an_hour)
    session.add_all([full_award, penalty])
    session.flush()

    amounts = session.scalars(
        select(PointsLedger.amount).where(PointsLedger.membership_id == world["member"].id)
    ).all()
    assert sorted(amounts) == [-5, 10]
    assert sum(amounts) == 5
