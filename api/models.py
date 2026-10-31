"""SQLAlchemy models for the Byline tables (SCRUM-68; auth_session SCRUM-13; invite SCRUM-11).

The source of truth is docs/erd.md. Every table follows its rules:
bigint ids, TIMESTAMPTZ everywhere, foreign keys and NOT NULL declared here
so the database enforces them, not the app.
"""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db import Base

# Shared column shapes, so every table spells them the same way.
# Timestamps are timezone-aware (TIMESTAMPTZ in Postgres) and default to now() in the database.
TIMESTAMPTZ = DateTime(timezone=True)
ACTOR_TYPES = "actor_type IN ('person', 'system')"


class Organization(Base):
    """The client company. Parent of nearly everything else."""

    __tablename__ = "organization"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )


class Person(Base):
    """Someone who can sign in. Roles live on membership, not here."""

    __tablename__ = "person"
    __table_args__ = (
        CheckConstraint(
            "contact_preference IN ('email', 'discord', 'phone')",
            name="ck_person_contact_preference",
        ),
    )

    # SQLite only auto-numbers a plain INTEGER primary key; Postgres keeps bigint.
    # Rows are created at runtime by the invite flow (SCRUM-11), so tests need this.
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    # IANA name such as America/Los_Angeles. Drives every due date the person sees.
    timezone: Mapped[str] = mapped_column(Text, nullable=False, server_default="UTC")
    email_unreachable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    email_bounced_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ)
    # Profile (SCRUM-17). The photo is a URL until file storage (R2) arrives.
    photo_url: Mapped[str | None] = mapped_column(Text)
    contact_preference: Mapped[str] = mapped_column(Text, nullable=False, server_default="email")
    contact_detail: Mapped[str | None] = mapped_column(Text)
    email_assignments: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    email_reminders: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    email_digest: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )


class Team(Base):
    """What a supervisor runs."""

    __tablename__ = "team"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organization.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )


class Cohort(Base):
    """The intake group an intern sits in."""

    __tablename__ = "cohort"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organization.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    starts_on: Mapped[date | None] = mapped_column(Date)
    ends_on: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )


class Track(Base):
    """One of the five tracks, with its onboarding pack."""

    __tablename__ = "track"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organization.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    onboarding_pack_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )


class Membership(Base):
    """A person's place in one organization: role, team, cohort, track, consents."""

    __tablename__ = "membership"
    __table_args__ = (
        UniqueConstraint("person_id", "organization_id", name="uq_membership_person_org"),
        CheckConstraint("role IN ('member', 'supervisor', 'admin')", name="ck_membership_role"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    person_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("person.id"), nullable=False)
    organization_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organization.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    team_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("team.id"))
    cohort_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("cohort.id"))
    track_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("track.id"))
    ai_consent: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    public_slug: Mapped[str | None] = mapped_column(Text, unique=True)
    public_byline_consent: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    public_byline_consent_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )


class Assignment(Base):
    """Work a supervisor posts. Targets a team, cohort, track and/or picked members."""

    __tablename__ = "assignment"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organization.id"), nullable=False
    )
    created_by_membership_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("membership.id"), nullable=False
    )
    team_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("team.id"))
    cohort_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("cohort.id"))
    track_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("track.id"))
    # Picked members. Postgres can't put a FK inside an array; see the ERD decision.
    recipient_membership_ids: Mapped[list[int] | None] = mapped_column(ARRAY(BigInteger))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    points_value: Mapped[int] = mapped_column(Integer, nullable=False)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    late_policy: Mapped[str] = mapped_column(Text, nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )


class Submission(Base):
    """An intern's hand-in. A resubmit is a new row with version + 1."""

    __tablename__ = "submission"
    __table_args__ = (
        UniqueConstraint("assignment_id", "membership_id", "version", name="uq_submission_version"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    assignment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("assignment.id"), nullable=False
    )
    membership_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("membership.id"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    # Cloudflare R2 object keys.
    file_keys: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    # Cached from the latest final review. review is the source of truth.
    status: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )


class Review(Base):
    """Approve or request changes. AI drafts have is_final = false; only a person writes a final."""

    __tablename__ = "review"
    __table_args__ = (CheckConstraint(ACTOR_TYPES, name="ck_review_actor_type"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    submission_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("submission.id"), nullable=False
    )
    actor_type: Mapped[str] = mapped_column(Text, nullable=False)
    # Membership id when actor_type is person; null when it is system.
    actor_id: Mapped[int | None] = mapped_column(BigInteger)
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )


class PointsLedger(Base):
    """Points earned. Append-only: corrections are reversing rows (SCRUM-69 adds the trigger)."""

    __tablename__ = "points_ledger"
    __table_args__ = (CheckConstraint(ACTOR_TYPES, name="ck_points_ledger_actor_type"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    membership_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("membership.id"), nullable=False
    )
    submission_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("submission.id"))
    reverses_ledger_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("points_ledger.id")
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    actor_type: Mapped[str] = mapped_column(Text, nullable=False)
    actor_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )


class Notification(Base):
    """An alert for one membership."""

    __tablename__ = "notification"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    membership_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("membership.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )


class AuditLog(Base):
    """Who did what to which record, with before and after."""

    __tablename__ = "audit_log"
    __table_args__ = (CheckConstraint(ACTOR_TYPES, name="ck_audit_log_actor_type"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organization.id"), nullable=False
    )
    actor_type: Mapped[str] = mapped_column(Text, nullable=False)
    actor_id: Mapped[int | None] = mapped_column(BigInteger)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    target_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    before: Mapped[dict | None] = mapped_column(JSONB)
    after: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )


class AuthSession(Base):
    """A signed-in browser (SCRUM-13).

    The cookie carries a random token; only its SHA-256 is stored, so a leaked
    database row cannot be replayed as a session. Revoking sets ``revoked_at``
    rather than deleting, so sign-out is enforced server-side and auditable.
    """

    __tablename__ = "auth_session"

    # SQLite only auto-numbers a plain INTEGER primary key; Postgres keeps bigint.
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    person_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("person.id"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )
    revoked_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ)


class Invite(Base):
    """A link that lets one person join one organization (SCRUM-11).

    The URL carries a random token; only its SHA-256 is stored, as with
    ``auth_session``. Accepting creates the person and the membership in
    one step and stamps ``accepted_at``, so a link works exactly once.
    ``revoked_at`` lets an admin withdraw an invite before it is used
    (SCRUM-39). Expiry is decided by ``expires_at``, set when the row is
    created.
    """

    __tablename__ = "invite"
    __table_args__ = (
        CheckConstraint("role IN ('member', 'supervisor', 'admin')", name="ck_invite_role"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organization.id"), nullable=False
    )
    invited_by_membership_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("membership.id"), nullable=False
    )
    email: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False, server_default="member")
    team_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("team.id"))
    cohort_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("cohort.id"))
    track_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("track.id"))
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ)
    revoked_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )
