"""Public forgot-password and reset-password API (SCRUM-10)."""

from typing import Self

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

import reset_mail
from db import get_db
from invites import MIN_PASSWORD_LENGTH
from models import Person
from password_reset import (
    ResetState,
    get_reset_state,
    issue_reset_token,
    redeem_reset_token,
)
from ratelimit import FailureLimiter
from routers.auth import client_ip

router = APIRouter(prefix="/auth", tags=["auth"])
# Limit reset requests even for emails that do not have an account.
# Keep the public confirmation identical for all requests.
reset_by_email = FailureLimiter(limit=3, window=3600)
reset_by_ip = FailureLimiter(limit=20, window=3600)

CONFIRMATION = "If an account exists for this email, we'll send a password reset link."


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class MessageResponse(BaseModel):
    message: str


class ResetStatusResponse(BaseModel):
    state: ResetState


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=1024)
    confirm_password: str

    @model_validator(mode="after")
    def passwords_match(self) -> Self:
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    body: ForgotPasswordRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    response: Response,
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Always return the same confirmation and limit repeated requests."""
    response.headers["Cache-Control"] = "no-store"

    email = str(body.email).strip().lower()
    ip = client_ip(request)

    # Don't reveal whether an account exists or a request was throttled.
    if reset_by_email.retry_after(email) or reset_by_ip.retry_after(ip):
        return MessageResponse(message=CONFIRMATION)

    # Count both known and unknown email addresses.
    reset_by_email.record_failure(email)
    reset_by_ip.record_failure(ip)

    person = db.scalar(select(Person).where(Person.email == email))

    if person is not None:
        token = issue_reset_token(db, person.id)
        background_tasks.add_task(reset_mail.send_reset_email, person.email, token)

    return MessageResponse(message=CONFIRMATION)


@router.get(
    "/reset-password/{token}",
    response_model=ResetStatusResponse,
)
def reset_status(
    token: str,
    response: Response,
    db: Session = Depends(get_db),
) -> ResetStatusResponse:
    """Allow P03 to distinguish valid, expired and used links."""
    response.headers["Cache-Control"] = "no-store"
    return ResetStatusResponse(state=get_reset_state(db, token))


@router.post(
    "/reset-password/{token}",
    response_model=ResetStatusResponse,
)
def reset_password(
    token: str,
    body: ResetPasswordRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> ResetStatusResponse:
    """Change the password and consume the link exactly once."""
    response.headers["Cache-Control"] = "no-store"

    state = redeem_reset_token(db, token, body.new_password)

    if state is ResetState.EXPIRED:
        raise HTTPException(
            status_code=410,
            detail={
                "state": "expired",
                "message": "This reset link has expired.",
            },
        )

    if state is ResetState.USED:
        raise HTTPException(
            status_code=410,
            detail={
                "state": "used",
                "message": "This reset link was already used.",
            },
        )

    if state is ResetState.INVALID:
        raise HTTPException(
            status_code=404,
            detail={
                "state": "invalid",
                "message": "This reset link is invalid.",
            },
        )

    return ResetStatusResponse(state=ResetState.SUCCESS)
