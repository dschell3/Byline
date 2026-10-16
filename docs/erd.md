# Byline schema (SCRUM-67)

The twelve tables from SCRUM-5, their relationships, foreign keys and cardinality.
Picture: [`erd.png`](erd.png). The same diagram as Mermaid is at the bottom, so GitHub renders it too.

Database: Postgres. Models and the first Alembic migration come in SCRUM-68.

## Rules that apply to every table

- Every table has `id` as a `bigint` primary key.
- Every timestamp is `TIMESTAMPTZ`, stored in UTC. No naive datetimes.
- Foreign keys and `NOT NULL` are declared in the database, not left to the app.
- The schema is created by an Alembic migration, never by hand.

## Tables

| # | Table | What it holds | Key relationships |
|---|---|---|---|
| 1 | organization | The client company. | Parent of membership, team, cohort, track, assignment, audit_log |
| 2 | person | A human who can sign in. Email is unique. | One person has many memberships |
| 3 | membership | A person's place in one organization: their `role` (member, supervisor, admin), team, cohort, track and `ai_consent`. | person 1–many, organization 1–many. Unique on (person_id, organization_id) |
| 4 | team | A team inside the organization. | organization 1–many. A membership belongs to 0 or 1 team |
| 5 | cohort | A group of interns that start together. | organization 1–many. A membership belongs to 0 or 1 cohort |
| 6 | track | A path of work, e.g. marketing or engineering. | organization 1–many. A membership belongs to 0 or 1 track |
| 7 | assignment | Work a supervisor posts. Can target a team, cohort and/or track. | organization 1–many, created by a membership |
| 8 | submission | An intern's hand-in. A resubmit is a new row with `version + 1`. | assignment 1–many, membership 1–many. Unique on (assignment_id, membership_id, version) |
| 9 | review | A decision on a submission (approved or changes requested) with feedback. | submission 1–many. Actor is a person or the system (see below) |
| 10 | points_ledger | Points earned. Append-only. | membership 1–many, submission 0..1–many, reverses another ledger row 0..1 |
| 11 | notification | An alert for one membership. | membership 1–many |
| 12 | audit_log | Who did what, when, to which record. | organization 1–many. Actor is a person or the system |

## Decisions baked in

**Actor can be a person or the system** (for the CSC 191 AI assistant, SCRUM-52).
`review`, `points_ledger` and `audit_log` use `actor_type` (`person` or `system`) plus `actor_id`, not a hard FK to person.
When `actor_type = person`, `actor_id` is a membership id. When it is `system`, `actor_id` is null.
The assistant can only write draft reviews (`is_final = false`). Only a person can write a final review.

**AI consent.** `membership.ai_consent` is `NOT NULL DEFAULT false`. SCRUM-52 checks it before sending anything to the model.

**Points ledger is append-only.** Rows are never updated or deleted. A correction writes a new reversing row
(negative `amount`, `reverses_entry_id` pointing at the original). A member's total is `SUM(amount)`.
SCRUM-69 enforces this and tests it.

**Roles live on membership, not person**, so one person could be a member in one organization and a supervisor in another.

## Still open

- Column details on assignment, submission and review wait for Lyric's weekly tracking-sheet headers. They do not change the relationships above.
- Can a membership be in more than one team, cohort or track? This draft says no (one of each). If yes, we add join tables.

## Diagram source

```mermaid
erDiagram
    organization ||--o{ membership : "has"
    person ||--o{ membership : "joins orgs via"
    organization ||--o{ team : "has"
    organization ||--o{ cohort : "has"
    organization ||--o{ track : "has"
    team |o--o{ membership : "groups"
    cohort |o--o{ membership : "groups"
    track |o--o{ membership : "groups"
    organization ||--o{ assignment : "owns"
    membership ||--o{ assignment : "creates (supervisor)"
    team |o--o{ assignment : "targets"
    cohort |o--o{ assignment : "targets"
    track |o--o{ assignment : "targets"
    assignment ||--o{ submission : "receives"
    membership ||--o{ submission : "submits (intern)"
    submission ||--o{ review : "gets"
    membership ||--o{ points_ledger : "earns"
    submission |o--o{ points_ledger : "awards"
    points_ledger |o--o| points_ledger : "reverses"
    membership ||--o{ notification : "receives"
    organization ||--o{ audit_log : "records"

    organization {
        bigint id PK
        text name "NOT NULL"
        text slug "NOT NULL, UNIQUE"
        timestamptz created_at "NOT NULL"
    }
    person {
        bigint id PK
        text email "NOT NULL, UNIQUE"
        text full_name "NOT NULL"
        timestamptz created_at "NOT NULL"
    }
    membership {
        bigint id PK
        bigint person_id FK "NOT NULL"
        bigint organization_id FK "NOT NULL"
        text role "NOT NULL: member | supervisor | admin"
        bigint team_id FK "nullable"
        bigint cohort_id FK "nullable"
        bigint track_id FK "nullable"
        boolean ai_consent "NOT NULL, default false"
        boolean is_active "NOT NULL, default true"
        timestamptz created_at "NOT NULL"
    }
    team {
        bigint id PK
        bigint organization_id FK "NOT NULL"
        text name "NOT NULL"
        timestamptz created_at "NOT NULL"
    }
    cohort {
        bigint id PK
        bigint organization_id FK "NOT NULL"
        text name "NOT NULL"
        date starts_on
        date ends_on
        timestamptz created_at "NOT NULL"
    }
    track {
        bigint id PK
        bigint organization_id FK "NOT NULL"
        text name "NOT NULL"
        timestamptz created_at "NOT NULL"
    }
    assignment {
        bigint id PK
        bigint organization_id FK "NOT NULL"
        bigint created_by_membership_id FK "NOT NULL"
        bigint team_id FK "nullable"
        bigint cohort_id FK "nullable"
        bigint track_id FK "nullable"
        text title "NOT NULL"
        int points_value "NOT NULL"
        timestamptz due_at
        timestamptz created_at "NOT NULL"
    }
    submission {
        bigint id PK
        bigint assignment_id FK "NOT NULL"
        bigint membership_id FK "NOT NULL"
        int version "NOT NULL"
        text status "NOT NULL"
        timestamptz submitted_at "NOT NULL"
    }
    review {
        bigint id PK
        bigint submission_id FK "NOT NULL"
        text actor_type "NOT NULL: person | system"
        bigint actor_id "membership id when person"
        text decision "NOT NULL"
        boolean is_final "NOT NULL, human only"
        timestamptz created_at "NOT NULL"
    }
    points_ledger {
        bigint id PK
        bigint membership_id FK "NOT NULL"
        bigint submission_id FK "nullable"
        bigint reverses_entry_id FK "nullable, self"
        int amount "NOT NULL"
        text reason "NOT NULL"
        text actor_type "NOT NULL: person | system"
        bigint actor_id "membership id when person"
        timestamptz created_at "NOT NULL"
    }
    notification {
        bigint id PK
        bigint membership_id FK "NOT NULL"
        text type "NOT NULL"
        text message "NOT NULL"
        timestamptz read_at "nullable"
        timestamptz created_at "NOT NULL"
    }
    audit_log {
        bigint id PK
        bigint organization_id FK "NOT NULL"
        text actor_type "NOT NULL: person | system"
        bigint actor_id
        text action "NOT NULL"
        text entity_type "NOT NULL"
        bigint entity_id "NOT NULL"
        jsonb details
        timestamptz created_at "NOT NULL"
    }
```
