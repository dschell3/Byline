"""SCRUM-19: create a member's first assignment submission."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

import assignments
import late_policy
import sessions
from db import get_db
from models import Assignment, Membership, Person, Submission
from sessions import NOT_ALLOWED, CurrentUser, current_user
from submit_work import SubmitWorkRequest

router = APIRouter(prefix="/assignments", tags=["submissions"])


class CreatedSubmission(BaseModel):
    id: int
    assignment_id: int
    version: int
    kind: str
    content: str
    status: str
    submitted_at: datetime


@router.post(
    "/{assignment_id}/submissions",
    response_model=CreatedSubmission,
    status_code=status.HTTP_201_CREATED,
)
def create_submission(
    assignment_id: int,
    body: SubmitWorkRequest,
    response: Response,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> CreatedSubmission:
    """Accept a first submission from an assigned, active member."""

    # Coordinate simultaneous submissions from the same account.
    db.scalar(select(Person.id).where(Person.id == user.person.id).with_for_update())

    # A person can belong to more than one organization.
    memberships = db.scalars(
        select(Membership)
        .where(
            Membership.person_id == user.person.id,
            Membership.is_active.is_(True),
            Membership.role == "member",
        )
        .order_by(Membership.id)
    ).all()

    assignment = None
    member = None

    for candidate in memberships:
        matching_assignment = db.scalar(
            select(Assignment).where(
                Assignment.id == assignment_id,
                assignments.assigned_to(candidate),
            )
        )
        if matching_assignment is not None:
            member = candidate
            assignment = matching_assignment
            break

    if member is None or assignment is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=NOT_ALLOWED,
        )

    # SCRUM-21 handles resubmission after review.
    previous_submission = db.scalar(
        select(Submission.id).where(
            Submission.assignment_id == assignment.id,
            Submission.membership_id == member.id,
        )
    )

    if previous_submission is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This assignment has already been submitted.",
        )

    submitted_at = sessions.now()

    if not late_policy.can_still_be_handed_in(assignment, submitted_at):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The submission deadline has passed.",
        )

    submission = Submission(
        assignment_id=assignment.id,
        membership_id=member.id,
        version=1,
        file_keys=None,
        submission_kind=body.kind,
        content=body.content,
        status="submitted",
        submitted_at=submitted_at,
    )

    db.add(submission)
    db.commit()
    db.refresh(submission)

    response.headers["Cache-Control"] = "no-store"

    return CreatedSubmission(
        id=submission.id,
        assignment_id=submission.assignment_id,
        version=submission.version,
        kind=body.kind,
        content=body.content,
        status=submission.status,
        submitted_at=submission.submitted_at,
    )
