"""SCRUM-23: the late policy rules. No database needed, so these run in CI as is.

Each test builds an assignment in memory with a known due date and policy,
then asks the rules about a hand-in at a known moment.
"""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from late_policy import (
    ACCEPTED_FULL_POINTS,
    ACCEPTED_HALF_POINTS,
    NOT_ACCEPTED,
    can_still_be_handed_in,
    last_moment_late_work_is_taken,
    points_after_late_penalty,
    was_handed_in_late,
)
from models import Assignment

DUE = datetime(2026, 11, 13, 23, 59, 59, tzinfo=UTC)
ONE_SECOND = timedelta(seconds=1)
ONE_HOUR = timedelta(hours=1)
INDIA = timezone(timedelta(hours=5, minutes=30))


def an_assignment(
    late_policy: str = ACCEPTED_FULL_POINTS,
    late_cutoff_hours: int | None = None,
    due_at: datetime | None = DUE,
    points_value: int = 15,
) -> Assignment:
    return Assignment(
        id=1,
        title="Homework",
        late_policy=late_policy,
        late_cutoff_hours=late_cutoff_hours,
        due_at=due_at,
        points_value=points_value,
    )


# --- Was it late? -------------------------------------------------------------


def test_work_handed_in_one_second_before_the_deadline_is_on_time() -> None:
    assert was_handed_in_late(an_assignment(), DUE - ONE_SECOND) is False


def test_work_handed_in_at_the_exact_deadline_is_on_time() -> None:
    assert was_handed_in_late(an_assignment(), DUE) is False


def test_work_handed_in_one_second_after_the_deadline_is_late() -> None:
    assert was_handed_in_late(an_assignment(), DUE + ONE_SECOND) is True


def test_a_hand_in_at_11_59_59_pm_in_india_on_the_due_date_is_on_time() -> None:
    due_at_midnight_in_india = datetime(2026, 11, 13, 23, 59, 59, tzinfo=INDIA)
    handed_in_in_india = datetime(2026, 11, 13, 23, 59, 59, tzinfo=INDIA)
    assignment = an_assignment(due_at=due_at_midnight_in_india)
    assert was_handed_in_late(assignment, handed_in_in_india) is False


def test_work_with_no_due_date_is_never_late() -> None:
    assignment = an_assignment(due_at=None)
    assert was_handed_in_late(assignment, DUE + timedelta(days=365)) is False


# --- Can it still be handed in? -------------------------------------------------


def test_anything_can_be_handed_in_before_the_deadline() -> None:
    assignment = an_assignment(late_policy=NOT_ACCEPTED)
    assert can_still_be_handed_in(assignment, DUE - ONE_HOUR) is True


def test_nothing_can_be_handed_in_after_the_deadline_when_late_work_is_not_accepted() -> None:
    assignment = an_assignment(late_policy=NOT_ACCEPTED)
    assert can_still_be_handed_in(assignment, DUE + ONE_SECOND) is False


def test_late_work_with_no_cutoff_is_taken_however_late_it_is() -> None:
    assignment = an_assignment(late_policy=ACCEPTED_FULL_POINTS, late_cutoff_hours=None)
    assert can_still_be_handed_in(assignment, DUE + timedelta(days=30)) is True


def test_a_48_hour_cutoff_takes_work_up_to_and_including_the_48th_hour() -> None:
    assignment = an_assignment(late_policy=ACCEPTED_HALF_POINTS, late_cutoff_hours=48)
    assert can_still_be_handed_in(assignment, DUE + 47 * ONE_HOUR) is True
    assert can_still_be_handed_in(assignment, DUE + 48 * ONE_HOUR) is True
    assert can_still_be_handed_in(assignment, DUE + 48 * ONE_HOUR + ONE_SECOND) is False


def test_the_last_moment_late_work_is_taken() -> None:
    assert last_moment_late_work_is_taken(an_assignment(late_policy=NOT_ACCEPTED)) == DUE
    with_cutoff = an_assignment(late_policy=ACCEPTED_HALF_POINTS, late_cutoff_hours=48)
    assert last_moment_late_work_is_taken(with_cutoff) == DUE + 48 * ONE_HOUR
    assert last_moment_late_work_is_taken(an_assignment(late_cutoff_hours=None)) is None
    assert last_moment_late_work_is_taken(an_assignment(due_at=None)) is None


# --- What is it worth? ----------------------------------------------------------


def test_on_time_work_keeps_every_point_whatever_the_policy() -> None:
    for policy in (NOT_ACCEPTED, ACCEPTED_FULL_POINTS, ACCEPTED_HALF_POINTS):
        assert points_after_late_penalty(an_assignment(late_policy=policy), DUE) == 15


def test_late_work_keeps_every_point_when_the_policy_is_full_points() -> None:
    assignment = an_assignment(late_policy=ACCEPTED_FULL_POINTS)
    assert points_after_late_penalty(assignment, DUE + ONE_HOUR) == 15


def test_late_work_is_worth_half_rounded_up_when_the_policy_is_half_points() -> None:
    fifteen_points = an_assignment(late_policy=ACCEPTED_HALF_POINTS, points_value=15)
    ten_points = an_assignment(late_policy=ACCEPTED_HALF_POINTS, points_value=10)
    assert points_after_late_penalty(fifteen_points, DUE + ONE_HOUR) == 8
    assert points_after_late_penalty(ten_points, DUE + ONE_HOUR) == 5


def test_working_out_points_for_late_work_that_was_never_allowed_is_a_mistake() -> None:
    assignment = an_assignment(late_policy=NOT_ACCEPTED)
    with pytest.raises(ValueError, match="does not accept late work"):
        points_after_late_penalty(assignment, DUE + ONE_HOUR)
