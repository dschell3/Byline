"""Create one person with a hashed password, for local testing only.

This is a dev helper so the sign-in endpoint (SCRUM-9) and the sign-in page
(SCRUM-8) have an account to try. It is not how users get created in the
product: that is the invite flow in SCRUM-11, and this file is deleted when
that lands.

Usage, from api/ with DATABASE_URL set and migrations applied:

    python scripts/create_person.py sham@example.com "Sham Phagura" 'a password'
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from db import get_session_factory  # noqa: E402
from models import Person  # noqa: E402
from security import hash_password  # noqa: E402


def main(argv: list[str]) -> int:
    """Insert the person, or report that the email is already taken."""
    if len(argv) != 4:
        print(__doc__)
        return 2
    _, email, full_name, password = argv
    email = email.lower()
    with get_session_factory()() as session:
        if session.scalar(select(Person).where(Person.email == email)):
            print(f"{email} already exists; nothing changed.")
            return 1
        person = Person(email=email, full_name=full_name, password_hash=hash_password(password))
        session.add(person)
        session.commit()
        print(f"Created person {person.id}: {full_name} <{email}>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
