"""Uploaded files: who may store one, who may open one (SCRUM-83).

The uploader may always open their own file. A file on a submission
follows the submission's rule, ``work.can_view``. A profile photo is
visible to anyone active in that organization, since it sits next to the
person's name. Everyone else gets the same answer as for an id that does
not exist.
"""

from datetime import datetime
from pathlib import PurePosixPath

from sqlalchemy import literal, select
from sqlalchemy.orm import Session

import work
from models import Membership, Person, StoredFile, Submission
from storage import StorageBackend, check_upload, object_key

MAX_NAME_CHARS = 255


class UploadRefusedError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def clean_name(name: str) -> str:
    """No path, no control characters; what is shown and sent back as the download filename."""
    base = PurePosixPath(name.replace("\\", "/")).name.strip()
    return "".join(ch for ch in base if ch.isprintable())[:MAX_NAME_CHARS] or "file"


def uploading_membership(db: Session, caller: Person) -> Membership | None:
    """An active member membership first, else any active one: the same pick as the home screen."""
    rows = db.scalars(
        select(Membership)
        .where(Membership.person_id == caller.id, Membership.is_active.is_(True))
        .order_by(Membership.id)
    ).all()
    return next((m for m in rows if m.role == "member"), rows[0] if rows else None)


def begin_upload(
    db: Session, uploader: Membership, name: str, content_type: str, size_bytes: int
) -> StoredFile:
    name = clean_name(name)
    code = check_upload(name, content_type, size_bytes)
    if code is not None:
        raise UploadRefusedError(code)
    stored = StoredFile(
        organization_id=uploader.organization_id,
        uploaded_by_membership_id=uploader.id,
        key=object_key(uploader.organization_id, name),
        name=name,
        content_type=content_type.lower(),
        size_bytes=size_bytes,
        status="pending",
    )
    db.add(stored)
    db.flush()
    return stored


def complete_upload(
    db: Session, backend: StorageBackend, stored: StoredFile, now: datetime
) -> bool:
    """Mark the row complete once the object is there at the declared size; False until then."""
    if stored.status == "complete":
        return True
    if backend.size_of(stored.key) != stored.size_bytes:
        return False
    stored.status = "complete"
    stored.completed_at = now
    db.flush()
    return True


def owned_by(db: Session, caller: Person, stored: StoredFile) -> bool:
    uploader = db.get(Membership, stored.uploaded_by_membership_id)
    return uploader is not None and uploader.person_id == caller.id


def can_download(db: Session, caller: Person, stored: StoredFile) -> bool:
    if owned_by(db, caller, stored):
        return True
    submission = db.scalar(
        select(Submission)
        .where(literal(stored.key) == Submission.file_keys.any_())
        .order_by(Submission.id)
    )
    if submission is not None:
        owner = db.get(Membership, submission.membership_id)
        return owner is not None and work.can_view(db, caller, owner)
    if db.scalar(select(Person.id).where(Person.photo_file_id == stored.id)) is not None:
        same_org = select(Membership.id).where(
            Membership.person_id == caller.id,
            Membership.organization_id == stored.organization_id,
            Membership.is_active.is_(True),
        )
        return db.scalar(same_org) is not None
    return False


def own_photo_candidate(db: Session, caller: Person, file_id: int) -> StoredFile | None:
    """A complete image the caller uploaded: what PATCH /me/profile may set as the photo."""
    stored = db.get(StoredFile, file_id)
    if (
        stored is None
        or stored.status != "complete"
        or not stored.content_type.startswith("image/")
        or not owned_by(db, caller, stored)
    ):
        return None
    return stored
