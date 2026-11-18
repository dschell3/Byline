"""Where uploaded files live (SCRUM-83).

The browser never sends bytes through the API: it gets a presigned URL and
uploads straight to the backend. ``LocalBackend`` is a directory on this
machine, for development and CI; ``R2Backend`` is Cloudflare R2 through its
S3 API. The upload limits live here so the API can state them before anyone
picks a file.
"""

import os
import tempfile
from pathlib import Path
from typing import Protocol

from config import Settings

# Long enough for a 25 MB upload on a slow connection; short enough that a leaked link soon dies.
URL_TTL_SECONDS = 15 * 60

MAX_UPLOAD_MB = 25
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

# Content type -> the extensions it may carry. Nothing executable, nothing a browser runs inline.
ALLOWED_TYPES: dict[str, tuple[str, ...]] = {
    "application/pdf": (".pdf",),
    "image/png": (".png",),
    "image/jpeg": (".jpg", ".jpeg"),
    "image/gif": (".gif",),
    "image/webp": (".webp",),
    "text/plain": (".txt",),
    "text/markdown": (".md",),
    "text/csv": (".csv",),
    "application/zip": (".zip",),
    "application/msword": (".doc",),
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": (".docx",),
    "application/vnd.ms-excel": (".xls",),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": (".xlsx",),
    "application/vnd.ms-powerpoint": (".ppt",),
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": (".pptx",),
}
ALLOWED_EXTENSIONS = sorted({ext for exts in ALLOWED_TYPES.values() for ext in exts})

FILE_TOO_LARGE = "file_too_large"
FILE_TYPE_NOT_ALLOWED = "file_type_not_allowed"


def check_upload(name: str, content_type: str, size_bytes: int) -> str | None:
    """The error code for a file that must not be uploaded, or None.

    Both the declared type and the extension must match, so a renamed
    executable with a PDF content type is still refused.
    """
    if size_bytes <= 0 or size_bytes > MAX_UPLOAD_BYTES:
        return FILE_TOO_LARGE
    extensions = ALLOWED_TYPES.get(content_type.lower())
    if extensions is None or not name.lower().endswith(extensions):
        return FILE_TYPE_NOT_ALLOWED
    return None


def object_key(organization_id: int, name: str) -> str:
    """A fresh key under the organization's prefix. Only the extension comes from the name."""
    return f"org-{organization_id}/{os.urandom(16).hex()}{Path(name).suffix.lower()}"


class StorageBackend(Protocol):
    def upload_url(self, key: str, content_type: str, size_bytes: int) -> str:
        """A URL the browser PUTs the file to."""

    def download_url(self, key: str, name: str) -> str:
        """A URL that serves the object as an attachment named ``name``."""

    def size_of(self, key: str) -> int | None:
        """The stored object's size, or None when there is no such object."""


# The files router serves these only on the local backend, so they never exist on Render.
LOCAL_URL_PREFIX = "/api/files/local/"


class LocalBackend:
    def __init__(self, directory: str | Path | None = None) -> None:
        self.root = Path(directory) if directory else Path(tempfile.gettempdir()) / "byline-files"
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if self.root.resolve() not in path.parents:
            raise ValueError("key leaves the storage directory")
        return path

    def upload_url(self, key: str, content_type: str, size_bytes: int) -> str:
        return LOCAL_URL_PREFIX + key

    def download_url(self, key: str, name: str) -> str:
        return LOCAL_URL_PREFIX + key

    def size_of(self, key: str) -> int | None:
        path = self._path(key)
        return path.stat().st_size if path.is_file() else None

    def write(self, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def read(self, key: str) -> bytes | None:
        path = self._path(key)
        return path.read_bytes() if path.is_file() else None


class R2Backend:
    """R2 is S3-compatible; the same class works against S3 or MinIO by changing the endpoint."""

    def __init__(
        self, endpoint: str, bucket: str, access_key_id: str, secret_access_key: str
    ) -> None:
        import boto3
        from botocore.config import Config

        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name="auto",  # R2 ignores the region; boto3 insists on one
            config=Config(signature_version="s3v4"),
        )

    def upload_url(self, key: str, content_type: str, size_bytes: int) -> str:
        # Type and length are signed, so the browser must send exactly what was declared.
        return self.client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self.bucket,
                "Key": key,
                "ContentType": content_type,
                "ContentLength": size_bytes,
            },
            ExpiresIn=URL_TTL_SECONDS,
            HttpMethod="PUT",
        )

    def download_url(self, key: str, name: str) -> str:
        disposition = f'attachment; filename="{name.replace(chr(34), "")}"'
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key, "ResponseContentDisposition": disposition},
            ExpiresIn=URL_TTL_SECONDS,
        )

    def size_of(self, key: str) -> int | None:
        from botocore.exceptions import ClientError

        try:
            return int(self.client.head_object(Bucket=self.bucket, Key=key)["ContentLength"])
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
                return None
            raise

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)


def backend_for(settings: Settings) -> StorageBackend:
    if settings.storage_backend == "local":
        return LocalBackend(settings.local_storage_dir)
    values = {
        name: getattr(settings, name)
        for name in ("r2_endpoint", "r2_bucket", "r2_access_key_id", "r2_secret_access_key")
    }
    missing = [name.upper() for name, value in values.items() if not value]
    if missing:
        raise RuntimeError(f"STORAGE_BACKEND=r2 needs {', '.join(missing)}")
    return R2Backend(*values.values())
