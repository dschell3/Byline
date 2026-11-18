"""Validation for text, link, GitHub PR and file submissions (SCRUM-19, SCRUM-83).

A file submission names stored_file ids the member has already uploaded
and completed; the router checks those against the database. Any text
sent with it is an optional note.
"""

import re
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, model_validator

SubmissionKind = Literal["text", "link", "pr", "file"]

MAX_TEXT_CHARS = 20_000
MAX_URL_CHARS = 2_048
# Files on one submission. Enough for a brief and its sources.
MAX_FILES = 10

GITHUB_PULL_PATH = re.compile(r"/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/pull/[1-9][0-9]*/?")


def validate_submission(kind: SubmissionKind, value: str) -> str:
    """Trim and validate submitted content."""
    content = value.strip()

    if not content:
        raise ValueError("Enter something to submit.")

    if kind == "text":
        if len(content) > MAX_TEXT_CHARS:
            raise ValueError("Text submissions must be 20,000 characters or fewer.")
        return content

    if len(content) > MAX_URL_CHARS or any(character.isspace() for character in content):
        raise ValueError("Enter a URL of 2,048 characters or fewer, without spaces.")

    try:
        parsed = urlsplit(content)
        host = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Enter a valid URL.") from exc

    if (
        parsed.scheme not in {"https", "http"}
        or not host
        or "." not in host
        or parsed.username is not None
        or parsed.password is not None
        or port == 0
    ):
        raise ValueError("Enter a full http:// or https:// URL.")

    if kind == "pr" and (
        parsed.scheme != "https"
        or host.lower() != "github.com"
        or GITHUB_PULL_PATH.fullmatch(parsed.path) is None
    ):
        raise ValueError(
            "Enter a GitHub pull request URL, such as https://github.com/org/repo/pull/123."
        )

    return content


class SubmitWorkRequest(BaseModel):
    kind: SubmissionKind
    # Required for text, link and pr. For file it is an optional note.
    content: str = Field(default="", max_length=MAX_TEXT_CHARS)
    # For kind "file" only: completed uploads of the member's own.
    file_ids: list[int] = Field(default_factory=list, max_length=MAX_FILES)

    @model_validator(mode="after")
    def validate_input(self) -> Self:
        if self.kind == "file":
            if not self.file_ids:
                raise ValueError("Attach at least one file.")
            if len(set(self.file_ids)) != len(self.file_ids):
                raise ValueError("Each file can be attached once.")
            self.content = self.content.strip()
            return self
        if self.file_ids:
            raise ValueError("Files go with a file submission.")
        self.content = validate_submission(self.kind, self.content)
        return self
