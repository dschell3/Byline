"""Uploaded files: who may store one, who may open one (SCRUM-83).

The rules, in one place so the router stays thin:

- Any active member, supervisor or admin may upload, within the limits in
  storage.py. The row is ``pending`` until the bucket confirms the object.
- The uploader may always open their own file. A file attached to a
  submission (its key is in ``submission.file_keys``) follows the
  submission's rule, ``work.can_view``: the member who made it, or a
  supervisor or admin in the same organization. A profile photo
  (``person.photo_file_id``) is visible to anyone active in that person's
  organization, since it sits next to their name on every screen.
- Anyone else gets the same answer as for an id that does not exist, so
  ids cannot be probed.
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
    """The file must not be uploaded. ``code`` is one of storage's error codes."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def clean_name(name: str) -> str:
    """The filename as it will be shown and sent back: no path, no control characters."""
    base = PurePosixPath(name.replace("\\", "/")).name.strip()
    base = "".join(ch for ch in base if ch.isprintable())
    return base[:MAX_NAME_CHARS] or "file"


def uploading_membership(db: Session, caller: Person) -> Membership | None:
    """The membership an upload is filed under: an active member one, else any active one.

    Same choice as the home screen (routers/me.py), so a person in two
    organizations uploads into the one where they are an intern.
    """
    rows = db.scalars(
        select(Membership)
        .where(Membership.person_id == caller.id, Membership.is_active.is_(True))
        .order_by(Membership.id)
    ).all()
    return next((m for m in rows if m.role == "member"), rows[0] if rows else None)


def begin_upload(
    db: Session, uploader: Membership, name: str, content_type: str, size_bytes: int
) -> StoredFile:
    """Check the limits and write the pending row. The caller gets the upload URL from storage."""
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
    """Mark the row complete once the object is in the bucket at the declared size.

    False when the object is missing or a different size: the row stays
    pending and the browser is told to upload again.
    """
    if stored.status == "complete":
        return True
    actual = backend.size_of(stored.key)
    if actual is None or actual != stored.size_bytes:
        return False
    stored.status = "complete"
    stored.completed_at = now
    db.flush()
    return True


def submission_holding(db: Session, stored: StoredFile) -> Submission | None:
    """The submission this file is attached to, if any."""
    return db.scalar(
        select(Submission)
        .where(literal(stored.key) == Submission.file_keys.any_())
        .order_by(Submission.id)
    )


def _active_membership(db: Session, caller: Person, organization_id: int) -> Membership | None:
    return db.scalar(
        select(Membership).where(
            Membership.person_id == caller.id,
            Membership.organization_id == organization_id,
            Membership.is_active.is_(True),
        )
    )


def can_download(db: Session, caller: Person, stored: StoredFile) -> bool:
    """Whether ``caller`` may have a download URL for this file. See the module docstring."""
    uploader = db.get(Membership, stored.uploaded_by_membership_id)
    if uploader is not None and uploader.person_id == caller.id:
        return True

    submission = submission_holding(db, stored)
    if submission is not None:
        owner = db.get(Membership, submission.membership_id)
        return owner is not None and work.can_view(db, caller, owner)

    is_photo = db.scalar(select(Person.id).where(Person.photo_file_id == stored.id)) is not None
    if is_photo:
        return _active_membership(db, caller, stored.organization_id) is not None

    return False


def own_photo_candidate(db: Session, caller: Person, file_id: int) -> StoredFile | None:
    """A complete image the caller uploaded, or None: what PATCH /me/profile may set."""
    stored = db.get(StoredFile, file_id)
    if stored is None or stored.status != "complete":
        return None
    if not stored.content_type.startswith("image/"):
        return None
    uploader = db.get(Membership, stored.uploaded_by_membership_id)
    if uploader is None or uploader.person_id != caller.id:
        return None
    return stored


def visible_file(db: Session, caller: Person, file_id: int) -> StoredFile | None:
    """The file, or None for a stranger and for an id that does not exist alike."""
    stored = db.get(StoredFile, file_id)
    if stored is None or not can_download(db, caller, stored):
        return None
    return stored
