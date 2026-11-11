"""My Work: the assignments that reach a member, grouped and sorted (SCRUM-14, P10).

Six groups, always in this order: Due soon, Optional, Submitted, Changes
requested, Overdue, Approved. Inside each group the earliest due date comes
first, and work with no due date comes last.

Which group an assignment lands in:

- the member's latest submission is approved -> Approved
- the member's latest submission has changes requested -> Changes requested
- any other submission -> Submitted
- no submission yet: past its due date -> Overdue, else optional work ->
  Optional, else -> Due soon.

``submission.status`` is the cached decision of the latest final review
(docs/erd.md), so no review join is needed here.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

import assignments
import sessions
from late_policy import ACCEPTED_FULL_POINTS, was_handed_in_late
from models import Membership, Person, Submission

# (key, label). The keys match the status words in the web app's Badge.
GROUPS = [
    ("due-soon", "Due soon"),
    ("optional", "Optional"),
    ("submitted", "Submitted"),
    ("changes", "Changes requested"),
    ("overdue", "Overdue"),
    ("approved", "Approved"),
]

APPROVED = "approved"
CHANGES_REQUESTED = "changes_requested"


class WorkItem(BaseModel):
    id: int
    # The member's latest submission, when there is one: the P14 link (SCRUM-22).
    submission_id: int | None
    title: str
    set_by: str
    due_at: datetime | None
    points: int
    status: str
    # SCRUM-23: what happens if it is handed in late. The web app turns these into
    # words (web/src/lib/latePolicy.ts); the rules live in late_policy.py.
    late_policy: str
    late_cutoff_hours: int | None
    # True when the first hand-in came after the due date. A resubmission the
    # reviewer asked for after the deadline does not make it late.
    handed_in_late: bool


class WorkGroup(BaseModel):
    key: str
    label: str
    items: list[WorkItem]


class WorkResponse(BaseModel):
    groups: list[WorkGroup]


@dataclass(frozen=True)
class Row:
    """One assignment as it stands for one member, before it is grouped."""

    id: int
    title: str
    set_by: str
    due_at: datetime | None
    points: int
    is_mandatory: bool
    submission_status: str | None  # the member's latest submission, if any
    submission_id: int | None = None
    late_policy: str = ACCEPTED_FULL_POINTS
    late_cutoff_hours: int | None = None
    handed_in_late: bool = False


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def status_of(row: Row, at: datetime) -> str:
    """The group key for ``row`` as of ``at``."""
    if row.submission_status == APPROVED:
        return "approved"
    if row.submission_status == CHANGES_REQUESTED:
        return "changes"
    if row.submission_status is not None:
        return "submitted"
    if row.due_at is not None and _aware(row.due_at) < at:
        return "overdue"
    return "due-soon" if row.is_mandatory else "optional"


def group_rows(rows: list[Row], at: datetime) -> WorkResponse:
    """Sort ``rows`` into the six groups, earliest due date first in each."""
    by_key: dict[str, list[WorkItem]] = {key: [] for key, _ in GROUPS}
    for row in sorted(
        rows,
        key=lambda r: (
            r.due_at is None,
            _aware(r.due_at) if r.due_at else datetime.max.replace(tzinfo=UTC),
            r.id,
        ),
    ):
        status = status_of(row, at)
        by_key[status].append(
            WorkItem(
                id=row.id,
                submission_id=row.submission_id,
                title=row.title,
                set_by=row.set_by,
                due_at=row.due_at,
                points=row.points,
                status=status,
                late_policy=row.late_policy,
                late_cutoff_hours=row.late_cutoff_hours,
                handed_in_late=row.handed_in_late,
            )
        )
    return WorkResponse(
        groups=[WorkGroup(key=key, label=label, items=by_key[key]) for key, label in GROUPS]
    )


def load_rows(db: Session, member: Membership) -> list[Row]:
    """Every assignment that reaches ``member``, with their latest submission's status.

    Uses the shared ``assigned_to`` rule, so it needs Postgres.
    """
    rows = []
    for assignment in assignments.assignments_for(db, member):
        latest = db.execute(
            select(Submission.id, Submission.status)
            .where(
                Submission.assignment_id == assignment.id,
                Submission.membership_id == member.id,
            )
            .order_by(Submission.version.desc())
            .limit(1)
        ).first()
        first_handed_in_at = db.scalar(
            select(Submission.submitted_at)
            .where(
                Submission.assignment_id == assignment.id,
                Submission.membership_id == member.id,
            )
            .order_by(Submission.version.asc())
            .limit(1)
        )
        set_by = db.scalar(
            select(Person.full_name)
            .join(Membership, Membership.person_id == Person.id)
            .where(Membership.id == assignment.created_by_membership_id)
        )
        rows.append(
            Row(
                id=assignment.id,
                title=assignment.title,
                set_by=set_by or "Your supervisor",
                due_at=assignment.due_at,
                points=assignment.points_value,
                is_mandatory=assignment.is_mandatory,
                submission_status=latest.status if latest else None,
                submission_id=latest.id if latest else None,
                late_policy=assignment.late_policy,
                late_cutoff_hours=assignment.late_cutoff_hours,
                handed_in_late=first_handed_in_at is not None
                and was_handed_in_late(assignment, first_handed_in_at),
            )
        )
    return rows


def for_member(db: Session, member: Membership) -> WorkResponse:
    """The My Work screen's data for ``member``. Both endpoints call this."""
    return group_rows(load_rows(db, member), sessions.now())


def supervising_membership(db: Session, caller: Person, organization_id: int) -> Membership | None:
    """The caller's active supervisor or admin membership in ``organization_id``, if any."""
    return db.scalar(
        select(Membership)
        .where(
            Membership.person_id == caller.id,
            Membership.is_active.is_(True),
            Membership.organization_id == organization_id,
            Membership.role.in_(("supervisor", "admin")),
        )
        .order_by(Membership.id)
    )


def can_view(db: Session, caller: Person, target: Membership) -> bool:
    """Your own work, or anyone's in an organization where you supervise or administer."""
    if target.person_id == caller.id:
        return True
    return supervising_membership(db, caller, target.organization_id) is not None
