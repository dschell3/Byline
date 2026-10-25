"""Server-side sessions and per-request roles (SCRUM-13).

Signing in issues a random token in an HTTP-only, Secure, SameSite=Lax
cookie. The browser never sees anything it could read or forge: no
localStorage, no role, no expiry it could edit. The database keeps only the
token's SHA-256, so a leaked row cannot be replayed.

A session ends when any of these is true, checked on every request:

- it was revoked (sign-out, or a newer sign-in from the same browser)
- it has been idle longer than ``IDLE_TIMEOUT``
- it is older than ``ABSOLUTE_TIMEOUT``, however active it has been

Roles are read from ``membership`` on every request, never stored in the
session, so a role change applies on the next request. Scoping a role to one
organization arrives with the tenancy work (1.5b); today a role in any active
membership counts.
"""

import hashlib
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import get_db
from models import AuthSession, Membership, Person

COOKIE_NAME = "byline_session"
IDLE_TIMEOUT = timedelta(hours=2)
ABSOLUTE_TIMEOUT = timedelta(days=30)  # the "expired after 30 days" in Figma D06

SIGN_IN_REQUIRED = "Your session has ended. Sign in to continue."
NOT_ALLOWED = "You do not have access to this."


def now() -> datetime:
    """The current time in UTC. Tests replace this to move the clock."""
    return datetime.now(UTC)


def _aware(moment: datetime) -> datetime:
    """SQLite hands back naive datetimes; every stored time is UTC."""
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def start_session(db: Session, person_id: int) -> str:
    """Record a new session and return the token for the cookie."""
    token = secrets.token_urlsafe(32)
    started = now()
    db.add(
        AuthSession(
            person_id=person_id,
            token_hash=_hash(token),
            created_at=started,
            last_seen_at=started,
        )
    )
    db.commit()
    return token


def end_session(db: Session, token: str | None) -> None:
    """Revoke the session behind ``token``, if there is a live one."""
    if not token:
        return
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == _hash(token)))
    if session is not None and session.revoked_at is None:
        session.revoked_at = now()
        db.commit()


def live_session(db: Session, token: str | None) -> AuthSession | None:
    """The session behind ``token`` if it is still valid, touched as seen now."""
    if not token:
        return None
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == _hash(token)))
    if session is None or session.revoked_at is not None:
        return None
    current = now()
    if current - _aware(session.last_seen_at) > IDLE_TIMEOUT:
        return None
    if current - _aware(session.created_at) > ABSOLUTE_TIMEOUT:
        return None
    session.last_seen_at = current
    db.commit()
    return session


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=int(ABSOLUTE_TIMEOUT.total_seconds()),
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/", secure=True, httponly=True, samesite="lax")


@dataclass(frozen=True)
class CurrentUser:
    """Who is calling, and the roles the database gives them right now."""

    person: Person
    roles: frozenset[str]


def current_user(request: Request, db: Session = Depends(get_db)) -> CurrentUser:
    """FastAPI dependency: 401 unless the request carries a live session."""
    session = live_session(db, request.cookies.get(COOKIE_NAME))
    person = db.get(Person, session.person_id) if session else None
    if person is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=SIGN_IN_REQUIRED)
    roles = db.scalars(
        select(Membership.role).where(
            Membership.person_id == person.id, Membership.is_active.is_(True)
        )
    )
    return CurrentUser(person=person, roles=frozenset(roles))


def require_role(*allowed: str) -> Callable[..., CurrentUser]:
    """FastAPI dependency factory: 403 unless the caller holds one of ``allowed``.

    Use it as ``Depends(require_role("supervisor", "admin"))``.
    """

    def check(user: CurrentUser = Depends(current_user)) -> CurrentUser:
        if not user.roles & set(allowed):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=NOT_ALLOWED)
        return user

    return check
