"""Seed a reviewed, resubmitted submission, for local and staging testing (SCRUM-22).

Until the submit flow (SCRUM-19) and the review screens (Sprint 4) exist,
nothing writes submissions, reviews or comments. This creates one member's
worth, so the submission page (P14, SCRUM-22) and the resubmit screen (P13,
SCRUM-21) have something real to show. Delete it when those arrive.

What it writes, all in one organization and team:

- an assignment with four assessment criteria, due five days ago, 20 points
- version 1 of the member's submission, with a final review that requested
  changes: a written reason and a score per criterion
- two comments on version 1, the second a reply to the first
- version 2, resubmitted and waiting for review

Usage, from api/ with DATABASE_URL set and migrations applied:

    python scripts/seed_submission.py amara@example.com --password "pick one"

Only the member email is required. The organization, team, supervisor and
member are created if they do not exist yet. --password sets the member's
password only when the person is created here, so you can sign in as them;
without it a created member gets a random password nobody knows. Running it
twice does nothing new: the assignment is found by title.
"""

import argparse
import secrets
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from db import get_session_factory  # noqa: E402
from models import (  # noqa: E402
    AssessmentCriterion,
    Assignment,
    Membership,
    Organization,
    Person,
    Review,
    ReviewCriterionScore,
    Submission,
    SubmissionComment,
    Team,
)
from scripts.create_invite import organization, team  # noqa: E402
from security import hash_password  # noqa: E402

ASSIGNMENT_TITLE = "Wireframes for the volunteer dashboard"
CRITERIA = [
    ("Covers the three volunteer tasks from the brief", 5),
    ("Mobile layout at 375px", 5),
    ("Labels and empty states are written, not lorem ipsum", 5),
    ("Annotated: what each screen is for and why", 5),
]
REASON = (
    "The desktop flow is there, but the phone layout stops at the sign-up step and two "
    "screens still have placeholder labels. Finish the 375px frames and write the real "
    "labels, then send it back."
)
SCORES = [5, 2, 2, 4]


@dataclass
class Seeded:
    """What the seed created or found, for the script's output and the tests."""

    organization_id: int
    team_id: int
    supervisor_membership_id: int
    member_membership_id: int
    assignment_id: int
    criterion_ids: list[int]
    version1_id: int
    review_id: int
    version2_id: int
    comment_ids: list[int]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("member", help="email of the intern whose submission this is")
    parser.add_argument("--member-name", default="Amara Okafor", help="used only if created")
    parser.add_argument("--password", default=None, help="member's password, only if created")
    parser.add_argument("--supervisor", default="marguerite@example.com")
    parser.add_argument("--supervisor-name", default="Marguerite Ellis", help="only if created")
    parser.add_argument("--org", default="The Emerson Empire")
    parser.add_argument("--team", default="Design")
    parser.add_argument("--site", default="http://localhost:5173", help="where the web app runs")
    return parser.parse_args(argv)


def person_in(
    db: Session,
    org: Organization,
    team_row: Team,
    email: str,
    full_name: str,
    role: str,
    password: str | None,
) -> Membership:
    """The membership for ``email`` in ``org``, creating the person and membership if needed."""
    email = email.lower()
    person = db.scalar(select(Person).where(Person.email == email))
    if person is None:
        person = Person(
            email=email,
            full_name=full_name,
            password_hash=hash_password(password or secrets.token_urlsafe(32)),
        )
        db.add(person)
        db.flush()
        usable = "with the given password" if password else "(no usable password)"
        print(f"Created {role} {person.full_name!r} <{email}> {usable}")
    membership = db.scalar(
        select(Membership).where(
            Membership.person_id == person.id, Membership.organization_id == org.id
        )
    )
    if membership is None:
        membership = Membership(
            person_id=person.id, organization_id=org.id, role=role, team_id=team_row.id
        )
        db.add(membership)
        db.flush()
        print(f"Made {person.full_name!r} a {role} on {team_row.name!r}")
    return membership


def seed(
    db: Session,
    org: Organization,
    team_row: Team,
    supervisor: Membership,
    member: Membership,
    now: datetime | None = None,
) -> Seeded:
    """Write the assignment, criteria, two versions, review, scores and comments.

    Finds the assignment by title first, so a second run returns what the
    first created. Flushes but does not commit; the caller decides.
    """
    now = now or datetime.now(UTC)
    assignment = db.scalar(
        select(Assignment).where(
            Assignment.organization_id == org.id, Assignment.title == ASSIGNMENT_TITLE
        )
    )
    created = assignment is None
    if created:
        assignment = Assignment(
            organization_id=org.id,
            created_by_membership_id=supervisor.id,
            team_id=team_row.id,
            title=ASSIGNMENT_TITLE,
            points_value=20,
            is_mandatory=True,
            late_policy="accepted_full_points",
            due_at=now - timedelta(days=5),
            created_at=now - timedelta(days=12),
        )
        db.add(assignment)
        db.flush()
        db.add_all(
            AssessmentCriterion(
                assignment_id=assignment.id, position=i + 1, text=text, max_points=points
            )
            for i, (text, points) in enumerate(CRITERIA)
        )
        db.flush()
    criteria = db.scalars(
        select(AssessmentCriterion)
        .where(AssessmentCriterion.assignment_id == assignment.id)
        .order_by(AssessmentCriterion.position)
    ).all()

    if created:
        version1 = Submission(
            assignment_id=assignment.id,
            membership_id=member.id,
            version=1,
            file_keys=["submissions/demo/volunteer-dashboard-v1.pdf"],
            status="changes_requested",
            submitted_at=now - timedelta(days=5, hours=3),
        )
        db.add(version1)
        db.flush()
        review = Review(
            submission_id=version1.id,
            actor_type="person",
            actor_id=supervisor.id,
            decision="changes_requested",
            reason=REASON,
            is_final=True,
            created_at=now - timedelta(days=3),
        )
        db.add(review)
        db.flush()
        db.add_all(
            ReviewCriterionScore(
                review_id=review.id,
                criterion_id=criterion.id,
                score=score,
                note="Stops at sign-up" if criterion.position == 2 else None,
            )
            for criterion, score in zip(criteria, SCORES, strict=True)
        )
        first = SubmissionComment(
            submission_id=version1.id,
            author_membership_id=member.id,
            body="Should the phone frames cover the admin screens too, or just the volunteer side?",
            created_at=now - timedelta(days=2, hours=20),
        )
        db.add(first)
        db.flush()
        reply = SubmissionComment(
            submission_id=version1.id,
            author_membership_id=supervisor.id,
            parent_comment_id=first.id,
            body="Just the volunteer side for this one. Admin is a separate assignment.",
            created_at=now - timedelta(days=2, hours=18),
        )
        db.add(reply)
        version2 = Submission(
            assignment_id=assignment.id,
            membership_id=member.id,
            version=2,
            file_keys=["submissions/demo/volunteer-dashboard-v2.pdf"],
            status="submitted",
            submitted_at=now - timedelta(days=1),
        )
        db.add(version2)
        db.flush()
        print(f"Created assignment {ASSIGNMENT_TITLE!r} with two versions and one review")
    else:
        versions = db.scalars(
            select(Submission)
            .where(Submission.assignment_id == assignment.id, Submission.membership_id == member.id)
            .order_by(Submission.version)
        ).all()
        version1, version2 = versions[0], versions[-1]
        review = db.scalar(select(Review).where(Review.submission_id == version1.id))
        first, reply = db.scalars(
            select(SubmissionComment)
            .where(SubmissionComment.submission_id == version1.id)
            .order_by(SubmissionComment.created_at)
        ).all()
        print(f"Assignment {ASSIGNMENT_TITLE!r} already seeded; nothing new written")

    return Seeded(
        organization_id=org.id,
        team_id=team_row.id,
        supervisor_membership_id=supervisor.id,
        member_membership_id=member.id,
        assignment_id=assignment.id,
        criterion_ids=[c.id for c in criteria],
        version1_id=version1.id,
        review_id=review.id,
        version2_id=version2.id,
        comment_ids=[first.id, reply.id],
    )


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    with get_session_factory()() as db:
        org = organization(db, args.org)
        team_row = team(db, org, args.team)
        assert team_row is not None  # the invite helper returns None only for a blank name
        supervisor = person_in(
            db, org, team_row, args.supervisor, args.supervisor_name, "supervisor", None
        )
        member = person_in(
            db, org, team_row, args.member, args.member_name, "member", args.password
        )
        seeded = seed(db, org, team_row, supervisor, member)
        db.commit()
    site = args.site.rstrip("/")
    print(f"Version 1 (changes requested): {site}/s/{seeded.version1_id}")
    print(f"Version 2 (submitted):         {site}/s/{seeded.version2_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
