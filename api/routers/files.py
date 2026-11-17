"""File storage endpoints (SCRUM-83).

The browser never sends bytes through the API. It asks for an upload URL,
PUTs the file straight to storage, then confirms. Downloads are the same in
reverse: a short-lived URL, after the access check in files.py.

| Endpoint | What |
| --- | --- |
| ``GET /files/limits`` | Size and type limits, so the form states them before a file is picked. |
| ``POST /files`` | Check the limits, write the pending row, return the upload URL. |
"""

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import files
import storage
from config import get_settings
from db import get_db
from sessions import NOT_ALLOWED, CurrentUser, current_user
from storage import StorageBackend

router = APIRouter(prefix="/files", tags=["files"])

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
