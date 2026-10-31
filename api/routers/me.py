"""The signed-in member's own home screen data (SCRUM-16).

``GET /me/home`` answers the first-run screen (P11): which organization,
cohort, track and supervisor this person belongs to, their onboarding pack,
and whether anything has been assigned yet. Once ``has_work`` is true the
web app shows My Work (P10) instead.

``GET`` and ``PATCH /me/profile`` serve the profile page (P18, SCRUM-17).
"""

from datetime import UTC, date, datetime
from functools import lru_cache
from typing import Literal, Self
from zoneinfo import available_timezones

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, StrictBool, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

import assignments
import sessions
import work
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


@router.get("/work", response_model=work.WorkResponse)
def my_work(
    response: Response,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> work.WorkResponse:
    """P10 My Work: the same data as GET /members/{id}/work, for your own membership."""
    member = _home_membership(db, user.person.id)
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=NO_MEMBERSHIP)
    response.headers["Cache-Control"] = "no-store"
    return work.for_member(db, member)


# --- Profile (SCRUM-17, page P18) ---------------------------------------------

ContactPreference = Literal["email", "discord", "phone"]

# Fields a PATCH may leave out, but may not send as null.
NOT_NULLABLE = (
    "full_name",
    "timezone",
    "contact_preference",
    "email_assignments",
    "email_reminders",
    "email_digest",
    "public_byline_consent",
)


@lru_cache(maxsize=1)
def _timezone_names() -> frozenset[str]:
    """Every IANA name this server knows. Unknown names are rejected, never defaulted."""
    return frozenset(available_timezones())


def _aware(moment: datetime | None) -> datetime | None:
    """SQLite hands back naive datetimes; every stored time is UTC."""
    if moment is None:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


class ProfileResponse(BaseModel):
    full_name: str
    email: str
    photo_url: str | None
    timezone: str
    contact_preference: str
    contact_detail: str | None
    email_assignments: bool
    email_reminders: bool
    email_digest: bool
    public_byline_consent: bool
    public_byline_consent_at: datetime | None


class ProfilePatch(BaseModel):
    """Any subset of the editable fields. Unknown fields, email included, are ignored."""

    full_name: str | None = None
    photo_url: str | None = None
    timezone: str | None = None
    contact_preference: ContactPreference | None = None
    contact_detail: str | None = None
    email_assignments: StrictBool | None = None
    email_reminders: StrictBool | None = None
    email_digest: StrictBool | None = None
    public_byline_consent: StrictBool | None = None

    @field_validator("full_name")
    @classmethod
    def check_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not 1 <= len(value) <= 200:
            raise ValueError("Name must be 1 to 200 characters.")
        return value

    @field_validator("photo_url")
    @classmethod
    def check_photo_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if (
            not value.lower().startswith("https://")
            or len(value) == len("https://")
            or len(value) > 2048
            or any(char.isspace() for char in value)
        ):
            raise ValueError("Photo must be an https:// link of at most 2048 characters.")
        return value

    @field_validator("timezone")
    @classmethod
    def check_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value not in _timezone_names():
            raise ValueError("Unknown timezone.")
        return value

    @field_validator("contact_detail")
    @classmethod
    def check_contact_detail(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if len(value) > 200:
            raise ValueError("Contact detail must be at most 200 characters.")
        return value or None

    @model_validator(mode="after")
    def reject_nulls(self) -> Self:
        for name in NOT_NULLABLE:
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null.")
        return self


def _profile(person: Person, member: Membership) -> ProfileResponse:
    return ProfileResponse(
        full_name=person.full_name,
        email=person.email,
        photo_url=person.photo_url,
        timezone=person.timezone,
        contact_preference=person.contact_preference,
        contact_detail=person.contact_detail,
        email_assignments=person.email_assignments,
        email_reminders=person.email_reminders,
        email_digest=person.email_digest,
        public_byline_consent=member.public_byline_consent,
        public_byline_consent_at=_aware(member.public_byline_consent_at),
    )


@router.get("/profile", response_model=ProfileResponse)
def profile(
    response: Response,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    """Everything P18 shows. 404 when the person has no active membership."""
    member = _home_membership(db, user.person.id)
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=NO_MEMBERSHIP)
    response.headers["Cache-Control"] = "no-store"
    return _profile(user.person, member)


@router.patch("/profile", response_model=ProfileResponse)
def update_profile(
    body: ProfilePatch,
    response: Response,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    """Change any subset of the editable fields; returns the full profile afterwards.

    Turning byline consent on stamps public_byline_consent_at once. Turning it off
    clears the flag and keeps the stamp as history. One commit covers everything.
    """
    member = _home_membership(db, user.person.id)
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=NO_MEMBERSHIP)

    person = user.person
    changes = body.model_dump(exclude_unset=True)
    consent = changes.pop("public_byline_consent", None)
    for field, value in changes.items():
        setattr(person, field, value)
    if consent is True and not member.public_byline_consent:
        member.public_byline_consent = True
        member.public_byline_consent_at = sessions.now()
    elif consent is False:
        member.public_byline_consent = False
    db.commit()

    response.headers["Cache-Control"] = "no-store"
    return _profile(person, member)
