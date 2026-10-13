# Byline ERD and table list (SCRUM-67)

Draft for the team review. Database: Postgres (SQLAlchemy models in `api/`, built by SCRUM-68).
Every table has `id` (primary key) and `created_at`. Arrows below read "one to many".

```mermaid
erDiagram
    organizations ||--o{ users : has
    organizations ||--o{ cohorts : has
    organizations ||--o{ assignments : owns
    cohorts ||--o{ cohort_members : contains
    users ||--o{ cohort_members : joins
    users ||--o{ assignments : "creates (supervisor)"
    cohorts |o--o{ assignments : "targeted at"
    assignments ||--o{ assignment_recipients : "sent to"
    users ||--o{ assignment_recipients : receives
    assignments ||--o{ submissions : gets
    users ||--o{ submissions : "submits (member)"
    submissions ||--o{ submission_files : attaches
    submissions ||--o{ reviews : gets
    users ||--o{ reviews : "writes (reviewer)"
    submissions ||--o{ ai_review_drafts : "drafted for"
    users ||--o{ points_ledger : earns
    submissions ||--o| points_ledger : awards
    users ||--o{ notifications : receives

    organizations {
        int id PK
        string name
        string slug "used in public byline URL"
        timestamp created_at
    }
    users {
        int id PK
        int organization_id FK
        string email "unique"
        string full_name
        string role "member | supervisor | admin"
        string password_hash
        string public_slug "nullable, public byline page"
        bool is_active
        timestamp created_at
    }
    cohorts {
        int id PK
        int organization_id FK
        string name
        date starts_on
        date ends_on
        timestamp created_at
    }
    cohort_members {
        int id PK
        int cohort_id FK
        int user_id FK
        timestamp created_at
    }
    assignments {
        int id PK
        int organization_id FK
        int created_by FK "users.id"
        int cohort_id FK "nullable"
        string title
        text description
        int points_value
        timestamp due_at
        string status "draft | published | closed"
        timestamp created_at
    }
    assignment_recipients {
        int id PK
        int assignment_id FK
        int user_id FK
        timestamp created_at
    }
    submissions {
        int id PK
        int assignment_id FK
        int member_id FK "users.id"
        int version "1, 2, 3 on resubmit"
        text body
        string link_url "nullable"
        string status "submitted | changes_requested | approved"
        timestamp submitted_at
        timestamp created_at
    }
    submission_files {
        int id PK
        int submission_id FK
        string file_name
        string storage_url
        timestamp created_at
    }
    reviews {
        int id PK
        int submission_id FK
        int reviewer_id FK "users.id"
        string decision "approved | changes_requested"
        text feedback
        int score "nullable"
        timestamp created_at
    }
    ai_review_drafts {
        int id PK
        int submission_id FK
        int suggested_score
        text suggested_feedback
        string model_name
        timestamp created_at
    }
    points_ledger {
        int id PK
        int user_id FK
        int submission_id FK "nullable for manual adjustments"
        int amount "can be negative for corrections"
        string reason
        int created_by FK "users.id"
        timestamp created_at
    }
    notifications {
        int id PK
        int user_id FK
        string type "assigned | reviewed | reminder"
        text message
        string link_url
        timestamp read_at "nullable"
        timestamp created_at
    }
```

## The 12 tables

| # | Table | What it stores |
|---|---|---|
| 1 | organizations | The client company (The Emerson Empire). Lets us support more orgs later. |
| 2 | users | Everyone who signs in. `role` is member, supervisor or admin. |
| 3 | cohorts | A group of interns, e.g. "Fall 2026 interns". |
| 4 | cohort_members | Which users are in which cohort. |
| 5 | assignments | Work a supervisor posts: title, instructions, due date, points. |
| 6 | assignment_recipients | Which members an assignment was sent to. |
| 7 | submissions | A member's hand-in. A resubmit is a new row with `version + 1`. |
| 8 | submission_files | Files attached to a submission. |
| 9 | reviews | Reviewer decision (approve or request changes) plus feedback. |
| 10 | ai_review_drafts | CSC 191 AI assistant's suggested score and feedback. Never approves or awards points. |
| 11 | points_ledger | Append-only: rows are only added, never edited or deleted (SCRUM-69). A member's total is `SUM(amount)`. |
| 12 | notifications | In-app alerts and the source for email reminders. |

**No table needed for:** the approved-work page (it's `submissions` where status = approved) or points totals (it's the ledger sum).

## Rules worth agreeing on

- A ledger row is written only when a review approves a submission. One approved submission gives one ledger row.
- Corrections are new ledger rows with a negative `amount`. Never update old rows.
- Only one `approved` submission per member per assignment.
- Deleting users: set `is_active = false` instead, so the history stays intact.

## Open questions for the review

1. Sign-in: our own passwords (`password_hash`) or Google / SSO? If SSO, swap `password_hash` for `auth_provider` + `auth_subject`.
2. Do assignments go to a whole cohort, to picked members, or both? (This draft supports both.)
3. Can a reviewer be any supervisor, or one assigned per submission?
4. Where do uploaded files live (S3, Supabase storage, Render disk)?
