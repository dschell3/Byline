"""A supervisor's decision on one submission (SCRUM-26, P20).

``POST /submissions/{id}/review`` writes a final review: approve or request
changes, a score for every criterion of the assignment, and an optional
written reason. SCRUM-27 makes the reason required on ``changes_requested``;
until then it may be left out.

Rules, in the order they are checked:

* Only a supervisor or admin in the submission's organization may review, and
  never their own work. Everyone else gets the same 403 as ``GET``.
* Only the latest version can be reviewed, and only while it is waiting
  (``submitted``). Anything else is a 409: someone already decided, or the
  member has sent a newer version.
* Every criterion of the assignment gets exactly one score, from 0 to its
  ``max_points``. Anything else is a 422.

The review row is the source of truth; ``submission.status`` is the cached
copy that My Work and the queue read, so both are written in one transaction.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import work
from models import (
    AssessmentCriterion,
    Membership,
    Person,
    Review,
    ReviewCriterionScore,
    Submission,
)

MAX_REASON_LENGTH = 4000
MAX_NOTE_LENGTH = 1000
WAITING = "submitted"

NOT_WAITING = "This version is not waiting for review. Reload to see where it stands."
NOT_LATEST = "The member has sent a newer version. Review that one instead."


class ScoreIn(BaseModel):
    criterion_id: int
    score: int = Field(ge=0)
    note: str | None = Field(default=None, max_length=MAX_NOTE_LENGTH)

    @field_validator("note")
    @classmethod
    def blank_is_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class ReviewIn(BaseModel):
    decision: Literal["approved", "changes_requested"]
    reason: str | None = Field(default=None, max_length=MAX_REASON_LENGTH)
    scores: list[ScoreIn]

    @field_validator("reason")
    @classmethod
    def blank_is_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class ReviewError(Exception):
    """A request the rules turn down. ``status`` is the HTTP code to answer with."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


def reviewer(db: Session, caller: Person, owner: Membership) -> Membership | None:
    """The membership the review is written under, or None if the caller may not review."""
    if owner.person_id == caller.id:
        return None
    return work.supervising_membership(db, caller, owner.organization_id)


def _latest_version(db: Session, submission: Submission) -> int:
    return db.scalar(
        select(func.max(Submission.version)).where(
            Submission.assignment_id == submission.assignment_id,
            Submission.membership_id == submission.membership_id,
        )
    )


def _check_scores(criteria: list[AssessmentCriterion], scores: list[ScoreIn]) -> dict[int, ScoreIn]:
    """Every criterion scored once, each within its maximum. Raises a 422 otherwise."""
    by_id = {c.id: c for c in criteria}
    given: dict[int, ScoreIn] = {}
    for s in scores:
        criterion = by_id.get(s.criterion_id)
        if criterion is None:
            raise ReviewError(422, "A score names a criterion this assignment does not have.")
        if s.criterion_id in given:
            raise ReviewError(422, "Each criterion gets one score.")
        if s.score > criterion.max_points:
            raise ReviewError(
                422, f"“{criterion.text}” is out of {criterion.max_points}, not {s.score}."
            )
        given[s.criterion_id] = s
    missing = [c for c in criteria if c.id not in given]
    if missing:
        raise ReviewError(422, f"Score every criterion first. Missing: “{missing[0].text}”.")
    return given


def decide(db: Session, submission: Submission, author: Membership, body: ReviewIn) -> Review:
    """Write the final review and its scores, and move the submission to its new status.

    Raises ReviewError for a version that cannot be reviewed or scores that do
    not fit the checklist. The caller commits.
    """
    # Lock the row so two supervisors pressing at once cannot both decide.
    db.execute(select(Submission.id).where(Submission.id == submission.id).with_for_update())
    db.refresh(submission)
    if submission.version != _latest_version(db, submission):
        raise ReviewError(409, NOT_LATEST)
    if submission.status != WAITING:
        raise ReviewError(409, NOT_WAITING)

    criteria = list(
        db.scalars(
            select(AssessmentCriterion)
            .where(AssessmentCriterion.assignment_id == submission.assignment_id)
            .order_by(AssessmentCriterion.position)
        )
    )
    given = _check_scores(criteria, body.scores)

    review = Review(
        submission_id=submission.id,
        actor_type="person",
        actor_id=author.id,
        decision=body.decision,
        reason=body.reason,
        is_final=True,
    )
    db.add(review)
    db.flush()
    db.add_all(
        ReviewCriterionScore(
            review_id=review.id,
            criterion_id=c.id,
            score=given[c.id].score,
            note=given[c.id].note,
        )
        for c in criteria
    )
    submission.status = body.decision
    db.flush()
    return review
