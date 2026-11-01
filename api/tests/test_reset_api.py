"""SCRUM-10: forgot-password and reset-password HTTP tests."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import reset_mail
from db import Base, get_db
from main import app
from models import AuthSession, PasswordResetToken, Person
from routers.reset_password import reset_by_email, reset_by_ip
from security import hash_password, verify_password

EMAIL = "member@example.com"
OLD_PASSWORD = "original-password-123"
NEW_PASSWORD = "replacement-password-456"


@pytest.fixture
def factory() -> sessionmaker[Session]:
    """Use a fresh SQLite database without touching PostgreSQL."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            Person.__table__,
            AuthSession.__table__,
            PasswordResetToken.__table__,
        ],
    )
    make_session = sessionmaker(bind=engine)

    with make_session() as db:
        db.add(
            Person(
                id=1,
                email=EMAIL,
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


@pytest.fixture
def client(factory: sessionmaker[Session]) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    reset_by_email._events.clear()
    reset_by_ip._events.clear()
    try:
        with TestClient(app, base_url="https://testserver") as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def mail_outbox(
    monkeypatch: pytest.MonkeyPatch,
) -> list[tuple[str, str]]:
    """Capture email requests without contacting a real email provider."""
    sent: list[tuple[str, str]] = []

    def fake_send(recipient: str, token: str) -> None:
        sent.append((recipient, token))

    monkeypatch.setattr(reset_mail, "send_reset_email", fake_send)
    return sent


def request_link(client: TestClient, email: str) -> object:
    return client.post("/auth/forgot-password", json={"email": email})


def test_known_and_unknown_email_get_same_confirmation(
    client: TestClient,
    mail_outbox: list[tuple[str, str]],
) -> None:
    known = request_link(client, EMAIL)
    unknown = request_link(client, "nobody@example.com")

    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    assert known.headers["cache-control"] == "no-store"
    assert unknown.headers["cache-control"] == "no-store"

    # Only the existing account triggers an email request.
    assert len(mail_outbox) == 1
    assert mail_outbox[0][0] == EMAIL
    assert mail_outbox[0][1] not in known.text


def test_email_lookup_is_case_insensitive(
    client: TestClient,
    mail_outbox: list[tuple[str, str]],
) -> None:
    response = request_link(client, "MEMBER@EXAMPLE.COM")
    assert response.status_code == 200
    assert len(mail_outbox) == 1
    assert mail_outbox[0][0] == EMAIL


def test_valid_and_invalid_link_states(
    client: TestClient,
    mail_outbox: list[tuple[str, str]],
) -> None:
    request_link(client, EMAIL)
    token = mail_outbox[0][1]

    valid = client.get(f"/auth/reset-password/{token}")
    invalid = client.get("/auth/reset-password/not-a-real-token")

    assert valid.status_code == 200
    assert valid.json() == {"state": "valid"}
    assert invalid.status_code == 200
    assert invalid.json() == {"state": "invalid"}


def test_reset_changes_password_and_link_becomes_used(
    client: TestClient,
    mail_outbox: list[tuple[str, str]],
    factory: sessionmaker[Session],
) -> None:
    request_link(client, EMAIL)
    token = mail_outbox[0][1]
    url = f"/auth/reset-password/{token}"

    result = client.post(
        url,
        json={
            "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD,
        },
    )

    assert result.status_code == 200
    assert result.json() == {"state": "success"}

    with factory() as db:
        person = db.get(Person, 1)
        session = db.get(AuthSession, 1)
        assert verify_password(NEW_PASSWORD, person.password_hash)
        assert not verify_password(OLD_PASSWORD, person.password_hash)
        assert session.revoked_at is not None

    assert client.get(url).json() == {"state": "used"}

    again = client.post(
        url,
        json={
            "new_password": "another-password-789",
            "confirm_password": "another-password-789",
        },
    )
    assert again.status_code == 410
    assert again.json()["detail"]["state"] == "used"


def test_expired_link_has_distinct_error(
    client: TestClient,
    mail_outbox: list[tuple[str, str]],
    factory: sessionmaker[Session],
) -> None:
    request_link(client, EMAIL)
    token = mail_outbox[0][1]
    url = f"/auth/reset-password/{token}"

    with factory() as db:
        db.execute(
            update(PasswordResetToken).values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )
        db.commit()

    assert client.get(url).json() == {"state": "expired"}

    result = client.post(
        url,
        json={
            "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD,
        },
    )
    assert result.status_code == 410
    assert result.json()["detail"]["state"] == "expired"

    with factory() as db:
        person = db.get(Person, 1)
        assert verify_password(OLD_PASSWORD, person.password_hash)


def test_mismatched_passwords_are_rejected(
    client: TestClient,
    mail_outbox: list[tuple[str, str]],
) -> None:
    request_link(client, EMAIL)
    token = mail_outbox[0][1]

    result = client.post(
        f"/auth/reset-password/{token}",
        json={
            "new_password": NEW_PASSWORD,
            "confirm_password": "different-password-123",
        },
    )
    assert result.status_code == 422
    assert client.get(f"/auth/reset-password/{token}").json()["state"] == "valid"


def test_short_password_is_rejected(
    client: TestClient,
    mail_outbox: list[tuple[str, str]],
) -> None:
    request_link(client, EMAIL)
    token = mail_outbox[0][1]

    result = client.post(
        f"/auth/reset-password/{token}",
        json={
            "new_password": "short",
            "confirm_password": "short",
        },
    )
    assert result.status_code == 422


def test_unknown_reset_token_cannot_change_password(
    client: TestClient,
    factory: sessionmaker[Session],
) -> None:
    result = client.post(
        "/auth/reset-password/not-a-real-token",
        json={
            "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD,
        },
    )

    assert result.status_code == 404
    assert result.json()["detail"]["state"] == "invalid"

    with factory() as db:
        person = db.scalar(select(Person).where(Person.email == EMAIL))
        assert verify_password(OLD_PASSWORD, person.password_hash)


def test_repeated_requests_are_limited_without_revealing_account(
    client: TestClient,
    mail_outbox: list[tuple[str, str]],
) -> None:
    """Only three emails are queued, but all requests look identical."""
    responses = [request_link(client, EMAIL) for _ in range(5)]

    assert all(response.status_code == 200 for response in responses)
    assert all(response.json() == responses[0].json() for response in responses)
    assert len(mail_outbox) == 3

    unknown = request_link(client, "unknown@example.com")
    assert unknown.status_code == 200
    assert unknown.json() == responses[0].json()
    assert len(mail_outbox) == 3


def test_ip_limit_blocks_additional_reset_emails(
    client: TestClient,
    mail_outbox: list[tuple[str, str]],
) -> None:
    """Twenty requests exhaust the IP allowance, including unknown emails."""
    for i in range(20):
        response = request_link(client, f"unknown{i}@example.com")
        assert response.status_code == 200

    blocked = request_link(client, EMAIL)

    assert blocked.status_code == 200
    assert blocked.json() == response.json()
    assert mail_outbox == []
