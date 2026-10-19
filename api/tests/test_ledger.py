"""SCRUM-69: the database itself refuses to change or remove ledger rows.

These tests talk to a real Postgres, because the trigger lives there. They
run when DATABASE_URL is set (locally, against the Docker database after
``alembic upgrade head``) and skip otherwise (CI has no Postgres yet).
Every test runs inside a transaction that is rolled back, so nothing is left
in the database afterwards.
"""

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, delete, func, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from db import as_psycopg_url
from models import Membership, Organization, Person, PointsLedger

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"), reason="needs a Postgres at DATABASE_URL"
)


@pytest.fixture
def session() -> Iterator[Session]:
    """A session inside one outer transaction that is rolled back at the end."""
    engine = create_engine(as_psycopg_url(os.environ["DATABASE_URL"]))
    with engine.connect() as connection:
        outer = connection.begin()
        trigger_exists = connection.execute(
            text("SELECT 1 FROM pg_trigger WHERE tgname = 'points_ledger_no_update_delete'")
        ).scalar()
        if not trigger_exists:
            outer.rollback()
            pytest.skip("run `alembic upgrade head` first; the ledger trigger is missing")

        # create_savepoint: session.commit()/rollback() act on a SAVEPOINT, so a
        # statement the trigger rejects does not poison the outer transaction.
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        outer.rollback()


@pytest.fixture
def membership(session: Session) -> Membership:
    """One member of one organization, the minimum a ledger row needs."""
    org = Organization(name="Emerson Empire", slug="emerson")
    person = Person(
        email="amara.okafor@example.com",
        full_name="Amara Okafor",
        password_hash="not-a-real-hash",
    )
    session.add_all([org, person])
    session.flush()
    member = Membership(person_id=person.id, organization_id=org.id, role="member")
    session.add(member)
    session.flush()
    return member


def award(session: Session, membership: Membership, amount: int, reason: str) -> PointsLedger:
    """Insert one ledger row and return it with its id populated."""
    row = PointsLedger(
        membership_id=membership.id, amount=amount, reason=reason, actor_type="system"
    )
    session.add(row)
    session.flush()
    return row


def total_for(session: Session, membership: Membership) -> int:
    """A member's points are the SUM of their ledger rows, nothing else."""
    return session.scalar(
        select(func.coalesce(func.sum(PointsLedger.amount), 0)).where(
            PointsLedger.membership_id == membership.id
        )
    )


def test_update_is_rejected(session: Session, membership: Membership) -> None:
    """UPDATE on a ledger row raises, so points can never be quietly changed."""
    row = award(session, membership, 10, "Competitor audit approved")
    with pytest.raises(DBAPIError, match="append-only"):
        with session.begin_nested():
            session.execute(update(PointsLedger).where(PointsLedger.id == row.id).values(amount=99))


def test_delete_is_rejected(session: Session, membership: Membership) -> None:
    """DELETE on a ledger row raises, so history can never disappear."""
    row = award(session, membership, 10, "Competitor audit approved")
    with pytest.raises(DBAPIError, match="append-only"):
        with session.begin_nested():
            session.execute(delete(PointsLedger).where(PointsLedger.id == row.id))


def test_correction_is_a_reversing_insert(session: Session, membership: Membership) -> None:
    """A correction is a new row that points at the row it reverses; the original is untouched."""
    original = award(session, membership, 10, "Competitor audit approved")

    correction = PointsLedger(
        membership_id=membership.id,
        amount=-10,
        reason="Approved by mistake, reversed",
        actor_type="person",
        actor_id=membership.id,
        reverses_ledger_id=original.id,
    )
    session.add(correction)
    session.flush()

    rows = session.scalars(
        select(PointsLedger).where(PointsLedger.membership_id == membership.id)
    ).all()
    assert len(rows) == 2
    assert correction.reverses_ledger_id == original.id
    session.refresh(original)
    assert original.amount == 10


def test_total_is_the_sum_of_ledger_rows(session: Session, membership: Membership) -> None:
    """The member's total follows the ledger before and after a correction."""
    assert total_for(session, membership) == 0

    first = award(session, membership, 10, "Competitor audit approved")
    award(session, membership, 5, "Weekly check-in")
    assert total_for(session, membership) == 15

    session.add(
        PointsLedger(
            membership_id=membership.id,
            amount=-10,
            reason="Reversed",
            actor_type="system",
            reverses_ledger_id=first.id,
        )
    )
    session.flush()
    assert total_for(session, membership) == 5
