"""The submission page's data (SCRUM-22, P14).

``GET /submissions/{id}`` is the history of the work that version belongs to.
``POST /submissions/{id}/comments`` adds to that version's thread. Both are
allowed for the member who made it or a supervisor or admin in the same
organization; everyone else, and any id that does not exist, gets 403.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

import submissions
import work
from db import get_db
from models import Membership, Submission
from sessions import NOT_ALLOWED, CurrentUser, current_user

router = APIRouter(prefix="/submissions", tags=["submissions"])

BAD_PARENT = "Replies go on a comment on this same submission."


def _visible(db: Session, user: CurrentUser, submission_id: int) -> Submission:
    submission = db.get(Submission, submission_id)
    owner = db.get(Membership, submission.membership_id) if submission else None
    if submission is None or owner is None or not work.can_view(db, user.person, owner):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=NOT_ALLOWED)
    return submission


@router.get("/{submission_id}", response_model=submissions.SubmissionDetail)
def submission_detail(
    submission_id: int,
    response: Response,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> submissions.SubmissionDetail:
    """Every version, each review with its scores, and the comments, oldest first."""
    submission = _visible(db, user, submission_id)
    response.headers["Cache-Control"] = "no-store"
    return submissions.history(db, submission)


@router.post(
    "/{submission_id}/comments",
    response_model=submissions.CommentOut,
    status_code=status.HTTP_201_CREATED,
)
def add_comment(
    submission_id: int,
    body: submissions.CommentIn,
    response: Response,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> submissions.CommentOut:
    """Add a comment, or a reply to a top-level comment, on this version."""
    submission = _visible(db, user, submission_id)
    author = submissions.commenter(db, user.person, submission)
    if author is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=NOT_ALLOWED)
    comment = submissions.add_comment(db, submission, author, body.body, body.parent_comment_id)
    if comment is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=BAD_PARENT)
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    return submissions.CommentOut(
        id=comment.id,
        author_membership_id=author.id,
        author_name=user.person.full_name,
        parent_comment_id=comment.parent_comment_id,
        body=comment.body,
        created_at=comment.created_at,
    )
