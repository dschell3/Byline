"""The signed-in member's own home screen data (SCRUM-16).

``GET /me/home`` answers the first-run screen (P11): which organization,
cohort, track and supervisor this person belongs to, their onboarding pack,
and whether anything has been assigned yet. Once ``has_work`` is true the
web app shows My Work (P10) instead.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

import assignments
from db import get_db
from models import Cohort, Membership, Organization, Person, Track
from sessions import CurrentUser, current_user

router = APIRouter(prefix="/me", tags=["me"])

NO_MEMBERSHIP = "You are not part of an organization yet."


class OrganizationOut(BaseModel):
    name: str


class CohortOut(BaseModel):
    name: str
    starts_on: date | None
    ends_on: date | None


class TrackOut(BaseModel):
    name: str
    onboarding_pack_url: str | None


class SupervisorOut(BaseModel):
    full_name: str
    email: str


class HomeResponse(BaseModel):
    full_name: str
    timezone: str
    organization: OrganizationOut
    cohort: CohortOut | None
    track: TrackOut | None
    supervisor: SupervisorOut | None
    has_work: bool


def _home_membership(db: Session, person_id: int) -> Membership | None:
    """The membership the home screen is about: an active member one, else any active one."""
    rows = db.scalars(
        select(Membership)
        .where(Membership.person_id == person_id, Membership.is_active.is_(True))
        .order_by(Membership.id)
    ).all()
    return next((m for m in rows if m.role == "member"), rows[0] if rows else None)


def _supervisor(db: Session, member: Membership) -> Person | None:
    """The active supervisor of the member's team, if they are on one."""
    if member.team_id is None:
        return None
    return db.scalar(
        select(Person)
        .join(Membership, Membership.person_id == Person.id)
        .where(
            Membership.organization_id == member.organization_id,
            Membership.team_id == member.team_id,
            Membership.role == "supervisor",
            Membership.is_active.is_(True),
        )
        .order_by(Membership.id)
    )


@router.get("/home", response_model=HomeResponse)
def home(
    response: Response,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> HomeResponse:
    """Everything P11 shows. 404 when the person has no active membership."""
    member = _home_membership(db, user.person.id)
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=NO_MEMBERSHIP)

    organization = db.get(Organization, member.organization_id)
    cohort = db.get(Cohort, member.cohort_id) if member.cohort_id else None
    track = db.get(Track, member.track_id) if member.track_id else None
    supervisor = _supervisor(db, member)

    response.headers["Cache-Control"] = "no-store"
    return HomeResponse(
        full_name=user.person.full_name,
        timezone=user.person.timezone,
        organization=OrganizationOut(name=organization.name),
        cohort=CohortOut(name=cohort.name, starts_on=cohort.starts_on, ends_on=cohort.ends_on)
        if cohort
        else None,
        track=TrackOut(name=track.name, onboarding_pack_url=track.onboarding_pack_url)
        if track
        else None,
        supervisor=SupervisorOut(full_name=supervisor.full_name, email=supervisor.email)
        if supervisor
        else None,
        has_work=assignments.has_assigned_work(db, member),
    )
