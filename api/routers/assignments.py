"""The assignment page's data (SCRUM-18, P12).

``GET /assignments/{id}`` is allowed only for a member the assignment was
targeted at. Everyone else, and any id that does not exist, gets 403.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

import assignment_page
from db import get_db
from models import Assignment
from sessions import NOT_ALLOWED, CurrentUser, current_user

router = APIRouter(prefix="/assignments", tags=["assignments"])


@router.get("/{assignment_id}", response_model=assignment_page.AssignmentDetail)
def assignment_detail(
    assignment_id: int,
    response: Response,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> assignment_page.AssignmentDetail:
    """The brief, the criteria checklist, references, late policy and which button to show."""
    member = assignment_page.membership_reached(db, user.person, assignment_id)
    assignment = db.get(Assignment, assignment_id) if member else None
    if member is None or assignment is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=NOT_ALLOWED)
    response.headers["Cache-Control"] = "no-store"
    return assignment_page.detail(db, assignment, member)
