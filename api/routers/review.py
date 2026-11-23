"""The review queue (SCRUM-24, P19): ``GET /review/queue``.

Supervisors and admins only. Everyone else gets 403.
"""

from typing import Literal

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

import review_queue
from db import get_db
from sessions import CurrentUser, require_role

router = APIRouter(prefix="/review", tags=["review"])


@router.get("/queue", response_model=review_queue.QueueResponse)
def review_queue_list(
    response: Response,
    status: Literal["submitted", "changes_requested", "approved", "all"] = "submitted",
    team_id: int | None = None,
    cohort_id: int | None = None,
    assignment_id: int | None = None,
    user: CurrentUser = Depends(require_role("supervisor", "admin")),
    db: Session = Depends(get_db),
) -> review_queue.QueueResponse:
    """Work waiting for review, oldest first, in the caller's team (or organization for admins)."""
    response.headers["Cache-Control"] = "no-store"
    return review_queue.queue(
        db,
        user.person,
        status=status,
        team_id=team_id,
        cohort_id=cohort_id,
        assignment_id=assignment_id,
    )
