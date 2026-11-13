# Byline

A web dashboard for assigning, submitting, and reviewing intern work. Approved submissions earn points and are credited on the intern's record of completed work.

Team Overclock · CSC 190/191 Senior Project, Sacramento State, Fall 2026 to Spring 2027
Client: The Emerson Empire · Advisor: Kenneth Elliott

> **Status:** Sprint 2 complete. People can join by invite (P05), sign in (P01), verify their email (P04), reset a forgotten password (P02, P03), see their first-run home (P11) and My Work (P10), and edit their profile (P18). Sprint 1 set up the front end, API, database schema, design system, CI and staging. Sprint 3 (Nov 2 to 15) builds the submission flow: the assignment page with its criteria checklist, handing in text, a file or a link, recovering a failed upload, resubmitting after feedback, the submission history page, and late policies. It also moves the app onto the client's own theme.

## Overview

The client's founder currently assigns, tracks, and reviews all intern work by hand in an Excel spreadsheet. This project replaces it: supervisors post assignments, interns submit work in one place, reviewers approve or request changes, and approved work adds to a points ledger and a page listing the intern's approved work.

## Features

**Must-have:** sign-in with roles (member, supervisor, admin), assignments, intern dashboard, submissions, review with feedback, points ledger and approved-work page, notifications, hosted deployment.

**CSC 191:** AI review assistant that drafts a score and feedback for the reviewer. It never approves work or awards points.

**Nice-to-have:** Excel import, GitHub/Discord/Slack/calendar integrations, client access, analytics.

## Tech stack

| Layer | Choice |
| --- | --- |
| Front end | React 19, TypeScript, Vite, Tailwind CSS 3, React Router |
| API | Python 3.13, FastAPI, SQLAlchemy 2, Alembic, psycopg 3 |
| Database | PostgreSQL 16 |
| Quality | ruff (Python), ESLint with the Airbnb config and Prettier (TypeScript), pre-commit hooks, pytest, Vitest |
| CI | GitHub Actions: pytest, ruff, vitest and eslint on every pull request |
| Hosting | Render: static site, web service and managed Postgres, declared in `render.yaml` |
| Local | Docker Compose |

## Architecture

Two deployable pieces and a database. The React app in `web/` is a single-page application that talks to the FastAPI service in `api/` over JSON. The API owns the schema: tables defined as SQLAlchemy models and created by Alembic migrations, never by hand. The entity-relationship diagram and the decisions behind it are in [`docs/erd.md`](docs/erd.md); the points ledger is append-only, so a correction is a new reversing row rather than an edit.

The design system lives in `web/src/styles/tokens.css` (colour, type and spacing as CSS variables with light and dark values) and `web/src/components/ui/` (Button, Input, Select, Card, Badge, Dialog, Table). The `/tokens` route renders all of it in both themes.

| Path | What it holds |
| --- | --- |
| `web/` | React front end, with its own README |
| `api/` | FastAPI service, models, migrations and tests, with its own README |
| `docs/` | ERD and design notes |
| `docker-compose.yml` | Local stack: web, api and Postgres 16 |
| `render.yaml` | Hosted stack on Render |
| `.github/workflows/ci.yml` | The four CI checks |

## Getting started

You need [Docker Desktop](https://www.docker.com/products/docker-desktop)
and [Git](https://git-scm.com). Nothing else.

1. Clone the repository and go into it:
   `git clone https://github.com/dschell3/Byline.git && cd Byline`
2. Create your local settings file from the template:
   `cp .env.example .env` (the defaults work as they are)
3. Start everything:
   `docker compose up`
   The first run takes a few minutes while it downloads and builds.
4. Open http://localhost:5173 for the app and
   http://localhost:8000/docs for the API.

`Ctrl+C` stops it. `docker compose down -v` wipes the database for a fresh
start. To run the API or front end without Docker, see `api/README.md` and
`web/README.md`.

## Contributing

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) for naming, branching, commits and review, and [`GIT-GUIDE.md`](GIT-GUIDE.md) for the day-to-day Git workflow in VS Code. The short version:

- Branch from `main` as `yourname/scrum-NN-short-description`.
- Prefix every commit message with the Jira key, for example `SCRUM-61 feat(api): ...`.
- Install the hooks once per clone: `pip install pre-commit && pre-commit install`.
- Every change goes through a pull request with one approval and all four CI checks green. Nothing is pushed to `main` directly.

## Testing

```bash
cd api && python -m pytest          # API
cd web && npm test                  # front end
```

Both run in CI on every pull request. API tests that need a database run only when `DATABASE_URL` points at a Postgres with the migrations applied, and skip otherwise.

## Deployment

- Front end: https://byline-web-eh4k.onrender.com/
- API health check: https://byline-api-mn90.onrender.com/health

Every merge to `main` deploys both services automatically; the stack is declared in `render.yaml`. These are the current services; the API takes under a minute to wake after being idle.

<!-- SCRUM-75 step 2: Jang swaps in the client-account URLs and describes the account here. -->

## Team

| Name | Role | GitHub |
| --- | --- | --- |
| Jangbahadar Singh | Team lead, CI and deployment | [Jsingh651](https://github.com/Jsingh651) |
| Darren Schell | Backend and AI | [dschell3](https://github.com/dschell3) |
| Arav Parmar | Front end and AI | [arav0328](https://github.com/arav0328) |
| Shamrit Phagura | Design system and UI components | [0x5h4mkp](https://github.com/0x5h4mkp) |
| Aaditya Kumar | Database and backend | [aadityakr2002](https://github.com/aadityakr2002) |
| Ibrahim Al-Jawi | Full-stack features | [cakey1](https://github.com/cakey1) |

## Links

[Jira](https://csus-team-notchuds.atlassian.net/jira/software/projects/SCRUM/boards/1) · [Figma](https://www.figma.com/design/iJjtNcHW10AKhJZD71hQFN/Byline-UI-Mockup--CSC-190-?node-id=298-2&t=XYNGRGfhRtMUm7Uy-0) · [Project website](https://byline-web-eh4k.onrender.com/)

## License

TBD
