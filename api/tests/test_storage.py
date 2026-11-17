"""SCRUM-83: the storage interface on the local backend, and the upload limits. No database."""

from pathlib import Path

import pytest

import storage
from config import Settings
from storage import LocalBackend


@pytest.mark.parametrize(
    ("name", "content_type", "size", "expected"),
    [
        ("notes.pdf", "application/pdf", 1024, None),
        ("photo.JPG", "image/jpeg", 1024, None),
        (
            "deck.pptx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            5,
            None,
        ),
        ("big.pdf", "application/pdf", storage.MAX_UPLOAD_BYTES + 1, storage.FILE_TOO_LARGE),
        ("empty.pdf", "application/pdf", 0, storage.FILE_TOO_LARGE),
        ("run.exe", "application/octet-stream", 10, storage.FILE_TYPE_NOT_ALLOWED),
        ("page.html", "text/html", 10, storage.FILE_TYPE_NOT_ALLOWED),
        # A renamed file: the type says PDF, the name does not.
        ("run.exe", "application/pdf", 10, storage.FILE_TYPE_NOT_ALLOWED),
    ],
)
def test_check_upload(name: str, content_type: str, size: int, expected: str | None) -> None:
    assert storage.check_upload(name, content_type, size) == expected


def test_exactly_the_limit_is_allowed() -> None:
    assert storage.check_upload("a.pdf", "application/pdf", storage.MAX_UPLOAD_BYTES) is None


def test_limits_match_the_allowed_table() -> None:
    limits = storage.limits()
    assert limits.max_upload_mb == 25
    assert "application/pdf" in limits.allowed_types
    assert ".pdf" in limits.allowed_extensions
    assert ".exe" not in limits.allowed_extensions


def test_object_key_keeps_only_the_extension() -> None:
    key = storage.object_key(7, "My Report (final).PDF")
    assert key.startswith("org-7/")
    assert key.endswith(".pdf")
    assert "Report" not in key
    assert key != storage.object_key(7, "My Report (final).PDF")


def test_local_backend_round_trip(tmp_path: Path) -> None:
    backend = LocalBackend(tmp_path)
    key = storage.object_key(1, "a.txt")

    assert backend.size_of(key) is None
    backend.write(key, b"hello")
    assert backend.size_of(key) == 5
    assert backend.read(key) == b"hello"

    backend.delete(key)
    assert backend.size_of(key) is None
    backend.delete(key)  # missing is not an error


def test_local_backend_urls_point_at_the_dev_route(tmp_path: Path) -> None:
    backend = LocalBackend(tmp_path)
    assert (
        backend.upload_url("org-1/abc.pdf", "application/pdf", 3)
        == "/api/files/local/org-1/abc.pdf"
    )
    assert backend.download_url("org-1/abc.pdf", "x.pdf") == "/api/files/local/org-1/abc.pdf"


def test_local_backend_refuses_keys_that_leave_the_directory(tmp_path: Path) -> None:
    backend = LocalBackend(tmp_path)
    with pytest.raises(ValueError):
        backend.read("../outside.txt")


def test_backend_for_defaults_to_local(tmp_path: Path) -> None:
    settings = Settings(database_url="postgresql://x", local_storage_dir=str(tmp_path))
    backend = storage.backend_for(settings)
    assert isinstance(backend, LocalBackend)
    assert backend.root == tmp_path
