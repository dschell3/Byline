"""Open an email verification link (SCRUM-12, P04).

Both endpoints are public: the person may not be signed in when they click
the link in their email.

* ``POST /verify/{token}`` uses the link and answers with one of the three
  P04 states (``verified``, ``expired``, ``already_verified``). It is a POST,
  not a GET, so a mail scanner that prefetches the link cannot use it up.
* ``POST /verify/{token}/resend`` sends a new link after an expired one.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

import verifications
from db import get_db
from models import EmailVerification
from verifications import VerificationState

router = APIRouter(prefix="/verify", tags=["verify"])

NOT_FOUND = "This verification link is not valid. Check the link in your email."
NOTHING_TO_RESEND = "This link has not expired, so there is nothing to resend."


class VerifyResponse(BaseModel):
    state: VerificationState
    email: str
    # When the address was confirmed. Null only for the expired state.
    verified_at: datetime | None


class ResendResponse(BaseModel):
    email: str


def _verification_or_404(db: Session, token: str) -> EmailVerification:
    verification = verifications.find_verification(db, token)
    if verification is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
    return verification


@router.post("/{token}", response_model=VerifyResponse)
def verify_email(token: str, response: Response, db: Session = Depends(get_db)) -> VerifyResponse:
    """Use the link and say which screen to show. 404 if there is no such link."""
    response.headers["Cache-Control"] = "no-store"
    outcome = verifications.confirm(db, _verification_or_404(db, token))
    return VerifyResponse(state=outcome.state, email=outcome.email, verified_at=outcome.verified_at)


@router.post("/{token}/resend", response_model=ResendResponse, status_code=status.HTTP_202_ACCEPTED)
def resend_verification(
    token: str, response: Response, db: Session = Depends(get_db)
) -> ResendResponse:
    """Send a new link to the same person. 409 unless the link has expired unused."""
    response.headers["Cache-Control"] = "no-store"
    verification = _verification_or_404(db, token)
    if not verifications.can_resend(db, verification):
        raise HTTPException(status.HTTP_409_CONFLICT, detail=NOTHING_TO_RESEND)
    return ResendResponse(email=verifications.resend(db, verification))
