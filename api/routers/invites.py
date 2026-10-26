"""Open and accept an invite link (SCRUM-11).

``GET /invites/{token}`` is public: it tells the person who invited them and
what they are joining, in any state, so the page can show the right screen.
``POST /invites/{token}/accept`` creates the account and the membership in
one action, starts a session and sets its cookie, so the browser lands on
the first-run screen (P11) already signed in.
"""

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

import invites
from db import get_db
from invites import MIN_PASSWORD_LENGTH, InviteState
from models import Cohort, Invite, Membership, Organization, Person, Track
from sessions import COOKIE_NAME, end_session, set_session_cookie, start_session

router = APIRouter(prefix="/invites", tags=["invites"])

NOT_FOUND = "This invite link is not valid. Check the link in your email."
ALREADY_HAVE_ACCOUNT = "You already have a Byline account with this email. Sign in instead."
GONE = {
    InviteState.EXPIRED: "This invite has expired. Ask the person who invited you for a new one.",
    InviteState.USED: "This invite was already used. Sign in to continue.",
    InviteState.REVOKED: "This invite was withdrawn. Ask the person who invited you for a new one.",
}


class OrganizationOut(BaseModel):
    name: str


class CohortOut(BaseModel):
    name: str
    starts_on: date | None
    ends_on: date | None


class TrackOut(BaseModel):
    name: str
    onboarding_pack_url: str | None


class InvitedByOut(BaseModel):
    full_name: str
    email: str


class InviteResponse(BaseModel):
    state: InviteState
    email: str
    role: str
    expires_at: datetime
    organization: OrganizationOut
    cohort: CohortOut | None
    track: TrackOut | None
    invited_by: InvitedByOut


class AcceptRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=1024)
    # IANA zone the browser detected. Anything unknown becomes UTC.
    timezone: str | None = None


class AcceptResponse(BaseModel):
    id: int
    full_name: str


def _invite_or_404(db: Session, token: str) -> Invite:
    invite = invites.find_invite(db, token)
    if invite is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
    return invite


def _describe(db: Session, invite: Invite) -> InviteResponse:
    organization = db.get(Organization, invite.organization_id)
    cohort = db.get(Cohort, invite.cohort_id) if invite.cohort_id else None
    track = db.get(Track, invite.track_id) if invite.track_id else None
    inviter = db.scalar(
        select(Person)
        .join(Membership, Membership.person_id == Person.id)
        .where(Membership.id == invite.invited_by_membership_id)
    )
    return InviteResponse(
        state=invites.state_of(invite),
        email=invite.email,
        role=invite.role,
        expires_at=invites.as_utc(invite.expires_at),
        organization=OrganizationOut(name=organization.name),
        cohort=CohortOut(name=cohort.name, starts_on=cohort.starts_on, ends_on=cohort.ends_on)
        if cohort
        else None,
        track=TrackOut(name=track.name, onboarding_pack_url=track.onboarding_pack_url)
        if track
        else None,
        invited_by=InvitedByOut(full_name=inviter.full_name, email=inviter.email),
    )


@router.get("/{token}", response_model=InviteResponse)
def read_invite(token: str, response: Response, db: Session = Depends(get_db)) -> InviteResponse:
    """Who invited you and what you are joining, with the link's state. 404 if no such link."""
    response.headers["Cache-Control"] = "no-store"
    return _describe(db, _invite_or_404(db, token))


@router.post("/{token}/accept", response_model=AcceptResponse, status_code=status.HTTP_201_CREATED)
def accept_invite(
    token: str,
    body: AcceptRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AcceptResponse:
    """Create the account and the membership, sign the person in, use up the link.

    410 when the link is expired, used or withdrawn; 409 when the email
    already has an account; 422 when the password is too short.
    """
    invite = _invite_or_404(db, token)
    state = invites.state_of(invite)
    if state is not InviteState.OPEN:
        raise HTTPException(status.HTTP_410_GONE, detail=GONE[state])
    if db.scalar(select(Person.id).where(Person.email == invite.email)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=ALREADY_HAVE_ACCOUNT)

    try:
        person = invites.accept_invite(
            db,
            invite,
            full_name=body.full_name,
            password=body.password,
            timezone=body.timezone,
        )
    except invites.InviteAlreadyUsedError:
        raise HTTPException(status.HTTP_410_GONE, detail=GONE[InviteState.USED]) from None

    # Same as sign-in: retire whatever session cookie the browser had, issue a fresh one.
    end_session(db, request.cookies.get(COOKIE_NAME))
    set_session_cookie(response, start_session(db, person.id))
    response.headers["Cache-Control"] = "no-store"
    return AcceptResponse(id=person.id, full_name=person.full_name)
