"""Email verification links: confirming a person owns their address (SCRUM-12).

A link carries a random token; the database keeps only its SHA-256, as with
``invite`` and ``auth_session``. Opening the link (P04) lands on one of three
screens:

* ``verified``: the link was good. It is used up and the person's
  ``email_verified_at`` is stamped.
* ``expired``: 24 hours have passed. The page offers to send a new link.
* ``already_verified``: the link was used before, or the address was
  confirmed some other way. The page says so and offers sign-in.

Confirming is a conditional UPDATE on ``used_at``, so a link works exactly
once even if two requests race.

There is no email service yet. ``deliver`` logs the link so it can be opened
by hand; the notifications card swaps it for a real send. Until then,
``scripts/create_verification.py`` makes a link for testing.
"""

import hashlib
import logging
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from sqlalchemy import select, update
from sqlalchemy.orm import Session

import sessions
from invites import as_utc
from models import EmailVerification, Person

# The SCRUM-12 card: "The token is single-use and expires after 24 hours."
VERIFICATION_LIFETIME = timedelta(hours=24)

logger = logging.getLogger(__name__)


class VerificationState(StrEnum):
    VERIFIED = "verified"
    EXPIRED = "expired"
    ALREADY_VERIFIED = "already_verified"


@dataclass
class Outcome:
    state: VerificationState
    email: str
    verified_at: datetime | None


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def find_verification(db: Session, token: str) -> EmailVerification | None:
    """The verification behind a URL token, in any state, or None if no such link."""
    return db.scalar(select(EmailVerification).where(EmailVerification.token_hash == _hash(token)))


def is_expired(verification: EmailVerification) -> bool:
    return sessions.now() >= as_utc(verification.expires_at)


def create_verification(db: Session, person: Person) -> tuple[EmailVerification, str]:
    """Record a link for the person's current email and return it with the one-time token."""
    token = secrets.token_urlsafe(32)
    created = sessions.now()
    verification = EmailVerification(
        person_id=person.id,
        email=person.email,
        token_hash=_hash(token),
        expires_at=created + VERIFICATION_LIFETIME,
        created_at=created,
    )
    db.add(verification)
    db.commit()
    return verification, token


def link_for(token: str) -> str:
    """The P04 address for a token. SITE_URL is the web app's origin."""
    site = os.environ.get("SITE_URL", "http://localhost:5173").rstrip("/")
    return f"{site}/verify/{token}"


def deliver(email: str, token: str) -> None:
    """Send the link. No email service yet, so it is logged for a developer to open.

    A warning, not info: nothing was actually emailed, and uvicorn shows warnings by default.
    """
    logger.warning(
        "Email sending is not set up yet. Verification link for %s: %s", email, link_for(token)
    )


def confirm(db: Session, verification: EmailVerification) -> Outcome:
    """Use the link if it still can be, and say which of the three screens to show."""
    person = db.get(Person, verification.person_id)
    if verification.used_at is not None:
        return Outcome(
            VerificationState.ALREADY_VERIFIED,
            verification.email,
            as_utc(person.email_verified_at or verification.used_at),
        )
    if person.email_verified_at is not None and person.email == verification.email:
        return Outcome(
            VerificationState.ALREADY_VERIFIED,
            person.email,
            as_utc(person.email_verified_at),
        )
    # Expired, or the person has changed their email since this link was sent.
    if is_expired(verification) or person.email != verification.email:
        return Outcome(VerificationState.EXPIRED, person.email, None)

    confirmed = sessions.now()
    claimed = db.execute(
        update(EmailVerification)
        .where(EmailVerification.id == verification.id, EmailVerification.used_at.is_(None))
        .values(used_at=confirmed)
    )
    if claimed.rowcount != 1:
        # Another request used it first: from here it is simply already verified.
        db.rollback()
        db.refresh(person)
        return Outcome(
            VerificationState.ALREADY_VERIFIED,
            person.email,
            as_utc(person.email_verified_at) if person.email_verified_at else confirmed,
        )
    person.email_verified_at = confirmed
    db.commit()
    return Outcome(VerificationState.VERIFIED, person.email, confirmed)


def can_resend(db: Session, verification: EmailVerification) -> bool:
    """True when the link is in the expired state: unused, unconfirmed, and dead.

    Same rules as ``confirm`` but without using anything up.
    """
    person = db.get(Person, verification.person_id)
    if verification.used_at is not None:
        return False
    if person.email_verified_at is not None and person.email == verification.email:
        return False
    return is_expired(verification) or person.email != verification.email


def resend(db: Session, verification: EmailVerification) -> str:
    """Send a fresh link to the person's current email, after an expired one.

    Only one live link at a time: if an unused, unexpired link was already
    sent after this one, nothing new is created. That stops a stale link
    being used to fill someone's inbox.
    """
    person = db.get(Person, verification.person_id)
    newer = db.scalar(
        select(EmailVerification).where(
            EmailVerification.person_id == person.id,
            EmailVerification.email == person.email,
            EmailVerification.used_at.is_(None),
            EmailVerification.expires_at > sessions.now(),
        )
    )
    if newer is None:
        _, token = create_verification(db, person)
        deliver(person.email, token)
    return person.email
