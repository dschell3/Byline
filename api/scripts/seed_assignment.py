"""Seed an assignment nobody has handed in yet, for local and staging testing (SCRUM-18).

Until supervisors can write assignments in the app (P22), nothing fills in an
assignment's description, criteria, reference links or attachments. This
creates the one from the Figma frame, so the assignment page (P12, SCRUM-18)
has something real to show and the Submit button (P13) has somewhere to
start. Delete it when P22 arrives.

What it writes, in one organization and team: an assignment due in four days,
15 points, accepted up to 48 hours late at half points, with a two-paragraph
description, four assessment criteria, two reference links and two attachments.

Usage, from api/ with DATABASE_URL set and migrations applied:

    python scripts/seed_assignment.py amara@example.com --password "pick one"

Takes the same options as seed_submission.py and creates the same people if
they are missing, so the two scripts can seed one member. Running it twice
does nothing new: the assignment is found by title.
"""

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from db import get_session_factory  # noqa: E402
from models import AssessmentCriterion, Assignment, Membership, Organization, Team  # noqa: E402
from scripts.create_invite import organization, team  # noqa: E402
from scripts.seed_submission import parse_args, person_in  # noqa: E402

ASSIGNMENT_TITLE = "Usability audit of the donor sign-up flow"
POINTS = 15
LATE_CUTOFF_HOURS = 48
DESCRIPTION = (
    "Walk through the donor sign-up flow as if you had never seen the site. Record what you "
    "hit. We are about to rebuild this flow and I would rather find the problems from you "
    "than from a donor who gives up halfway.\n\n"
    "Use whatever tool you like. A shared doc or a PDF is fine. Do not spend time making it "
    "pretty."
)
# (text, detail, max_points)
CRITERIA = [
    (
        "Every step of the sign-up flow is captured",
        "Screenshots or a recording, start to finish",
        4,
    ),
    (
        "At least five problems, each with severity",
        "Say why it is a problem, not just what it is",
        6,
    ),
    ("A recommendation per problem", "One sentence each is enough", 3),
    ("Written so a non-designer understands it", None, 2),
]
REFERENCE_LINKS = [
    {"label": "The current sign-up flow", "url": "https://example.org/sign-up"},
    {
        "label": "Nielsen's ten heuristics",
        "url": "https://www.nngroup.com/articles/ten-usability-heuristics/",
    },
]
ATTACHMENTS = [
    {
        "name": "audit-template.docx",
        "key": "assignments/demo/audit-template.docx",
        "size_bytes": 24_576,
    },
    {"name": "brand-voice.pdf", "key": "assignments/demo/brand-voice.pdf", "size_bytes": 1_153_434},
]


def seed(
    db: Session,
    org: Organization,
    team_row: Team,
    supervisor: Membership,
    now: datetime | None = None,
) -> Assignment:
    """Write the assignment and its criteria, or return the one already there.

    It targets ``team_row``, so every member on that team sees it. Flushes but
    does not commit; the caller decides.
    """
    now = now or datetime.now(UTC)
    assignment = db.scalar(
        select(Assignment).where(
            Assignment.organization_id == org.id, Assignment.title == ASSIGNMENT_TITLE
        )
    )
    if assignment is not None:
        print(f"Assignment {ASSIGNMENT_TITLE!r} already seeded; nothing new written")
        return assignment
    assignment = Assignment(
        organization_id=org.id,
        created_by_membership_id=supervisor.id,
        team_id=team_row.id,
        title=ASSIGNMENT_TITLE,
        description=DESCRIPTION,
        reference_links=REFERENCE_LINKS,
        attachments=ATTACHMENTS,
        points_value=POINTS,
        is_mandatory=True,
        late_policy="accepted_half_points",
        late_cutoff_hours=LATE_CUTOFF_HOURS,
        due_at=now + timedelta(days=4),
        created_at=now - timedelta(days=3),
    )
    db.add(assignment)
    db.flush()
    db.add_all(
        AssessmentCriterion(
            assignment_id=assignment.id,
            position=i + 1,
            text=text,
            detail=detail,
            max_points=points,
        )
        for i, (text, detail, points) in enumerate(CRITERIA)
    )
    db.flush()
    print(f"Created assignment {ASSIGNMENT_TITLE!r} with {len(CRITERIA)} criteria")
    return assignment


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    with get_session_factory()() as db:
        org = organization(db, args.org)
        team_row = team(db, org, args.team)
        assert team_row is not None  # the invite helper returns None only for a blank name
        supervisor = person_in(
            db, org, team_row, args.supervisor, args.supervisor_name, "supervisor", None
        )
        person_in(db, org, team_row, args.member, args.member_name, "member", args.password)
        assignment = seed(db, org, team_row, supervisor)
        db.commit()
        assignment_id = assignment.id
    print(f"Assignment page: {args.site.rstrip('/')}/a/{assignment_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
