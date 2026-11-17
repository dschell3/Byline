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
        SubmitWorkRequest(kind="video", content="something.mp4")


# --- SCRUM-83: file submissions ---------------------------------------------


def test_file_submission_needs_at_least_one_file() -> None:
    with pytest.raises(ValidationError, match="at least one file"):
        SubmitWorkRequest(kind="file")


def test_file_submission_keeps_the_note_and_the_ids() -> None:
    request = SubmitWorkRequest(kind="file", file_ids=[3, 1], content="  Two drafts.  ")
    assert request.file_ids == [3, 1]
    assert request.content == "Two drafts."


def test_file_submission_note_is_optional() -> None:
    assert SubmitWorkRequest(kind="file", file_ids=[1]).content == ""


def test_file_submission_rejects_duplicates_and_too_many() -> None:
    with pytest.raises(ValidationError, match="once"):
        SubmitWorkRequest(kind="file", file_ids=[1, 1])
    with pytest.raises(ValidationError):
        SubmitWorkRequest(kind="file", file_ids=list(range(1, 12)))


@pytest.mark.parametrize("kind", ["text", "link", "pr"])
def test_files_only_go_with_a_file_submission(kind: str) -> None:
    with pytest.raises(ValidationError, match="file submission"):
        SubmitWorkRequest(kind=kind, content="https://github.com/o/r/pull/1", file_ids=[1])


def test_text_still_needs_content() -> None:
    with pytest.raises(ValidationError):
        SubmitWorkRequest(kind="text")
