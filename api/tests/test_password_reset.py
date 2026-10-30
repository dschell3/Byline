"""SCRUM-10: password reset security and lifecycle tests."""

from datetime import UTC, datetime, timedelta
from hashlib import sha256

import pytest
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from db import Base
from models import AuthSession, PasswordResetToken, Person
from password_reset import (
    TOKEN_LIFETIME,
    ResetState,
    get_reset_state,
    issue_reset_token,
    redeem_reset_token,
)
from security import hash_password, verify_password

OLD_PASSWORD = "original-password-123"
NEW_PASSWORD = "replacement-password-456"


@pytest.fixture
def factory() -> sessionmaker[Session]:
    """Fresh isolated database with one account and active session."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    tables = [Person, AuthSession, PasswordResetToken]
    Base.metadata.create_all(engine, tables=[model.__table__ for model in tables])
    make_session = sessionmaker(bind=engine)

    with make_session() as db:
        db.add(
            Person(
                id=1,
                email="member@example.com",
                full_name="Test Member",
                password_hash=hash_password(OLD_PASSWORD),
            )
        )
        db.add(
            AuthSession(
                id=1,
                person_id=1,
                token_hash="existing-session-hash",
            )
        )
        db.commit()

    return make_session


def test_token_is_hashed_in_database(
    factory: sessionmaker[Session],
) -> None:
    with factory() as db:
        token = issue_reset_token(db, 1)
        record = db.scalar(select(PasswordResetToken))

        assert record is not None
        assert record.token_hash == sha256(token.encode()).hexdigest()
        assert token != record.token_hash
        assert get_reset_state(db, token) == ResetState.VALID


def test_token_has_one_hour_lifetime(
    factory: sessionmaker[Session],
) -> None:
    before = datetime.now(UTC)
    with factory() as db:
        token = issue_reset_token(db, 1)
        record = db.scalar(select(PasswordResetToken))

        assert record is not None
        assert TOKEN_LIFETIME == timedelta(hours=1)
        expiry = record.expires_at
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=UTC)
        assert before + timedelta(minutes=59) < expiry
        assert expiry <= datetime.now(UTC) + TOKEN_LIFETIME
        assert get_reset_state(db, token) == ResetState.VALID


def test_unknown_token_is_rejected(
    factory: sessionmaker[Session],
) -> None:
    with factory() as db:
        assert get_reset_state(db, "unknown") == ResetState.INVALID
        assert redeem_reset_token(db, "unknown", NEW_PASSWORD) == ResetState.INVALID


def test_expired_token_cannot_change_password(
    factory: sessionmaker[Session],
) -> None:
    with factory() as db:
        token = issue_reset_token(db, 1)
        db.execute(
            update(PasswordResetToken).values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )
        db.commit()

        assert get_reset_state(db, token) == ResetState.EXPIRED
        assert redeem_reset_token(db, token, NEW_PASSWORD) == ResetState.EXPIRED
        person = db.get(Person, 1)
        assert verify_password(OLD_PASSWORD, person.password_hash)


def test_successful_reset_changes_password_and_revokes_sessions(
    factory: sessionmaker[Session],
) -> None:
    with factory() as db:
        token = issue_reset_token(db, 1)

        assert redeem_reset_token(db, token, NEW_PASSWORD) == ResetState.SUCCESS

        person = db.get(Person, 1)
        assert verify_password(NEW_PASSWORD, person.password_hash)
        assert not verify_password(OLD_PASSWORD, person.password_hash)

        session = db.get(AuthSession, 1)
        assert session.revoked_at is not None
        assert get_reset_state(db, token) == ResetState.USED


def test_token_cannot_be_reused(
    factory: sessionmaker[Session],
) -> None:
    with factory() as db:
        token = issue_reset_token(db, 1)

        assert redeem_reset_token(db, token, NEW_PASSWORD) == ResetState.SUCCESS
        assert redeem_reset_token(db, token, "another-password-789") == ResetState.USED

        person = db.get(Person, 1)
        assert verify_password(NEW_PASSWORD, person.password_hash)
