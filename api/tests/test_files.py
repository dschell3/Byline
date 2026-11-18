"""SCRUM-83: the file rules and the /files endpoints, against PostgreSQL on the local backend.

Same shape as test_submit_api.py: each test runs in a transaction that is
rolled back afterward, and the file skips without DATABASE_URL.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import files
import ratelimit
import sessions
import storage
from db import as_psycopg_url, get_db
from main import app
from models import Assignment, Membership, Organization, Person, StoredFile, Submission
from routers.files import UPLOAD_INCOMPLETE, get_backend
from security import hash_password
from sessions import NOT_ALLOWED
from storage import LocalBackend

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="needs PostgreSQL at DATABASE_URL",
)

PASSWORD = "correct horse battery staple"
MEMBER = "member.scrum83@example.com"
OTHER = "other.scrum83@example.com"
SUPERVISOR = "supervisor.scrum83@example.com"
OUTSIDER = "outsider.scrum83@example.com"
NOBODY = "nobody.scrum83@example.com"


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


def membership(db: Session, org: Organization, email: str, role: str) -> Membership:
    row = Membership(person_id=person(db, email).id, organization_id=org.id, role=role)
    db.add(row)
    db.flush()
    return row


@pytest.fixture
def org(db: Session) -> Organization:
    row = Organization(name="SCRUM-83 Test Org", slug="scrum83-test")
    db.add(row)
    db.flush()
    return row


@pytest.fixture
def member(db: Session, org: Organization) -> Membership:
    return membership(db, org, MEMBER, "member")


@pytest.fixture
def other(db: Session, org: Organization) -> Membership:
    return membership(db, org, OTHER, "member")


@pytest.fixture
def supervisor(db: Session, org: Organization) -> Membership:
    return membership(db, org, SUPERVISOR, "supervisor")


@pytest.fixture
def outsider(db: Session) -> Membership:
    outside = Organization(name="SCRUM-83 Outside Org", slug="scrum83-outside")
    db.add(outside)
    db.flush()
    return membership(db, outside, OUTSIDER, "member")


@pytest.fixture
def backend(tmp_path: Path) -> LocalBackend:
    return LocalBackend(tmp_path)


@pytest.fixture
def client(
    db: Session, member: Membership, other: Membership, backend: LocalBackend
) -> Iterator[TestClient]:
    person(db, NOBODY)  # signed in, but in no organization

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


def person_of(db: Session, row: Membership) -> Person:
    found = db.get(Person, row.person_id)
    assert found is not None
    return found


def upload(db: Session, who: Membership, name: str = "notes.pdf") -> StoredFile:
    return files.begin_upload(db, who, name, "application/pdf", 1024)


def sign_in(client: TestClient, email: str = MEMBER) -> None:
    r = client.post("/auth/sign-in", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text


def begin(client: TestClient, **overrides: object) -> Response:
    body: dict[str, object] = {
        "name": "notes.pdf",
        "content_type": "application/pdf",
        "size_bytes": 1024,
    }
    body.update(overrides)
    return client.post("/files", json=body)


def api_path(url: str) -> str:
    # Upload and download URLs are /api/...; the API itself is mounted at the root.
    return url.removeprefix("/api")


def upload_bytes(
    client: TestClient, data: bytes = b"%PDF-1.4 test", name: str = "notes.pdf"
) -> dict:
    r = begin(client, name=name, size_bytes=len(data))
    assert r.status_code == 201, r.text
    body = r.json()
    assert client.put(api_path(body["upload_url"]), content=data).status_code == 204
    done = client.post(f"/files/{body['id']}/complete")
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "complete"
    return body


# --- files.py rules ---------------------------------------------------------


def test_begin_upload_writes_a_pending_row_under_the_org(db: Session, member: Membership) -> None:
    stored = upload(db, member, "My Notes.PDF")
    assert stored.status == "pending"
    assert stored.organization_id == member.organization_id
    assert stored.uploaded_by_membership_id == member.id
    assert stored.key.startswith(f"org-{member.organization_id}/")
    assert stored.name == "My Notes.PDF"
    assert stored.completed_at is None


@pytest.mark.parametrize(
    ("raw", "cleaned"),
    [
        ("report.pdf", "report.pdf"),
        ("  report.pdf  ", "report.pdf"),
        ("../../etc/passwd.pdf", "passwd.pdf"),
        ("C:\\Users\\me\\report.pdf", "report.pdf"),
        ("re\x00port.pdf", "report.pdf"),
        ("", "file"),
    ],
)
def test_clean_name(raw: str, cleaned: str) -> None:
    assert files.clean_name(raw) == cleaned


def test_complete_marks_the_row_once_the_object_matches(
    db: Session, member: Membership, backend: LocalBackend
) -> None:
    stored = upload(db, member)
    now = sessions.now()

    assert files.complete_upload(db, backend, stored, now) is False  # nothing stored yet
    backend.write(stored.key, b"x" * 999)
    assert files.complete_upload(db, backend, stored, now) is False  # wrong size
    assert stored.status == "pending"

    backend.write(stored.key, b"x" * 1024)
    assert files.complete_upload(db, backend, stored, now) is True
    assert stored.status == "complete"
    assert stored.completed_at == now
    assert files.complete_upload(db, backend, stored, sessions.now()) is True
    assert stored.completed_at == now  # not re-stamped


def test_uploader_may_always_open_their_own_file(
    db: Session, member: Membership, other: Membership, supervisor: Membership
) -> None:
    stored = upload(db, member)
    assert files.can_download(db, person_of(db, member), stored) is True
    # Not attached to anything yet, so nobody else may, not even the supervisor.
    assert files.can_download(db, person_of(db, other), stored) is False
    assert files.can_download(db, person_of(db, supervisor), stored) is False


def test_a_submission_file_follows_the_submission_rule(
    db: Session,
    org: Organization,
    member: Membership,
    other: Membership,
    supervisor: Membership,
    outsider: Membership,
) -> None:
    assignment = Assignment(
        organization_id=org.id,
        created_by_membership_id=supervisor.id,
        recipient_membership_ids=[member.id],
        title="SCRUM-83 Test Assignment",
        points_value=10,
        late_policy="accepted_full_points",
    )
    db.add(assignment)
    db.flush()
    stored = upload(db, member)
    db.add(
        Submission(
            assignment_id=assignment.id,
            membership_id=member.id,
            version=1,
            file_keys=[stored.key],
            submission_kind="file",
            status="submitted",
        )
    )
    db.flush()

    assert files.can_download(db, person_of(db, member), stored) is True
    assert files.can_download(db, person_of(db, supervisor), stored) is True
    assert files.can_download(db, person_of(db, other), stored) is False
    assert files.can_download(db, person_of(db, outsider), stored) is False


def test_a_profile_photo_is_visible_inside_the_organization(
    db: Session, member: Membership, other: Membership, outsider: Membership
) -> None:
    stored = files.begin_upload(db, member, "me.png", "image/png", 10)
    person_of(db, member).photo_file_id = stored.id
    db.flush()
    assert files.can_download(db, person_of(db, other), stored) is True
    assert files.can_download(db, person_of(db, outsider), stored) is False


def test_own_photo_candidate_is_a_complete_image_of_your_own(
    db: Session, member: Membership, other: Membership, backend: LocalBackend
) -> None:
    me = person_of(db, member)
    pending = files.begin_upload(db, member, "a.png", "image/png", 1)
    assert files.own_photo_candidate(db, me, pending.id) is None
    backend.write(pending.key, b"x")
    files.complete_upload(db, backend, pending, sessions.now())
    assert files.own_photo_candidate(db, me, pending.id) is pending

    pdf = files.begin_upload(db, member, "a.pdf", "application/pdf", 1)
    pdf.status = "complete"
    theirs = files.begin_upload(db, other, "b.png", "image/png", 1)
    theirs.status = "complete"
    db.flush()
    assert files.own_photo_candidate(db, me, pdf.id) is None
    assert files.own_photo_candidate(db, me, theirs.id) is None
    assert files.own_photo_candidate(db, me, theirs.id + 100_000) is None


# --- GET /files/limits and POST /files --------------------------------------


def test_limits_need_no_session(client: TestClient) -> None:
    r = client.get("/files/limits")
    assert r.status_code == 200
    body = r.json()
    assert body["max_upload_mb"] == storage.MAX_UPLOAD_MB
    assert "application/pdf" in body["allowed_types"]
    assert ".pdf" in body["allowed_extensions"]
    assert body["max_text_chars"] == 20_000


def test_begin_upload_returns_the_pending_row_and_the_url(
    client: TestClient, db: Session, member: Membership
) -> None:
    sign_in(client)
    r = begin(client, name="My Notes.pdf")
    assert r.status_code == 201, r.text
    assert r.headers["cache-control"] == "no-store"
    body = r.json()
    assert body["name"] == "My Notes.pdf"
    assert body["size_bytes"] == 1024
    assert body["status"] == "pending"
    stored = db.get(StoredFile, body["id"])
    assert stored is not None and stored.uploaded_by_membership_id == member.id
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


def test_no_membership_is_403_and_signed_out_is_401(client: TestClient) -> None:
    assert begin(client).status_code == 401
    sign_in(client, NOBODY)
    r = begin(client)
    assert r.status_code == 403
    assert r.json()["detail"] == NOT_ALLOWED


# --- the whole round trip on the local backend -------------------------------


def test_upload_complete_and_download(
    client: TestClient, db: Session, backend: LocalBackend
) -> None:
    sign_in(client)
    data = b"%PDF-1.4 hello"
    body = upload_bytes(client, data)

    stored = db.get(StoredFile, body["id"])
    assert stored is not None and stored.status == "complete"
    assert backend.read(stored.key) == data

    r = client.get(f"/files/{body['id']}")
    assert r.status_code == 200, r.text
    assert r.headers["cache-control"] == "no-store"
    assert r.json()["download_url"] == storage.LOCAL_URL_PREFIX + stored.key

    served = client.get(api_path(r.json()["download_url"]))
    assert served.status_code == 200
    assert served.content == data
    assert served.headers["content-type"].startswith("application/pdf")
    assert served.headers["content-disposition"] == 'attachment; filename="notes.pdf"'


def test_complete_is_409_until_the_object_is_there_at_the_declared_size(client: TestClient) -> None:
    sign_in(client)
    r = begin(client, size_bytes=10)
    file_id, url = r.json()["id"], api_path(r.json()["upload_url"])

    done = client.post(f"/files/{file_id}/complete")
    assert done.status_code == 409
    assert done.json()["detail"] == UPLOAD_INCOMPLETE

    assert client.put(url, content=b"short").status_code == 204
    assert client.post(f"/files/{file_id}/complete").status_code == 409
    assert client.get(f"/files/{file_id}").status_code == 409  # still pending

    client.put(url, content=b"0123456789")
    assert client.post(f"/files/{file_id}/complete").status_code == 200
    assert client.get(f"/files/{file_id}").status_code == 200


def test_only_the_uploader_may_put_or_complete(client: TestClient) -> None:
    sign_in(client)
    r = begin(client, size_bytes=4)
    file_id, url = r.json()["id"], api_path(r.json()["upload_url"])

    sign_in(client, OTHER)
    assert client.put(url, content=b"evil").status_code == 403
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
    assert client.get(api_path(download_url)).status_code == 403


def test_local_put_refuses_more_than_the_limit(client: TestClient) -> None:
    sign_in(client)
    r = begin(client, size_bytes=storage.MAX_UPLOAD_BYTES)
    too_big = b"x" * (storage.MAX_UPLOAD_BYTES + 1)
    assert client.put(api_path(r.json()["upload_url"]), content=too_big).status_code == 413


def test_local_routes_do_not_exist_on_other_backends(client: TestClient) -> None:
    class NotLocal:
        def upload_url(self, key: str, content_type: str, size_bytes: int) -> str:
            return "https://bucket.example/" + key

        def download_url(self, key: str, name: str) -> str:
            return "https://bucket.example/" + key

        def size_of(self, key: str) -> int | None:
            return None

    app.dependency_overrides[get_backend] = lambda: NotLocal()
    sign_in(client)
    assert client.put("/files/local/org-1/x.pdf", content=b"x").status_code == 404
    assert client.get("/files/local/org-1/x.pdf").status_code == 404
