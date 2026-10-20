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

Sessions and cookies are added on the success path by SCRUM-13.

To get an account to try locally, with `DATABASE_URL` set and migrations
applied:

```bash
python scripts/create_person.py you@example.com "Your Name" 'a password'
```

That script is a dev helper only and goes away when the invite flow (SCRUM-11) lands.

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
| `tests/` | pytest suite |
| `requirements.txt` | Pinned dependencies |
| `requirements-dev.txt` | Dev tools on top of the runtime pins (ruff) |
| `pyproject.toml` | Ruff configuration, the code style rules |
