"""File storage endpoints (SCRUM-83).

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
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

import files
import sessions
import storage
from config import get_settings
from db import get_db
from models import StoredFile
from sessions import NOT_ALLOWED, CurrentUser, current_user
from storage import LocalBackend, StorageBackend
from submit_work import MAX_TEXT_CHARS

router = APIRouter(prefix="/files", tags=["files"])

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


DbDep = Annotated[Session, Depends(get_db)]
UserDep = Annotated[CurrentUser, Depends(current_user)]
BackendDep = Annotated[StorageBackend, Depends(get_backend)]


class LimitsOut(BaseModel):
    max_upload_mb: int
    allowed_types: list[str]
    allowed_extensions: list[str]
    # The text submission limit too, so the form has one source for every limit it states.
    max_text_chars: int


class UploadIn(BaseModel):
    name: str = Field(min_length=1, max_length=files.MAX_NAME_CHARS)
    content_type: str = Field(min_length=1, max_length=255)
    size_bytes: int = Field(ge=0)


class FileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    content_type: str
    size_bytes: int
    status: str


class UploadOut(FileOut):
    upload_url: str


class DownloadOut(FileOut):
    download_url: str


def _own_upload(db: Session, user: CurrentUser, file_id: int) -> StoredFile:
    """The caller's own upload, or 403 for anyone else and for an id that does not exist."""
    stored = db.get(StoredFile, file_id)
    if stored is None or not files.owned_by(db, user.person, stored):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=NOT_ALLOWED)
    return stored


@router.get("/limits", response_model=LimitsOut)
def limits() -> LimitsOut:
    return LimitsOut(
        max_upload_mb=storage.MAX_UPLOAD_MB,
        allowed_types=sorted(storage.ALLOWED_TYPES),
        allowed_extensions=storage.ALLOWED_EXTENSIONS,
        max_text_chars=MAX_TEXT_CHARS,
    )


@router.post("", response_model=UploadOut, status_code=status.HTTP_201_CREATED)
def begin_upload(
    body: UploadIn, response: Response, user: UserDep, db: DbDep, backend: BackendDep
) -> UploadOut:
    """413 for too large, 415 for a type not on the list, 403 with no active membership."""
    uploader = files.uploading_membership(db, user.person)
    if uploader is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=NOT_ALLOWED)
    try:
        stored = files.begin_upload(db, uploader, body.name, body.content_type, body.size_bytes)
    except files.UploadRefusedError as refused:
        raise HTTPException(REFUSAL_STATUS[refused.code], detail=refused.code) from refused
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    url = backend.upload_url(stored.key, stored.content_type, stored.size_bytes)
    return UploadOut(**FileOut.model_validate(stored).model_dump(), upload_url=url)


@router.post("/{file_id}/complete", response_model=FileOut)
def complete_upload(
    file_id: int, response: Response, user: UserDep, db: DbDep, backend: BackendDep
) -> FileOut:
    """409 until the object is there at the declared size, so the browser uploads again."""
    stored = _own_upload(db, user, file_id)
    if not files.complete_upload(db, backend, stored, sessions.now()):
        raise HTTPException(status.HTTP_409_CONFLICT, detail=UPLOAD_INCOMPLETE)
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    return FileOut.model_validate(stored)


@router.get("/{file_id}", response_model=DownloadOut)
def download(
    file_id: int, response: Response, user: UserDep, db: DbDep, backend: BackendDep
) -> DownloadOut:
    stored = db.get(StoredFile, file_id)
    if stored is None or not files.can_download(db, user.person, stored):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=NOT_ALLOWED)
    if stored.status != "complete":
        raise HTTPException(status.HTTP_409_CONFLICT, detail=UPLOAD_INCOMPLETE)
    response.headers["Cache-Control"] = "no-store"
    url = backend.download_url(stored.key, stored.name)
    return DownloadOut(**FileOut.model_validate(stored).model_dump(), download_url=url)


# --- Local backend only -----------------------------------------------------
# R2 takes the PUT and serves the GET itself. These stand in for it on the
# local backend and answer 404 on any other. The presigned-URL idea holds:
# PUT needs a pending row of the caller's own, GET the same access as /files/{id}.


def _local_file(db: Session, backend: StorageBackend, key: str) -> tuple[LocalBackend, StoredFile]:
    if not isinstance(backend, LocalBackend):
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    stored = db.scalar(select(StoredFile).where(StoredFile.key == key))
    if stored is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=NOT_ALLOWED)
    return backend, stored


@router.put("/local/{key:path}", status_code=status.HTTP_204_NO_CONTENT)
async def local_put(
    key: str, request: Request, user: UserDep, db: DbDep, backend: BackendDep
) -> Response:
    local, stored = _local_file(db, backend, key)
    if not files.owned_by(db, user.person, stored):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=NOT_ALLOWED)
    body = await request.body()
    if len(body) > storage.MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, detail=storage.FILE_TOO_LARGE)
    local.write(key, body)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/local/{key:path}")
def local_get(key: str, user: UserDep, db: DbDep, backend: BackendDep) -> Response:
    local, stored = _local_file(db, backend, key)
    if not files.can_download(db, user.person, stored):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=NOT_ALLOWED)
    data = local.read(key)
    if data is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return Response(
        content=data,
        media_type=stored.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{stored.name.replace(chr(34), "")}"',
            "Cache-Control": "no-store",
        },
    )
