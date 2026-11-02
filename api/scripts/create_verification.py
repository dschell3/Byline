"""Create an email verification link, for local and staging testing (SCRUM-12).

A dev helper until real email sending lands: it prints the P04 link for an
existing person so each of the three screens can be checked by hand.

Usage, from api/ with DATABASE_URL set and migrations applied:

    python scripts/create_verification.py amara@example.com
    python scripts/create_verification.py amara@example.com --expired
    python scripts/create_verification.py amara@example.com \\
        --site https://byline-web-xxxx.onrender.com

Open the link once to see "Email confirmed", again to see "Already verified".
--expired makes a link that ran out a minute ago, to see "This link has expired".
"""

import argparse
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

import sessions  # noqa: E402
from db import get_session_factory  # noqa: E402
from models import Person  # noqa: E402
from verifications import VERIFICATION_LIFETIME, create_verification  # noqa: E402


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("email", help="an existing person's email")
    parser.add_argument("--site", default="http://localhost:5173", help="where the web app runs")
    parser.add_argument(
        "--expired", action="store_true", help="make a link that has already expired"
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    with get_session_factory()() as db:
        person = db.scalar(select(Person).where(Person.email == args.email.strip().lower()))
        if person is None:
            print(f"No person with email {args.email}. Create one with create_invite.py first.")
            return 1
        verification, token = create_verification(db, person)
        if args.expired:
            verification.expires_at = sessions.now() - timedelta(minutes=1)
            db.commit()
        lifetime = "already expired" if args.expired else f"lasts {VERIFICATION_LIFETIME}"
        print(f"Verification link for {person.email} ({lifetime}):")
        print(f"{args.site.rstrip('/')}/verify/{token}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
