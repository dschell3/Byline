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

## Tests

```bash
python -m pytest
```

The current tests need no database.

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
