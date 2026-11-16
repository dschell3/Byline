"""SCRUM-21: when a member may hand in again, and which version number it gets.

A resubmit is a new ``submission`` row with ``version + 1``; the earlier rows
are never changed. A member may resubmit only after a supervisor asked for
changes on their latest version.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Submission


def latest_version(db: Session, assignment_id: int, membership_id: int) -> Submission | None:
    """The member's newest version of this assignment, or None before the first hand-in."""
    return db.scalar(
        select(Submission)
        .where(
            Submission.assignment_id == assignment_id,
            Submission.membership_id == membership_id,
        )
        .order_by(Submission.version.desc())
        .limit(1)
    )


def can_resubmit(latest: Submission | None) -> bool:
    """True only when the latest version came back with changes requested."""
    return latest is not None and latest.status == "changes_requested"


def next_version(latest: Submission | None) -> int:
    """1 for a first hand-in, otherwise one more than the latest version."""
    return 1 if latest is None else latest.version + 1
