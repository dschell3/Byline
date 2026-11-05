"""What happens to work handed in after its due date (SCRUM-23).

Every assignment has one of three late policies:

- ``not_accepted``: nothing can be handed in once the due date has passed
- ``accepted_full_points``: late work is still taken, and is worth full points
- ``accepted_half_points``: late work is still taken, but is worth half points

``late_cutoff_hours``, when set, is how long after the due date late work is
still taken. So the Figma's "accepted up to 48 hours late at half points" is
``accepted_half_points`` with a cutoff of 48.

Late means handed in after the exact moment ``due_at`` names. Both times are
stored in UTC, so the answer is the same wherever the intern or supervisor
is: a due date of 11:59:59 PM in India and a hand-in at 11:59:59 PM in India
are the same instant, and that is on time. Work with no due date is never late.
"""

from datetime import datetime, timedelta

from invites import as_utc
from models import Assignment

NOT_ACCEPTED = "not_accepted"
ACCEPTED_FULL_POINTS = "accepted_full_points"
ACCEPTED_HALF_POINTS = "accepted_half_points"


def was_handed_in_late(assignment: Assignment, handed_in_at: datetime) -> bool:
    """True when the work came in after the assignment's due date."""
    if assignment.due_at is None:
        return False
    return as_utc(handed_in_at) > as_utc(assignment.due_at)


def last_moment_late_work_is_taken(assignment: Assignment) -> datetime | None:
    """When late work stops being taken, or None if there is no such moment.

    None covers two cases: there is no due date, or late work is accepted with
    no cutoff. For ``not_accepted`` the last moment is the due date itself.
    """
    if assignment.due_at is None:
        return None
    due_at = as_utc(assignment.due_at)
    if assignment.late_policy == NOT_ACCEPTED:
        return due_at
    if assignment.late_cutoff_hours is None:
        return None
    return due_at + timedelta(hours=assignment.late_cutoff_hours)


def can_still_be_handed_in(assignment: Assignment, at: datetime) -> bool:
    """True while the assignment will still take a hand-in at the moment ``at``."""
    last_moment = last_moment_late_work_is_taken(assignment)
    return last_moment is None or as_utc(at) <= last_moment


def points_after_late_penalty(assignment: Assignment, handed_in_at: datetime) -> int:
    """What the work is worth once the late policy has been applied.

    On-time work, and late work under ``accepted_full_points``, keep every point.
    Under ``accepted_half_points`` late work is worth half, rounded up, so the
    intern gets the odd point: 15 becomes 8.
    """
    full_points = assignment.points_value
    if not was_handed_in_late(assignment, handed_in_at):
        return full_points
    if assignment.late_policy == ACCEPTED_FULL_POINTS:
        return full_points
    if assignment.late_policy == ACCEPTED_HALF_POINTS:
        return (full_points + 1) // 2
    raise ValueError(
        f"Assignment {assignment.id} does not accept late work, so a late hand-in has no "
        "points to work out. Check can_still_be_handed_in() before accepting it."
    )
