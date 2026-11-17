"""File storage endpoints (SCRUM-83).

The browser never sends bytes through the API. It asks for an upload URL,
PUTs the file straight to storage, then confirms. Downloads are the same in
reverse: a short-lived URL, after the access check in files.py.

| Endpoint | What |
| --- | --- |
| ``GET /files/limits`` | Size and type limits, so the form states them before a file is picked. |
| ``POST /files`` | Check the limits, write the pending row, return the upload URL. |
| ``POST /files/{id}/complete`` | Confirm the object is there at the declared size. Uploader only. |
| ``GET /files/{id}`` | A short-lived download URL, after the access check in files.py. |
| ``PUT/GET /files/local/{key}`` | The local backend's stand-in for the bucket. Dev and CI only. |
"""

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

import files
import sessions
import storage
from config import get_settings
from db import get_db
from models import Membership, StoredFile
from sessions import NOT_ALLOWED, CurrentUser, current_user
from storage import LocalBackend, StorageBackend

router = APIRouter(prefix="/files", tags=["files"])

# The object is not in storage yet, or not at the declared size: upload again.
UPLOAD_INCOMPLETE = "upload_incomplete"

# Distinct status codes for the two refusals, so the form can say which it was.
REFUSAL_STATUS = {
    storage.FILE_TOO_LARGE: status.HTTP_413_CONTENT_TOO_LARGE,
    storage.FILE_TYPE_NOT_ALLOWED: status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
}


@lru_cache
def get_backend() -> StorageBackend:
    """One backend per process. Tests override this dependency with a LocalBackend."""
    return storage.backend_for(get_settings())


class LimitsOut(BaseModel):
    max_upload_mb: int
    allowed_types: list[str]
    allowed_extensions: list[str]


class UploadIn(BaseModel):
    name: str = Field(min_length=1, max_length=files.MAX_NAME_CHARS)
    content_type: str = Field(min_length=1, max_length=255)
    size_bytes: int = Field(ge=0)


class FileOut(BaseModel):
    id: int
    name: str
    content_type: str
    size_bytes: int
    status: str


class UploadOut(FileOut):
    # Where the browser PUTs the bytes. Short-lived; not stored.
    upload_url: str


class DownloadOut(FileOut):
    # Where the browser GETs the bytes. Short-lived; not stored.
    download_url: str


def _out(stored: StoredFile) -> dict[str, object]:
    return {
        "id": stored.id,
        "name": stored.name,
        "content_type": stored.content_type,
        "size_bytes": stored.size_bytes,
        "status": stored.status,
    }


def _own_pending_or_complete(db: Session, user: CurrentUser, file_id: int) -> StoredFile:
    """The caller's own upload, or 403 for anyone else and for an id that does not exist."""
    stored = db.get(StoredFile, file_id)
    uploader = db.get(Membership, stored.uploaded_by_membership_id) if stored else None
    if stored is None or uploader is None or uploader.person_id != user.person.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=NOT_ALLOWED)
    return stored


@router.get("/limits", response_model=LimitsOut)
def limits() -> LimitsOut:
    """What may be uploaded. No session needed; nothing here is secret."""
    current = storage.limits()
    return LimitsOut(
        max_upload_mb=current.max_upload_mb,
        allowed_types=list(current.allowed_types),
        allowed_extensions=list(current.allowed_extensions),
    )


@router.post("", response_model=UploadOut, status_code=status.HTTP_201_CREATED)
def begin_upload(
    body: UploadIn,
    response: Response,
    user: Annotated[CurrentUser, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
    backend: Annotated[StorageBackend, Depends(get_backend)],
) -> UploadOut:
    """Refuse over-limit or disallowed files before any bytes move; otherwise hand out the URL.

    413 for too large, 415 for a type not on the list. 403 for a person with
    no active membership, since every file belongs to an organization.
    """
    uploader = files.uploading_membership(db, user.person)
    if uploader is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=NOT_ALLOWED)
    try:
        stored = files.begin_upload(db, uploader, body.name, body.content_type, body.size_bytes)
    except files.UploadRefusedError as refused:
        raise HTTPException(REFUSAL_STATUS[refused.code], detail=refused.code) from refused
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    return UploadOut(
        id=stored.id,
        name=stored.name,
        content_type=stored.content_type,
        size_bytes=stored.size_bytes,
        status=stored.status,
        upload_url=backend.upload_url(stored.key, stored.content_type, stored.size_bytes),
    )


@router.post("/{file_id}/complete", response_model=FileOut)
def complete_upload(
    file_id: int,
    response: Response,
    user: Annotated[CurrentUser, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
    backend: Annotated[StorageBackend, Depends(get_backend)],
) -> FileOut:
    """Mark the upload complete once the object is in storage at the declared size.

    409 when it is not there yet or the size differs, so the browser uploads
    again rather than attaching a file that is not really there.
    """
    stored = _own_pending_or_complete(db, user, file_id)
    if not files.complete_upload(db, backend, stored, sessions.now()):
        raise HTTPException(status.HTTP_409_CONFLICT, detail=UPLOAD_INCOMPLETE)
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    return FileOut(**_out(stored))


@router.get("/{file_id}", response_model=DownloadOut)
def download(
    file_id: int,
    response: Response,
    user: Annotated[CurrentUser, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
    backend: Annotated[StorageBackend, Depends(get_backend)],
) -> DownloadOut:
    """A download URL for a file the caller may open; 403 otherwise, and for a missing id."""
    stored = files.visible_file(db, user.person, file_id)
    if stored is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=NOT_ALLOWED)
    if stored.status != "complete":
        raise HTTPException(status.HTTP_409_CONFLICT, detail=UPLOAD_INCOMPLETE)
    response.headers["Cache-Control"] = "no-store"
    return DownloadOut(**_out(stored), download_url=backend.download_url(stored.key, stored.name))


# --- Local backend only -----------------------------------------------------
#
# R2 takes the PUT and serves the GET itself; these two stand in for it when
# STORAGE_BACKEND=local. Any other backend answers 404 so they never exist on
# Render. The presigned-URL idea still holds: PUT needs a pending row of the
# caller's own with this key, GET needs the same access as /files/{id}.


def _local(backend: StorageBackend) -> LocalBackend:
    if not isinstance(backend, LocalBackend):
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return backend


@router.put("/local/{key:path}", status_code=status.HTTP_204_NO_CONTENT)
async def local_put(
    key: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
    backend: Annotated[StorageBackend, Depends(get_backend)],
) -> Response:
    local = _local(backend)
    stored = db.scalar(select(StoredFile).where(StoredFile.key == key))
    uploader = db.get(Membership, stored.uploaded_by_membership_id) if stored else None
    if stored is None or uploader is None or uploader.person_id != user.person.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=NOT_ALLOWED)
    body = await request.body()
    if len(body) > storage.MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, detail=storage.FILE_TOO_LARGE)
    local.write(key, body)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/local/{key:path}")
def local_get(
    key: str,
    user: Annotated[CurrentUser, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
    backend: Annotated[StorageBackend, Depends(get_backend)],
) -> Response:
    local = _local(backend)
    stored = db.scalar(select(StoredFile).where(StoredFile.key == key))
    if stored is None or not files.can_download(db, user.person, stored):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=NOT_ALLOWED)
    data = local.read(key)
    if data is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    safe_name = stored.name.replace('"', "")
    return Response(
        content=data,
        media_type=stored.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "Cache-Control": "no-store",
        },
    )
