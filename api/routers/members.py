"""One member's work, behind a role check (SCRUM-14).

``GET /members/{id}/work`` is allowed for your own membership, or for a
supervisor or admin in the same organization. Everyone else gets 403, and so
does an id that does not exist, so the answer never says which ids are real.
``GET /me/work`` is this same call with your own membership.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

import work
from db import get_db
from models import Membership
from sessions import NOT_ALLOWED, CurrentUser, current_user

router = APIRouter(prefix="/members", tags=["members"])


@router.get("/{membership_id}/work", response_model=work.WorkResponse)
def member_work(
    membership_id: int,
    response: Response,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> work.WorkResponse:
    """Assignments for one member, in the six My Work groups."""
    target = db.get(Membership, membership_id)
    if target is None or not work.can_view(db, user.person, target):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=NOT_ALLOWED)
    response.headers["Cache-Control"] = "no-store"
    return work.for_member(db, target)
