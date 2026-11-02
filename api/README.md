# OverClock API

FastAPI service for the OverClock dashboard. Everything lives flat in this
folder: `main.py` is the app, `config.py` the settings, `db.py` the database
plumbing and `alembic/` the migrations.

## Requirements

- Python 3.13 (the version the pins in `requirements.txt` were resolved with)
- A Postgres connection string. Render Postgres and Supabase both work.

## First-time setup

Run everything below from inside the `api/` folder.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

The app reads a single variable from the environment.

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Postgres connection string. There is no default, so anything that touches the database fails loudly without it. |

For local work put it in an `api/.env` file, which is gitignored:

```
DATABASE_URL=postgresql://user:password@host:5432/overclock
```

Plain `postgresql://` and legacy `postgres://` URLs, as issued by Render and
Supabase, are accepted as is. The driver is pinned to psycopg 3 internally,
so switching providers is a change to this one variable and nothing else.

## Run the server

```bash
uvicorn main:app --reload
```

- <http://localhost:8000/health> returns `{"status": "ok"}`. It never touches
  the database, so it passes before one exists. Render uses it as the
  health check.
- <http://localhost:8000/docs> is the interactive API documentation.

## Sign-in

`POST /auth/sign-in` with JSON `{"email": "...", "password": "..."}`.

| Result | Status | Body |
| --- | --- | --- |
| Correct credentials | 200 | `{"id": 1, "full_name": "..."}` |
| Wrong password or unknown email | 401 | `{"detail": "Email or password is incorrect."}` |
| Too many failures | 429 | `{"detail": "Too many sign-in attempts. Try again later."}` plus a `Retry-After` header |

The two failure cases are deliberately identical in status, body and timing,
so a response never reveals whether an email is registered. The hash check
runs on both paths, against a dummy hash when there is no account.

Passwords are hashed with Argon2id (`security.py`) and never stored or logged
in plain text. Failures are rate-limited (`ratelimit.py`): 5 per account and
20 per client IP in any 15-minute window. A successful sign-in clears the
account's count. The counters live in the process, which is right for one
instance and would need a shared store if the API ever runs several.

### Sessions (SCRUM-13)

A successful sign-in starts a server-side session (`sessions.py`) and sets
the `byline_session` cookie: HTTP-only, Secure, SameSite=Lax, path `/`. The
browser never stores a token anywhere a script can read it. The database
keeps only the token's SHA-256 in `auth_session`.

| Endpoint | Result |
| --- | --- |
| `GET /auth/me` | 200 `{"id", "full_name", "roles"}`, or 401 when there is no live session |
| `POST /auth/sign-out` | 204. Revokes the session in the database, then clears the cookie |

A session ends after 2 hours idle or 30 days in total, whichever comes first,
and on sign-out. Signing in again retires the browser's previous token.

Roles come from `membership` on every request, never from the cookie, so a
role change applies immediately. Protect a route with a dependency:

```python
from sessions import CurrentUser, current_user, require_role


@router.get("/review-queue")
def review_queue(user: CurrentUser = Depends(require_role("supervisor", "admin"))) -> ...: ...
```

`current_user` answers 401 (not signed in), `require_role` answers 403
(signed in, wrong role). The web app treats a 401 as "send to sign-in and
come back here afterwards".

The web app calls the API as `/api/...` on its own origin: Vite proxies it
locally and a rewrite in `render.yaml` does it on Render. That is what lets
a SameSite cookie travel without CORS.

Accounts are created through invite links (below), not by hand.

## Invites (SCRUM-11)

A new person joins through a link. `invite` holds who is invited (email),
what they join (organization, cohort, track, team, role), who sent it, and
only the SHA-256 of the URL token, as with sessions.

| Endpoint | Result |
| --- | --- |
| `GET /invites/{token}` | Public. `state` (`open`, `expired`, `used`, `revoked`), `email`, `role`, `expires_at`, `organization`, `cohort`, `track`, `invited_by` (name and email). 404 if no such link. Non-open states still answer, so the page can say who to ask for a new one. |
| `POST /invites/{token}/accept` | Body `{"full_name", "password", "timezone"}`. Creates the person and the membership in one transaction, stamps `accepted_at`, starts a session and sets the cookie, returns 201 `{"id", "full_name"}`. 410 when expired, used or withdrawn; 409 when the email already has an account; 422 when the password is under 10 characters. |

Invites last 30 days (`invites.INVITE_LIFETIME`). A link works once: the
`accepted_at` stamp is a conditional update, so two submits cannot both win.
An unknown `timezone` is stored as UTC; the profile page (SCRUM-17) fixes it.

Until the admin screens exist (SCRUM-39, SCRUM-42), make an invite with the
dev helper, with `DATABASE_URL` set and migrations applied. It creates the
organization, cohort, track, team and inviter by name if they are missing,
then prints the link once:

```bash
python scripts/create_invite.py you@example.com \
    --inviter lyric@example.com --inviter-name "Lyric James" \
    --cohort "Autumn 2026 · Cohort 7" --starts 2026-09-28 --ends 2026-12-18 \
    --track UX/UI --team Design --site http://localhost:5173
```

`--site` is where the web app runs; use the staging address to test there.

## Home screen (SCRUM-16)

`GET /me/home` (signed in) returns what the first-run screen P11 shows:
`full_name`, `timezone`, `organization`, `cohort` (name, `starts_on`,
`ends_on`), `track` (name, `onboarding_pack_url`), `supervisor` (the active
supervisor on the member's team: name and email) and `has_work`. 404 when
the person has no active membership.

`has_work` comes from `assignments.py`, the single rule for who an
assignment reaches: picked by `recipient_membership_ids`, or every one of
team / cohort / track that the assignment names matches the member. Same
organization only. My Work (SCRUM-14) should use `assigned_to()` from there
rather than writing its own query.

## Profile (SCRUM-17)

The profile page (P18) reads and writes the signed-in person's own settings.
Both endpoints need a session, send `Cache-Control: no-store`, and answer 404
(the same message as `/me/home`) when the person has no active membership,
because byline consent lives on `membership`.

| Endpoint | Result |
| --- | --- |
| `GET /me/profile` | 200 with `full_name`, `email`, `photo_url`, `timezone`, `contact_preference`, `contact_detail`, `email_assignments`, `email_reminders`, `email_digest`, `public_byline_consent` and `public_byline_consent_at`. |
| `PATCH /me/profile` | Takes any subset of the fields below and returns 200 with the full profile after the change, in one transaction. 422 when any field is invalid, and then nothing is changed. |

| Field | Rule |
| --- | --- |
| `full_name` | 1 to 200 characters after trimming. |
| `photo_url` | An `https://` link of up to 2048 characters, or `null` to clear it. A link for now; uploads arrive with file storage (SCRUM-19, SCRUM-20). |
| `timezone` | Must be an IANA name known to `zoneinfo.available_timezones()`, else 422. Unlike the invite flow, it never falls back to UTC. |
| `contact_preference` | `email`, `discord` or `phone`. Default `email`. |
| `contact_detail` | Up to 200 characters (a handle or number), or `null`. |
| `email_assignments`, `email_reminders`, `email_digest` | Booleans, all on by default. Assignments covers work assigned, reviewed and approved; reminders covers due soon; digest is the weekly summary. |
| `public_byline_consent` | Boolean, off by default. Turning it on stamps `public_byline_consent_at` with the current UTC time. Turning it off clears the flag and keeps the stamp as history. Sending `true` again does not move the stamp. |

Fields left out of a PATCH are not touched, and the ones above cannot be sent
as `null` except `photo_url` and `contact_detail`. Unknown fields are ignored,
`email` included: changing an email needs the verification flow (SCRUM-12).
Account emails (sign-in, password reset, invites, verification) have no
setting here and always send.

The consent columns are the ones on `membership` that the public byline page
(P16, SCRUM-37) reads, which is what keeps the two controls in sync.

## Email verification (SCRUM-12)

A verification link confirms a person owns their email address. Like
invites, the URL carries a random token and `email_verification` stores only
its SHA-256. Opening `/verify/{token}` (P04) lands on one of three screens.

| Endpoint | Result |
| --- | --- |
| `POST /verify/{token}` | Public. Uses the link and returns `{"state", "email", "verified_at"}`. `state` is `verified` (the link worked; `person.email_verified_at` is stamped), `expired` (24 hours have passed, or the email has changed since; `verified_at` is null) or `already_verified` (used before, or the address was confirmed another way). 404 if no such link. A POST so a mail scanner that prefetches the link cannot use it up. |
| `POST /verify/{token}/resend` | Public. After an expired link, sends a new one to the person's current email and returns 202 `{"email"}`. Only one live link at a time, so repeat clicks send nothing new. 409 when the link is not in the expired state. |

Links last 24 hours (`verifications.VERIFICATION_LIFETIME`) and work once:
`used_at` is a conditional update, as with invites.

There is no email service yet. `verifications.deliver` logs the link
(`SITE_URL` sets its origin, default `http://localhost:5173`); the
notifications work replaces it with a real send. To test the three screens,
make a link for an existing person:

```bash
python scripts/create_verification.py you@example.com            # confirmed, then already verified
python scripts/create_verification.py you@example.com --expired  # expired
```

## Tests

```bash
python -m pytest
```

Most tests need no database. The ledger tests in `tests/test_ledger.py`
check a Postgres trigger, so they run only when `DATABASE_URL` points at a
database that has had `alembic upgrade head` applied, and skip otherwise.
CI has no Postgres yet, so they skip there and run locally.

## Code style

Ruff is the single source of truth, configured in `pyproject.toml`. Line
length is 100. The rule families and what each one enforces:

| Rules | What they enforce |
| --- | --- |
| `E`, `W` | PEP 8 layout and whitespace |
| `F` | No unused imports or undefined names |
| `I` | Import order: standard library, third party, then our own modules |
| `N` | `snake_case` functions and variables, `PascalCase` classes |
| `ANN` | A type hint on every function signature |

Install the dev tools once, then run both before opening a pull request:

```bash
pip install -r requirements-dev.txt
ruff check .     # lint
ruff format .    # format in place
```

Both must pass. If a rule feels wrong, change it in `pyproject.toml` in its
own pull request rather than adding `# noqa` to the code.

## Migrations

Alembic takes the database URL from `config.py`, never from `alembic.ini`,
so `DATABASE_URL` must be set for every Alembic command.

```bash
alembic upgrade head                               # apply migrations
alembic revision --autogenerate -m "describe it"   # after changing models
```

Autogenerate only sees models that are imported by the time `alembic/env.py`
runs, so import new model modules there as they are added.

## Layout

| Path | Purpose |
| --- | --- |
| `main.py` | FastAPI app and routes |
| `config.py` | Settings loaded from the environment with pydantic-settings |
| `db.py` | SQLAlchemy engine, session factory and declarative `Base` |
| `alembic.ini`, `alembic/` | Migration config and scripts |
| `scripts/create_invite.py` | Dev helper: make an invite link (goes away with SCRUM-39/42) |
| `tests/` | pytest suite |
| `requirements.txt` | Pinned dependencies |
| `requirements-dev.txt` | Dev tools on top of the runtime pins (ruff) |
| `pyproject.toml` | Ruff configuration, the code style rules |
