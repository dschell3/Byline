"""SCRUM-19 and SCRUM-21: hand in work, or hand it in again after changes were requested."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

import assignments
import late_policy
import resubmit
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
    """Accept a first submission, or a resubmission after changes were requested.

    One endpoint for both. The server picks the version number; earlier
    versions are never changed. The new row is ``submitted``, which puts it
    back in the supervisor's queue.
    """

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

    # SCRUM-21: a second hand-in is allowed only after changes were requested.
    latest = resubmit.latest_version(db, assignment.id, member.id)

    if latest is not None and not resubmit.can_resubmit(latest):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This assignment has already been submitted.",
        )

    submitted_at = sessions.now()

    # Lateness is judged on the first hand-in only (SCRUM-23), so a resubmission
    # after the deadline is still accepted.
    if latest is None and not late_policy.can_still_be_handed_in(assignment, submitted_at):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The submission deadline has passed.",
        )

    submission = Submission(
        assignment_id=assignment.id,
        membership_id=member.id,
        version=resubmit.next_version(latest),
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
