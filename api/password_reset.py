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
    """Generate a secure token and retire earlier unused links."""
    now = datetime.now(UTC)

    # Serialize reset requests for the same account.
    db.execute(select(Person.id).where(Person.id == person_id).with_for_update()).scalar_one()

    # Retire earlier unused reset links for this person.
    db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.person_id == person_id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=now)
    )

    # Generate a new secure token and store only its hash.
    token = secrets.token_urlsafe(32)
    db.add(
        PasswordResetToken(
            person_id=person_id,
            token_hash=_hash_token(token),
            expires_at=now + TOKEN_LIFETIME,
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
        select(PasswordResetToken).where(PasswordResetToken.token_hash == _hash_token(token))
    )

    if record is None:
        db.rollback()
        return ResetState.INVALID

    # Lock the account before changing or checking token state.
    # Issuing and redeeming tokens now use the same lock order.
    person = db.scalar(select(Person).where(Person.id == record.person_id).with_for_update())

    if person is None:
        db.rollback()
        return ResetState.INVALID

    # Re-read the token after acquiring the account lock.
    # Another request may have retired it while we waited.
    db.refresh(record, with_for_update=True)

    now = datetime.now(UTC)
    state = _state(record, now)

    if state is not ResetState.VALID:
        db.rollback()
        return state

    person.password_hash = hash_password(new_password)
    record.used_at = now

    # Retire every other unused reset link for this account.
    db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.person_id == person.id,
            PasswordResetToken.id != record.id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=now)
    )

    # Revoke existing sessions after the password reset.
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
