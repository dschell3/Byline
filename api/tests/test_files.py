"""SCRUM-83: the upload and download rules in files.py, against PostgreSQL.

Same shape as test_submit_api.py: each test runs in a transaction that is
rolled back afterward, and the file skips without DATABASE_URL.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import files
import sessions
import storage
from db import as_psycopg_url
from models import Membership, Organization, Person, StoredFile, Submission, Team
from security import hash_password
from storage import LocalBackend

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="needs PostgreSQL at DATABASE_URL",
)


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


def membership(db: Session, org: Organization, email: str, role: str) -> Membership:
    person = Person(email=email, full_name=email.split("@")[0], password_hash=hash_password("x"))
    db.add(person)
    db.flush()
    row = Membership(person_id=person.id, organization_id=org.id, role=role)
    db.add(row)
    db.flush()
    return row


@pytest.fixture
def org(db: Session) -> Organization:
    row = Organization(name="SCRUM-83 Test Org", slug="scrum83-test")
    db.add(row)
    db.flush()
    db.add(Team(organization_id=row.id, name="Design"))
    db.flush()
    return row


@pytest.fixture
def member(db: Session, org: Organization) -> Membership:
    return membership(db, org, "member.scrum83@example.com", "member")


@pytest.fixture
def other(db: Session, org: Organization) -> Membership:
    return membership(db, org, "other.scrum83@example.com", "member")


@pytest.fixture
def supervisor(db: Session, org: Organization) -> Membership:
    return membership(db, org, "supervisor.scrum83@example.com", "supervisor")


@pytest.fixture
def outsider(db: Session) -> Membership:
    outside = Organization(name="SCRUM-83 Outside Org", slug="scrum83-outside")
    db.add(outside)
    db.flush()
    return membership(db, outside, "outsider.scrum83@example.com", "member")


def person_of(db: Session, row: Membership) -> Person:
    person = db.get(Person, row.person_id)
    assert person is not None
    return person


def upload(db: Session, who: Membership, name: str = "notes.pdf") -> StoredFile:
    return files.begin_upload(db, who, name, "application/pdf", 1024)


# --- begin_upload -----------------------------------------------------------


def test_begin_upload_writes_a_pending_row_under_the_org(db: Session, member: Membership) -> None:
    stored = upload(db, member, "My Notes.PDF")
    assert stored.status == "pending"
    assert stored.organization_id == member.organization_id
    assert stored.uploaded_by_membership_id == member.id
    assert stored.key.startswith(f"org-{member.organization_id}/")
    assert stored.name == "My Notes.PDF"
    assert stored.size_bytes == 1024
    assert stored.completed_at is None


@pytest.mark.parametrize(
    ("name", "content_type", "size", "code"),
    [
        ("big.pdf", "application/pdf", storage.MAX_UPLOAD_BYTES + 1, storage.FILE_TOO_LARGE),
        ("run.exe", "application/x-msdownload", 10, storage.FILE_TYPE_NOT_ALLOWED),
        ("run.exe", "application/pdf", 10, storage.FILE_TYPE_NOT_ALLOWED),
    ],
)
def test_begin_upload_refuses_with_a_code(
    db: Session, member: Membership, name: str, content_type: str, size: int, code: str
) -> None:
    with pytest.raises(files.UploadRefusedError) as refused:
        files.begin_upload(db, member, name, content_type, size)
    assert refused.value.code == code
    assert db.query(StoredFile).count() == 0


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


# --- complete_upload --------------------------------------------------------


def test_complete_marks_the_row_once_the_object_matches(
    db: Session, member: Membership, tmp_path: Path
) -> None:
    backend = LocalBackend(tmp_path)
    stored = upload(db, member)
    now = sessions.now()

    assert files.complete_upload(db, backend, stored, now) is False  # nothing stored yet
    assert stored.status == "pending"

    backend.write(stored.key, b"x" * 999)
    assert files.complete_upload(db, backend, stored, now) is False  # wrong size
    assert stored.status == "pending"

    backend.write(stored.key, b"x" * 1024)
    assert files.complete_upload(db, backend, stored, now) is True
    assert stored.status == "complete"
    assert stored.completed_at == now

    # Completing twice is fine and does not re-stamp.
    assert files.complete_upload(db, backend, stored, sessions.now()) is True
    assert stored.completed_at == now


# --- can_download -----------------------------------------------------------


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
    from models import Assignment

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


def test_visible_file_hides_strangers_and_missing_ids_alike(
    db: Session, member: Membership, other: Membership
) -> None:
    stored = upload(db, member)
    assert files.visible_file(db, person_of(db, member), stored.id) is stored
    assert files.visible_file(db, person_of(db, other), stored.id) is None
    assert files.visible_file(db, person_of(db, other), stored.id + 100_000) is None
