"""Create an invite link, for local and staging testing (SCRUM-11).

A dev helper until the admin screens land: it stands in for "the founder
sets up the organization" (SCRUM-42) and "an admin invites a cohort"
(SCRUM-39), creating whatever is missing by name and then printing the
invite URL once. Delete it when those arrive.

Usage, from api/ with DATABASE_URL set and migrations applied:

    python scripts/create_invite.py amara@example.com \\
        --inviter marguerite@example.com --inviter-name "Marguerite Ellis" \\
        --cohort "Autumn 2026 · Cohort 7" --starts 2026-09-28 --ends 2026-12-18 \\
        --track UX/UI --team Design \\
        --site https://byline-web-xxxx.onrender.com

Only the invitee email and --inviter are required. The organization, cohort,
track, team and inviter are created if they do not exist yet. An inviter
created here gets a random password nobody knows; it is a name on the invite,
not an account anyone signs in with.
"""

import argparse
import secrets
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from db import get_session_factory  # noqa: E402
from invites import INVITE_LIFETIME, create_invite  # noqa: E402
from models import Cohort, Membership, Organization, Person, Team, Track  # noqa: E402
from security import hash_password  # noqa: E402


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("email", help="who to invite")
    parser.add_argument(
        "--inviter", required=True, help="email of the supervisor or admin sending it"
    )
    parser.add_argument("--inviter-name", default="Your supervisor", help="used only if created")
    parser.add_argument("--org", default="The Emerson Empire")
    parser.add_argument("--cohort", default=None, help="cohort name; created if missing")
    parser.add_argument("--starts", type=date.fromisoformat, default=None, help="YYYY-MM-DD")
    parser.add_argument("--ends", type=date.fromisoformat, default=None, help="YYYY-MM-DD")
    parser.add_argument("--track", default=None, help="track name; created if missing")
    parser.add_argument("--pack", default=None, help="onboarding pack URL, if creating the track")
    parser.add_argument("--team", default=None, help="team name; created if missing")
    parser.add_argument("--role", default="member", choices=["member", "supervisor", "admin"])
    parser.add_argument("--site", default="http://localhost:5173", help="where the web app runs")
    return parser.parse_args(argv)


def organization(db: Session, name: str) -> Organization:
    slug = "-".join(name.lower().split())
    org = db.scalar(select(Organization).where(Organization.slug == slug))
    if org is None:
        org = Organization(name=name, slug=slug)
        db.add(org)
        db.flush()
        print(f"Created organization {org.name!r}")
    return org


def cohort(db: Session, org: Organization, args: argparse.Namespace) -> Cohort | None:
    if not args.cohort:
        return None
    row = db.scalar(
        select(Cohort).where(Cohort.organization_id == org.id, Cohort.name == args.cohort)
    )
    if row is None:
        row = Cohort(
            organization_id=org.id, name=args.cohort, starts_on=args.starts, ends_on=args.ends
        )
        db.add(row)
        db.flush()
        print(f"Created cohort {row.name!r}")
    return row


def track(db: Session, org: Organization, args: argparse.Namespace) -> Track | None:
    if not args.track:
        return None
    row = db.scalar(select(Track).where(Track.organization_id == org.id, Track.name == args.track))
    if row is None:
        row = Track(organization_id=org.id, name=args.track, onboarding_pack_url=args.pack)
        db.add(row)
        db.flush()
        print(f"Created track {row.name!r}")
    return row


def team(db: Session, org: Organization, name: str | None) -> Team | None:
    if not name:
        return None
    row = db.scalar(select(Team).where(Team.organization_id == org.id, Team.name == name))
    if row is None:
        row = Team(organization_id=org.id, name=name)
        db.add(row)
        db.flush()
        print(f"Created team {row.name!r}")
    return row


def inviter(
    db: Session, org: Organization, team_row: Team | None, args: argparse.Namespace
) -> Membership:
    email = args.inviter.lower()
    person = db.scalar(select(Person).where(Person.email == email))
    if person is None:
        person = Person(
            email=email,
            full_name=args.inviter_name,
            password_hash=hash_password(secrets.token_urlsafe(32)),
        )
        db.add(person)
        db.flush()
        print(f"Created inviter {person.full_name!r} <{email}> (no usable password)")
    membership = db.scalar(
        select(Membership).where(
            Membership.person_id == person.id, Membership.organization_id == org.id
        )
    )
    if membership is None:
        membership = Membership(
            person_id=person.id,
            organization_id=org.id,
            role="supervisor",
            team_id=team_row.id if team_row else None,
        )
        db.add(membership)
        db.flush()
        print(f"Made {person.full_name!r} a supervisor in {org.name!r}")
    return membership


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    with get_session_factory()() as db:
        if db.scalar(select(Person).where(Person.email == args.email.lower())):
            print(f"{args.email} already has an account; they should sign in instead.")
            return 1
        org = organization(db, args.org)
        team_row = team(db, org, args.team)
        cohort_row = cohort(db, org, args)
        track_row = track(db, org, args)
        sender = inviter(db, org, team_row, args)
        db.commit()
        invite, token = create_invite(
            db,
            organization_id=org.id,
            invited_by_membership_id=sender.id,
            email=args.email,
            role=args.role,
            team_id=team_row.id if team_row else None,
            cohort_id=cohort_row.id if cohort_row else None,
            track_id=track_row.id if track_row else None,
        )
        invite_id, invite_email = invite.id, invite.email
    print(f"Invite {invite_id} for {invite_email}, valid {INVITE_LIFETIME.days} days.")
    print("The link below is shown once; only its hash is stored:")
    print(f"{args.site.rstrip('/')}/invite/{token}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
