"""SCRUM-21: the resubmit rule and the version numbering.

These are plain-object tests and need no database. The API tests that write
real rows (version 2 created, version 1 untouched) are in test_submit_api.py
and run against PostgreSQL.
"""

import pytest

from models import Submission
from resubmit import can_resubmit, next_version


def version(number: int, status: str) -> Submission:
    return Submission(assignment_id=1, membership_id=1, version=number, status=status)


def test_first_hand_in_is_version_one() -> None:
    assert next_version(None) == 1


@pytest.mark.parametrize("number", [1, 2, 7])
def test_next_version_is_one_more_than_the_latest(number: int) -> None:
    assert next_version(version(number, "changes_requested")) == number + 1


def test_resubmit_allowed_after_changes_requested() -> None:
    assert can_resubmit(version(1, "changes_requested")) is True


@pytest.mark.parametrize("status", ["submitted", "approved"])
def test_resubmit_not_allowed_while_waiting_or_once_approved(status: str) -> None:
    assert can_resubmit(version(1, status)) is False


def test_nothing_to_resubmit_before_the_first_hand_in() -> None:
    assert can_resubmit(None) is False
