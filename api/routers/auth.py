"""Sign-in endpoint (SCRUM-9).

Every failure, wrong password or unknown email, returns the same status,
the same body and takes the same time, so the response never reveals
whether an account exists. Sessions and cookies are added on the success
path by SCRUM-13.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import get_db
from models import Person
from ratelimit import by_account, by_ip
from security import verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

INVALID_CREDENTIALS = "Email or password is incorrect."
TOO_MANY_ATTEMPTS = "Too many sign-in attempts. Try again later."


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class SignInResponse(BaseModel):
    id: int
    full_name: str


def client_ip(request: Request) -> str:
    """The caller's address, honouring the proxy header Render sets."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _too_many(retry_after: int) -> HTTPException:
    return HTTPException(
        status.HTTP_429_TOO_MANY_REQUESTS,
        detail=TOO_MANY_ATTEMPTS,
        headers={"Retry-After": str(retry_after)},
    )


@router.post("/sign-in", response_model=SignInResponse)
def sign_in(
    body: SignInRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> SignInResponse:
    """Check credentials. 401 on any failure, 429 when a limit is hit."""
    email = body.email.lower()
    ip = client_ip(request)

    wait = max(by_ip.retry_after(ip), by_account.retry_after(email))
    if wait:
        raise _too_many(wait)

    person = db.scalar(select(Person).where(Person.email == email))
    # Runs on both paths: against the dummy hash when there is no account.
    ok = verify_password(body.password, person.password_hash if person else None)

    if not ok or person is None:
        by_ip.record_failure(ip)
        by_account.record_failure(email)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=INVALID_CREDENTIALS)

    by_account.clear(email)
    response.headers["Cache-Control"] = "no-store"
    return SignInResponse(id=person.id, full_name=person.full_name)
