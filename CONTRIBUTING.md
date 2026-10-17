# Contributing to Byline

How we name things, branch, commit and review. If a pull request argues about style, point at this file.

## One-time setup

1. Clone the repo and follow `api/README.md` and `web/README.md` to install each side.
2. Install the pre-commit hooks (once per clone):

   ```bash
   pip install pre-commit        # or: brew install pre-commit
   pre-commit install
   cd web && npm install && cd ..
   ```

From then on, every `git commit` runs the hooks below. A commit that fails a hook is blocked.
Fix what it reports, `git add` again, and commit again.

| Hook | Runs on | What it checks |
| --- | --- | --- |
| ruff | `api/**` | Python lint and import order, using `api/pyproject.toml` |
| eslint | `web/**/*.{js,jsx,ts,tsx}` | Airbnb style for React + TypeScript, zero warnings |
| prettier | `web/**` | Formatting |

Useful commands from `web/`: `npm run lint`, `npm run format` (fixes formatting), `npm test`.
From `api/`: `ruff check .` and `ruff check . --fix`.

## Naming rules

| Where | Style | Example |
| --- | --- | --- |
| TypeScript variables and functions | camelCase | `dueDate`, `fetchAssignments()` |
| React components and their files | PascalCase | `AssignmentCard`, `AssignmentCard.tsx` |
| TypeScript types and interfaces | PascalCase | `Submission`, `ReviewDecision` |
| Python variables, functions, modules | snake_case | `due_date`, `get_settings()`, `points_ledger.py` |
| Python classes | PascalCase | `Settings`, `Membership` |
| Database tables and columns | snake_case, singular table names | `points_ledger`, `created_at` |
| Constants (both sides) | UPPER_SNAKE_CASE | `MAX_UPLOAD_MB` |

## Branches

Branch from the latest `main`, one branch per Jira card:

```
yourname/scrum-NN-short-name
```

Example: `arav/scrum-64-lint-hooks`. Start each card on a fresh branch instead of reusing an old one.

## Commit messages

Start every commit with the Jira key so Jira links it, then a type and a short summary:

```
SCRUM-NN type(scope): what changed
```

- **type**: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`
- **scope**: `api`, `web`, `docs`, `ci` (optional)
- Summary in the imperative, under about 72 characters, no full stop.

Examples:

```
SCRUM-61 feat(api): FastAPI app with GET /health
SCRUM-64 chore(web): ESLint Airbnb config and Prettier
```

## Pull requests

- Open the PR into `main` as soon as it runs, even if unfinished. Put the Jira key in the title.
- Drop the link in Discord and name a reviewer.
- Direct pushes to `main` are blocked. One approval is required to merge.
- During review, push fixes as **new commits**. Don't amend or force-push, so reviewers can see what changed.
- Small PRs merged often beat one big one at the end of the sprint.

## Stuck or blocked

Blocked on someone else's card? Say so in Discord with the card number. Stuck for more than 30 minutes? Ask the channel.
