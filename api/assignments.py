"""Who an assignment is for (SCRUM-16; shared with SCRUM-14 My Work).

An assignment reaches a membership when either:

- the membership is one of its picked ``recipient_membership_ids``, or
- it names at least one of team, cohort or track, and every one it names
  matches the membership (so team X + cohort Y means "team X's members in
  cohort Y", not everyone in either).

Always within the same organization. Keep this the one place the rule
lives, so My Work and the first-run screen can never disagree.
"""

from sqlalchemy import ColumnElement, and_, any_, exists, literal, or_, select
from sqlalchemy.orm import Session

from models import Assignment, Membership


def assigned_to(member: Membership) -> ColumnElement[bool]:
    """A WHERE clause selecting the assignments that reach ``member``."""

    def matches(column: ColumnElement, value: int | None) -> ColumnElement[bool]:
        # A filter the assignment leaves empty matches anyone.
        return column.is_(None) if value is None else or_(column.is_(None), column == value)

    by_group = and_(
        or_(
            Assignment.team_id.is_not(None),
            Assignment.cohort_id.is_not(None),
            Assignment.track_id.is_not(None),
        ),
        matches(Assignment.team_id, member.team_id),
        matches(Assignment.cohort_id, member.cohort_id),
        matches(Assignment.track_id, member.track_id),
    )
    picked = literal(member.id) == any_(Assignment.recipient_membership_ids)
    return and_(Assignment.organization_id == member.organization_id, or_(picked, by_group))


def has_assigned_work(db: Session, member: Membership) -> bool:
    """True once anything at all has been assigned to ``member``."""
    return bool(db.scalar(select(exists().where(assigned_to(member)))))
