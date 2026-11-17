"""SCRUM-83: the /files endpoints on the local backend, against PostgreSQL.

Same shape as test_submit_api.py. The storage backend is a LocalBackend in a
temp directory, swapped in through the router's dependency.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import ratelimit
import storage
from db import as_psycopg_url, get_db
from main import app
from models import Membership, Organization, Person, StoredFile
from routers.files import UPLOAD_INCOMPLETE, get_backend
from security import hash_password
from sessions import NOT_ALLOWED
from storage import LocalBackend

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="needs PostgreSQL at DATABASE_URL",
)

PASSWORD = "correct horse battery staple"
MEMBER = "member.scrum83api@example.com"
OTHER = "other.scrum83api@example.com"
NOBODY = "nobody.scrum83api@example.com"


@pytest.fixture
def db() -> Iterator[Session]:
    engine = create_engine(as_psycopg_url(os.environ["DATABASE_URL"]))
    with engine.connect() as connection:
        outer = connection.begin()
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            session.close()
            outer.rollback()
    engine.dispose()


def person(db: Session, email: str) -> Person:
    row = Person(email=email, full_name=email.split("@")[0], password_hash=hash_password(PASSWORD))
    db.add(row)
    db.flush()
    return row


@pytest.fixture
def member(db: Session) -> Membership:
    org = Organization(name="SCRUM-83 API Org", slug="scrum83-api")
    db.add(org)
    db.flush()
    row = Membership(person_id=person(db, MEMBER).id, organization_id=org.id, role="member")
    other = Membership(person_id=person(db, OTHER).id, organization_id=org.id, role="member")
    db.add_all([row, other])
    db.flush()
    # Signed in, but in no organization.
    person(db, NOBODY)
    return row


@pytest.fixture
def backend(tmp_path: Path) -> LocalBackend:
    return LocalBackend(tmp_path)


@pytest.fixture
def client(db: Session, member: Membership, backend: LocalBackend) -> Iterator[TestClient]:
    def override_db() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_backend] = lambda: backend
    ratelimit.by_account._events.clear()
    ratelimit.by_ip._events.clear()
    try:
        with TestClient(app, base_url="https://testserver") as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def sign_in(client: TestClient, email: str = MEMBER) -> None:
    r = client.post("/auth/sign-in", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text


def begin(client: TestClient, **overrides: object) -> object:
    body = {"name": "notes.pdf", "content_type": "application/pdf", "size_bytes": 1024}
    body.update(overrides)
    return client.post("/files", json=body)


# --- GET /files/limits ------------------------------------------------------


def test_limits_need_no_session(client: TestClient) -> None:
    r = client.get("/files/limits")
    assert r.status_code == 200
    body = r.json()
    assert body["max_upload_mb"] == storage.MAX_UPLOAD_MB
    assert "application/pdf" in body["allowed_types"]
    assert ".pdf" in body["allowed_extensions"]


# --- POST /files ------------------------------------------------------------


def test_begin_upload_writes_a_pending_row_and_returns_the_url(
    client: TestClient, db: Session, member: Membership
) -> None:
    sign_in(client)
    r = begin(client, name="My Notes.pdf")

    assert r.status_code == 201, r.text
    assert r.headers["cache-control"] == "no-store"
    body = r.json()
    assert body["name"] == "My Notes.pdf"
    assert body["content_type"] == "application/pdf"
    assert body["size_bytes"] == 1024
    assert body["status"] == "pending"
    assert body["upload_url"].startswith(
        storage.LOCAL_URL_PREFIX + f"org-{member.organization_id}/"
    )

    stored = db.get(StoredFile, body["id"])
    assert stored is not None
    assert stored.uploaded_by_membership_id == member.id
    assert stored.status == "pending"
    assert body["upload_url"] == storage.LOCAL_URL_PREFIX + stored.key


def test_too_large_is_413_before_anything_is_stored(client: TestClient, db: Session) -> None:
    sign_in(client)
    r = begin(client, size_bytes=storage.MAX_UPLOAD_BYTES + 1)
    assert r.status_code == 413
    assert r.json()["detail"] == storage.FILE_TOO_LARGE
    assert db.query(StoredFile).count() == 0


@pytest.mark.parametrize(
    ("name", "content_type"),
    [
        ("run.exe", "application/x-msdownload"),
        ("page.html", "text/html"),
        ("run.exe", "application/pdf"),
    ],
)
def test_disallowed_type_is_415(
    client: TestClient, db: Session, name: str, content_type: str
) -> None:
    sign_in(client)
    r = begin(client, name=name, content_type=content_type)
    assert r.status_code == 415
    assert r.json()["detail"] == storage.FILE_TYPE_NOT_ALLOWED
    assert db.query(StoredFile).count() == 0


def test_malformed_body_is_422(client: TestClient) -> None:
    sign_in(client)
    assert begin(client, name="").status_code == 422
    assert begin(client, size_bytes=-1).status_code == 422
    assert client.post("/files", json={}).status_code == 422


def test_no_membership_is_403(client: TestClient, db: Session) -> None:
    sign_in(client, NOBODY)
    r = begin(client)
    assert r.status_code == 403
    assert r.json()["detail"] == NOT_ALLOWED
    assert db.query(StoredFile).count() == 0


def test_signed_out_is_401(client: TestClient) -> None:
    assert begin(client).status_code == 401


# --- the whole round trip on the local backend -------------------------------


def upload_bytes(
    client: TestClient, data: bytes = b"%PDF-1.4 test", name: str = "notes.pdf"
) -> dict:
    r = begin(client, name=name, size_bytes=len(data))
    assert r.status_code == 201, r.text
    body = r.json()
    # The upload URL is /api/...; the API itself is mounted at the root.
    put = client.put(body["upload_url"].removeprefix("/api"), content=data)
    assert put.status_code == 204, put.text
    done = client.post(f"/files/{body['id']}/complete")
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "complete"
    return body


def test_upload_complete_and_download(
    client: TestClient, db: Session, backend: LocalBackend
) -> None:
    sign_in(client)
    data = b"%PDF-1.4 hello"
    body = upload_bytes(client, data)

    stored = db.get(StoredFile, body["id"])
    assert stored is not None
    assert stored.status == "complete"
    assert stored.completed_at is not None
    assert backend.read(stored.key) == data

    r = client.get(f"/files/{body['id']}")
    assert r.status_code == 200, r.text
    assert r.headers["cache-control"] == "no-store"
    assert r.json()["download_url"] == storage.LOCAL_URL_PREFIX + stored.key

    served = client.get(r.json()["download_url"].removeprefix("/api"))
    assert served.status_code == 200
    assert served.content == data
    assert served.headers["content-type"].startswith("application/pdf")
    assert served.headers["content-disposition"] == 'attachment; filename="notes.pdf"'


def test_complete_is_409_until_the_object_is_there_at_the_declared_size(
    client: TestClient, backend: LocalBackend, db: Session
) -> None:
    sign_in(client)
    r = begin(client, size_bytes=10)
    file_id = r.json()["id"]

    done = client.post(f"/files/{file_id}/complete")
    assert done.status_code == 409
    assert done.json()["detail"] == UPLOAD_INCOMPLETE

    put = client.put(r.json()["upload_url"].removeprefix("/api"), content=b"short")
    assert put.status_code == 204
    assert client.post(f"/files/{file_id}/complete").status_code == 409

    # Still pending, so no download URL either.
    assert client.get(f"/files/{file_id}").status_code == 409

    client.put(r.json()["upload_url"].removeprefix("/api"), content=b"0123456789")
    assert client.post(f"/files/{file_id}/complete").status_code == 200
    assert client.get(f"/files/{file_id}").status_code == 200


def test_only_the_uploader_may_put_or_complete(client: TestClient) -> None:
    sign_in(client)
    r = begin(client, size_bytes=4)
    file_id, upload_url = r.json()["id"], r.json()["upload_url"].removeprefix("/api")

    sign_in(client, OTHER)
    assert client.put(upload_url, content=b"evil").status_code == 403
    assert client.post(f"/files/{file_id}/complete").status_code == 403
    assert client.post("/files/999999/complete").status_code == 403


def test_a_stranger_and_a_missing_id_get_the_same_403(client: TestClient) -> None:
    sign_in(client)
    body = upload_bytes(client)
    download_url = client.get(f"/files/{body['id']}").json()["download_url"]

    sign_in(client, OTHER)
    stranger = client.get(f"/files/{body['id']}")
    missing = client.get("/files/999999")
    assert stranger.status_code == missing.status_code == 403
    assert stranger.json() == missing.json() == {"detail": NOT_ALLOWED}
    assert client.get(download_url.removeprefix("/api")).status_code == 403


def test_local_put_refuses_more_than_the_limit(client: TestClient) -> None:
    sign_in(client)
    r = begin(client, size_bytes=storage.MAX_UPLOAD_BYTES)
    too_big = b"x" * (storage.MAX_UPLOAD_BYTES + 1)
    put = client.put(r.json()["upload_url"].removeprefix("/api"), content=too_big)
    assert put.status_code == 413


def test_local_routes_do_not_exist_on_other_backends(client: TestClient) -> None:
    class NotLocal:
        def upload_url(self, key: str, content_type: str, size_bytes: int) -> str:
            return "https://bucket.example/" + key

        def download_url(self, key: str, name: str) -> str:
            return "https://bucket.example/" + key

        def size_of(self, key: str) -> int | None:
            return None

        def delete(self, key: str) -> None:
            pass

    app.dependency_overrides[get_backend] = lambda: NotLocal()
    sign_in(client)
    assert client.put("/files/local/org-1/x.pdf", content=b"x").status_code == 404
    assert client.get("/files/local/org-1/x.pdf").status_code == 404
