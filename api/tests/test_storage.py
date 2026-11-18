"""SCRUM-83: the storage interface on the local backend, and the upload limits. No database."""

import os
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from botocore.stub import Stubber

import storage
from config import StorageSettings
from storage import LocalBackend, R2Backend


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


def test_allowed_extensions_come_from_the_type_table() -> None:
    assert ".pdf" in storage.ALLOWED_EXTENSIONS
    assert ".exe" not in storage.ALLOWED_EXTENSIONS


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
    settings = StorageSettings(local_storage_dir=str(tmp_path))
    backend = storage.backend_for(settings)
    assert isinstance(backend, LocalBackend)
    assert backend.root == tmp_path


# --- R2 backend, signing only (no network) ----------------------------------


@pytest.fixture
def r2() -> R2Backend:
    return R2Backend(
        endpoint="https://example.r2.cloudflarestorage.com",
        bucket="byline-test",
        access_key_id="AKIAFAKEFAKEFAKEFAKE",
        secret_access_key="not-a-real-secret",
    )


def test_r2_upload_url_is_a_signed_put_for_that_key(r2: R2Backend) -> None:
    url = r2.upload_url("org-1/abc.pdf", "application/pdf", 1234)
    parts = urlsplit(url)
    assert parts.scheme == "https"
    assert parts.netloc == "example.r2.cloudflarestorage.com"
    assert parts.path == "/byline-test/org-1/abc.pdf"
    query = parse_qs(parts.query)
    assert query["X-Amz-Algorithm"] == ["AWS4-HMAC-SHA256"]
    assert query["X-Amz-Expires"] == [str(storage.URL_TTL_SECONDS)]
    assert "X-Amz-Signature" in query
    assert "not-a-real-secret" not in url


def test_r2_download_url_names_the_file(r2: R2Backend) -> None:
    url = r2.download_url("org-1/abc.pdf", 'My "Report".pdf')
    query = parse_qs(urlsplit(url).query)
    assert query["response-content-disposition"] == ['attachment; filename="My Report.pdf"']


def test_r2_size_of_reads_head_and_treats_404_as_missing(r2: R2Backend) -> None:
    with Stubber(r2.client) as stub:
        stub.add_response(
            "head_object",
            {"ContentLength": 1234},
            {"Bucket": "byline-test", "Key": "org-1/abc.pdf"},
        )
        stub.add_client_error(
            "head_object",
            service_error_code="404",
            http_status_code=404,
            expected_params={"Bucket": "byline-test", "Key": "org-1/missing.pdf"},
        )
        assert r2.size_of("org-1/abc.pdf") == 1234
        assert r2.size_of("org-1/missing.pdf") is None


def test_r2_delete_calls_delete_object(r2: R2Backend) -> None:
    with Stubber(r2.client) as stub:
        stub.add_response("delete_object", {}, {"Bucket": "byline-test", "Key": "org-1/abc.pdf"})
        r2.delete("org-1/abc.pdf")


def test_backend_for_r2_needs_all_four_values() -> None:
    settings = StorageSettings(storage_backend="r2", r2_endpoint="https://x", r2_bucket="b")
    with pytest.raises(RuntimeError, match="R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY"):
        storage.backend_for(settings)


# --- The real bucket. Skipped in CI; run locally with the four R2 variables set.


R2_VARS = ("R2_ENDPOINT", "R2_BUCKET", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY")


@pytest.mark.skipif(
    not all(os.environ.get(name) for name in R2_VARS),
    reason="needs the four R2_* variables for a real bucket",
)
def test_real_bucket_round_trip() -> None:
    import httpx

    backend = R2Backend(
        endpoint=os.environ["R2_ENDPOINT"],
        bucket=os.environ["R2_BUCKET"],
        access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
    )
    key = storage.object_key(0, "round-trip.txt")
    data = b"SCRUM-83 round trip"
    try:
        put = httpx.put(
            backend.upload_url(key, "text/plain", len(data)),
            content=data,
            headers={"Content-Type": "text/plain"},
        )
        assert put.status_code == 200, put.text
        assert backend.size_of(key) == len(data)
        got = httpx.get(backend.download_url(key, "round-trip.txt"))
        assert got.status_code == 200
        assert got.content == data
        assert got.headers["content-disposition"] == 'attachment; filename="round-trip.txt"'
    finally:
        backend.delete(key)
    assert backend.size_of(key) is None
