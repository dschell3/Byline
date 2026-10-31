"""Secure password-reset token handling for SCRUM-10."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from models import AuthSession, PasswordResetToken, Person
from security import hash_password

TOKEN_LIFETIME = timedelta(hours=1)


class ResetState(StrEnum):
    VALID = "valid"
    INVALID = "invalid"
    EXPIRED = "expired"
    USED = "used"
    SUCCESS = "success"


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def issue_reset_token(db: Session, person_id: int) -> str:
    """Generate a secure token; store only its hash."""
    token = secrets.token_urlsafe(32)
    db.add(
        PasswordResetToken(
            person_id=person_id,
            token_hash=_hash_token(token),
            expires_at=datetime.now(UTC) + TOKEN_LIFETIME,
        )
    )
    db.commit()
    return token


def _state(record: PasswordResetToken | None, now: datetime) -> ResetState:
    if record is None:
        return ResetState.INVALID
    if record.used_at is not None:
        return ResetState.USED
    if now >= _as_utc(record.expires_at):
        return ResetState.EXPIRED
    return ResetState.VALID


def get_reset_state(db: Session, token: str) -> ResetState:
    """Return the current state without consuming the token."""
    record = db.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == _hash_token(token))
    )
    return _state(record, datetime.now(UTC))


def redeem_reset_token(db: Session, token: str, new_password: str) -> ResetState:
    """Consume a reset link and update the password atomically."""
    record = db.scalar(
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == _hash_token(token))
        .with_for_update()
    )

    now = datetime.now(UTC)
    state = _state(record, now)
    if state is not ResetState.VALID:
        db.rollback()
        return state

    person = db.get(Person, record.person_id)
    if person is None:
        db.rollback()
        return ResetState.INVALID

    person.password_hash = hash_password(new_password)
    record.used_at = now

    # Sign out existing sessions after a password reset.
    db.execute(
        update(AuthSession)
        .where(
            AuthSession.person_id == person.id,
            AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    db.commit()
    return ResetState.SUCCESS
