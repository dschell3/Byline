"""The review queue's data (SCRUM-24, P19).

``GET /review/queue`` lists the work waiting for a supervisor, oldest first.
That order is fixed: it is the point of the screen, not an option.

Who sees what (docs/erd.md, "Teams vs cohorts"): a supervisor sees submissions
from the team they run; an admin sees the whole organization. Only the latest
version of each piece of work counts, so a resubmission replaces the old row.
"""

from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import Assignment, Cohort, Membership, Person, Submission, Team, Track

WAITING = "submitted"
STATUSES = (WAITING, "changes_requested", "approved")


class QueueRow(BaseModel):
    submission_id: int
    intern_name: str
    assignment_id: int
    assignment_title: str
    team_id: int | None
    team_name: str | None
    cohort_id: int | None
    cohort_name: str | None
    track_name: str | None
    submitted_at: datetime
    status: str


class Option(BaseModel):
    id: int
    name: str


class QueueFilters(BaseModel):
    """What the filter dropdowns offer. Always the whole scope, not the filtered rows."""

    teams: list[Option]
    cohorts: list[Option]
    assignments: list[Option]


class QueueResponse(BaseModel):
    rows: list[QueueRow]
    filters: QueueFilters


def scope(db: Session, person: Person) -> list[Membership]:
    """The caller's active supervisor and admin memberships."""
    return list(
        db.scalars(
            select(Membership).where(
                Membership.person_id == person.id,
                Membership.is_active.is_(True),
                Membership.role.in_(("supervisor", "admin")),
            )
        )
    )


def _in_scope(memberships: list[Membership]):  # noqa: ANN202
    """A SQL condition: submitted by someone this caller reviews."""
    parts = []
    for m in memberships:
        if m.role == "admin":
            parts.append(Membership.organization_id == m.organization_id)
        elif m.team_id is not None:
            parts.append(
                (Membership.organization_id == m.organization_id)
                & (Membership.team_id == m.team_id)
            )
    if not parts:
        return None
    condition = parts[0]
    for part in parts[1:]:
        condition = condition | part
    return condition


def queue(
    db: Session,
    person: Person,
    *,
    status: str = WAITING,
    team_id: int | None = None,
    cohort_id: int | None = None,
    assignment_id: int | None = None,
) -> QueueResponse:
    """The queue for ``person``. ``status`` is one of STATUSES, or ``all``."""
    empty = QueueResponse(rows=[], filters=QueueFilters(teams=[], cohorts=[], assignments=[]))
    condition = _in_scope(scope(db, person))
    if condition is None:
        return empty

    # The latest version of each piece of work: one row per (assignment, member).
    latest = (
        select(
            Submission.assignment_id,
            Submission.membership_id,
            func.max(Submission.version).label("version"),
        )
        .group_by(Submission.assignment_id, Submission.membership_id)
        .subquery()
    )
    base = (
        select(
            Submission,
            Person.full_name,
            Assignment.title,
            Membership.team_id,
            Team.name,
            Membership.cohort_id,
            Cohort.name,
            Track.name,
        )
        .join(
            latest,
            (latest.c.assignment_id == Submission.assignment_id)
            & (latest.c.membership_id == Submission.membership_id)
            & (latest.c.version == Submission.version),
        )
        .join(Membership, Membership.id == Submission.membership_id)
        .join(Person, Person.id == Membership.person_id)
        .join(Assignment, Assignment.id == Submission.assignment_id)
        .outerjoin(Team, Team.id == Membership.team_id)
        .outerjoin(Cohort, Cohort.id == Membership.cohort_id)
        .outerjoin(Track, Track.id == Membership.track_id)
        .where(condition)
    )

    # The dropdowns offer everything in scope, whatever is filtered right now.
    everything = db.execute(base).all()
    filters = QueueFilters(
        teams=_options((r[3], r[4]) for r in everything),
        cohorts=_options((r[5], r[6]) for r in everything),
        assignments=_options((r[0].assignment_id, r[2]) for r in everything),
    )

    query = base
    if status != "all":
        query = query.where(Submission.status == status)
    if team_id is not None:
        query = query.where(Membership.team_id == team_id)
    if cohort_id is not None:
        query = query.where(Membership.cohort_id == cohort_id)
    if assignment_id is not None:
        query = query.where(Submission.assignment_id == assignment_id)
    # Oldest first, always. The id breaks ties so the order never shuffles.
    query = query.order_by(Submission.submitted_at.asc(), Submission.id.asc())

    rows = [
        QueueRow(
            submission_id=s.id,
            intern_name=name,
            assignment_id=s.assignment_id,
            assignment_title=title,
            team_id=team,
            team_name=team_name,
            cohort_id=cohort,
            cohort_name=cohort_name,
            track_name=track_name,
            submitted_at=s.submitted_at,
            status=s.status,
        )
        for s, name, title, team, team_name, cohort, cohort_name, track_name in db.execute(query)
    ]
    return QueueResponse(rows=rows, filters=filters)


def _options(pairs) -> list[Option]:  # noqa: ANN001
    seen: dict[int, str] = {}
    for key, name in pairs:
        if key is not None and name is not None:
            seen[key] = name
    return [Option(id=k, name=v) for k, v in sorted(seen.items(), key=lambda kv: kv[1].lower())]
