"""Invite links: how a new person joins an organization (SCRUM-11).

An admin or supervisor creates an invite for one email address. The link
carries a random token; the database keeps only its SHA-256, as with
``auth_session``, so a leaked row cannot be turned back into a working link.

Opening the link shows who sent it and what the person is joining. Accepting
creates the ``person`` and the ``membership`` in one transaction and stamps
``accepted_at``, which is what makes a link single-use. An invite is also
dead once ``expires_at`` has passed or an admin has set ``revoked_at``.

Invites are created by ``scripts/create_invite.py`` until the admin invite
screen (SCRUM-39) lands; ``create_invite`` here is what both will call.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from zoneinfo import available_timezones

from sqlalchemy import select, update
from sqlalchemy.orm import Session

import sessions
from models import Invite, Membership, Person
from security import hash_password

# Interns are students: a link sent on a Monday may not be opened for weeks.
# Single-use and tied to one email, so a long window costs little.
INVITE_LIFETIME = timedelta(days=30)

# Matches the P05 frame ("At least 10 characters").
MIN_PASSWORD_LENGTH = 10


class InviteAlreadyUsedError(Exception):
    """Raised when a second accept races the first and loses."""


class InviteState(StrEnum):
    OPEN = "open"
    EXPIRED = "expired"
    USED = "used"
    REVOKED = "revoked"


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def as_utc(moment: datetime) -> datetime:
    """SQLite hands back naive datetimes; every stored time is UTC."""
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def state_of(invite: Invite) -> InviteState:
    """What the link can do right now. Used and revoked win over expired."""
    if invite.accepted_at is not None:
        return InviteState.USED
    if invite.revoked_at is not None:
        return InviteState.REVOKED
    if sessions.now() >= as_utc(invite.expires_at):
        return InviteState.EXPIRED
    return InviteState.OPEN


def find_invite(db: Session, token: str) -> Invite | None:
    """The invite behind a URL token, in any state, or None if no such link."""
    return db.scalar(select(Invite).where(Invite.token_hash == _hash(token)))


def create_invite(
    db: Session,
    *,
    organization_id: int,
    invited_by_membership_id: int,
    email: str,
    role: str = "member",
    team_id: int | None = None,
    cohort_id: int | None = None,
    track_id: int | None = None,
) -> tuple[Invite, str]:
    """Record an invite and return it with the one-time URL token.

    The token is returned exactly once, here. Only its hash is stored.
    """
    token = secrets.token_urlsafe(32)
    created = sessions.now()
    invite = Invite(
        organization_id=organization_id,
        invited_by_membership_id=invited_by_membership_id,
        email=email.strip().lower(),
        role=role,
        team_id=team_id,
        cohort_id=cohort_id,
        track_id=track_id,
        token_hash=_hash(token),
        expires_at=created + INVITE_LIFETIME,
        created_at=created,
    )
    db.add(invite)
    db.commit()
    return invite, token


def safe_timezone(name: str | None) -> str:
    """An IANA zone the database can trust: the browser's if valid, else UTC.

    The profile page (SCRUM-17) lets the person correct it later.
    """
    return name if name in available_timezones() else "UTC"


def accept_invite(
    db: Session, invite: Invite, *, full_name: str, password: str, timezone: str | None
) -> Person:
    """Create the account and the membership in one step and use up the link.

    The caller has already checked ``state_of`` and that no account exists
    for the email. The ``accepted_at`` stamp is a conditional UPDATE, so two
    simultaneous submits cannot both succeed.
    """
    accepted = sessions.now()
    claimed = db.execute(
        update(Invite)
        .where(Invite.id == invite.id, Invite.accepted_at.is_(None))
        .values(accepted_at=accepted)
    )
    if claimed.rowcount != 1:
        db.rollback()
        raise InviteAlreadyUsedError
    person = Person(
        email=invite.email,
        full_name=full_name.strip(),
        password_hash=hash_password(password),
        timezone=safe_timezone(timezone),
    )
    db.add(person)
    db.flush()  # gives person.id for the membership
    db.add(
        Membership(
            person_id=person.id,
            organization_id=invite.organization_id,
            role=invite.role,
            team_id=invite.team_id,
            cohort_id=invite.cohort_id,
            track_id=invite.track_id,
        )
    )
    db.commit()
    db.refresh(person)
    return person
