"""SCRUM-19: validation tests for P13 submissions."""

import pytest
from pydantic import ValidationError

from submit_work import SubmitWorkRequest, validate_submission


@pytest.mark.parametrize(
    ("kind", "value"),
    [
        ("text", "My finished assignment"),
        ("link", "https://example.com/my-work"),
        ("pr", "https://github.com/owner/repo/pull/123"),
    ],
)
def test_accepts_supported_submissions(kind: str, value: str) -> None:
    request = SubmitWorkRequest(kind=kind, content=value)
    assert request.content == value


def test_trims_whitespace() -> None:
    request = SubmitWorkRequest(
        kind="text",
        content="  My assignment  ",
    )
    assert request.content == "My assignment"


@pytest.mark.parametrize(
    "value",
    ["", " ", "\n\t"],
)
def test_rejects_empty_text(value: str) -> None:
    with pytest.raises((ValueError, ValidationError)):
        SubmitWorkRequest(kind="text", content=value)


def test_rejects_oversized_text() -> None:
    with pytest.raises(ValueError, match="20,000"):
        validate_submission("text", "a" * 20_001)


@pytest.mark.parametrize(
    "value",
    [
        "not-a-link",
        "ftp://example.com/file",
        "https://user:secret@example.com/file",
        "https://example.com/has space",
        "https://example.com:invalid/file",
    ],
)
def test_rejects_invalid_links(value: str) -> None:
    with pytest.raises(ValueError):
        validate_submission("link", value)


@pytest.mark.parametrize(
    "value",
    [
        "https://github.com/owner/repo",
        "https://github.com/owner/repo/issues/123",
        "https://github.com/owner/repo/pull/0",
        "https://example.com/owner/repo/pull/123",
        "http://github.com/owner/repo/pull/123",
        "https://github.com.evil.com/owner/repo/pull/123",
    ],
)
def test_rejects_invalid_github_pr_urls(value: str) -> None:
    with pytest.raises(ValueError):
        validate_submission("pr", value)


def test_rejects_unsupported_submission_type() -> None:
    with pytest.raises(ValidationError):
        SubmitWorkRequest(kind="file", content="something.pdf")
