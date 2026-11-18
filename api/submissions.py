"""A submission's history: every version, each review with its scores, the comments (SCRUM-22).

``GET /submissions/{id}`` serves P14. The id names one version; the answer
carries every version of the same member's work on the same assignment,
oldest first, each with its reviews and its comment thread in the order they
happened, so the page reads top to bottom as a history.

Who may look: the member who made the submission, or a supervisor or admin
in the same organization, the same rule as ``/members/{id}/work``
(``work.can_view``). Anyone else, and any id that does not exist, gets the
same 403, so the answer never says which ids are real.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

import work
from models import (
    AssessmentCriterion,
    Assignment,
    Membership,
    Person,
    Review,
    ReviewCriterionScore,
    StoredFile,
    Submission,
    SubmissionComment,
)

MAX_COMMENT_LENGTH = 4000


class ScoreOut(BaseModel):
    criterion_id: int
    position: int
    text: str
    max_points: int
    score: int
    note: str | None


class ReviewOut(BaseModel):
    id: int
    decision: str
    reason: str | None
    is_final: bool
    actor_type: str
    # The reviewer's name when a person; null for the system (the CSC 191 assistant).
    actor_name: str | None
    created_at: datetime
    scores: list[ScoreOut]


class CommentOut(BaseModel):
    id: int
    author_membership_id: int
    author_name: str
    parent_comment_id: int | None
    body: str
    created_at: datetime


class FileOut(BaseModel):
    """A file on a version. The id is what GET /files/{id} takes."""

    id: int
    name: str
    content_type: str
    size_bytes: int


class VersionOut(BaseModel):
    id: int
    version: int
    status: str
    submitted_at: datetime
    file_keys: list[str]
    # The rows behind file_keys, in order. A key with no row (older seed data) is left out.
    files: list[FileOut]
    submission_kind: str | None
    content: str | None
    reviews: list[ReviewOut]
    comments: list[CommentOut]


class AssignmentOut(BaseModel):
    id: int
    title: str
    points_value: int
    due_at: datetime | None


class MemberOut(BaseModel):
    membership_id: int
    full_name: str


class SubmissionDetail(BaseModel):
    # The version that was asked for; ``versions`` holds all of them, oldest first.
    id: int
    assignment: AssignmentOut
    member: MemberOut
    versions: list[VersionOut]


class CommentIn(BaseModel):
    body: str = Field(min_length=1, max_length=MAX_COMMENT_LENGTH)
    parent_comment_id: int | None = None

    @field_validator("body")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("A comment needs some text")
        return value.strip()


def _name_of(db: Session, membership_id: int | None) -> str | None:
    if membership_id is None:
        return None
    return db.scalar(
        select(Person.full_name)
        .join(Membership, Membership.person_id == Person.id)
        .where(Membership.id == membership_id)
    )


def _scores(db: Session, review_id: int) -> list[ScoreOut]:
    rows = db.execute(
        select(ReviewCriterionScore, AssessmentCriterion)
        .join(AssessmentCriterion, AssessmentCriterion.id == ReviewCriterionScore.criterion_id)
        .where(ReviewCriterionScore.review_id == review_id)
        .order_by(AssessmentCriterion.position)
    ).all()
    return [
        ScoreOut(
            criterion_id=criterion.id,
            position=criterion.position,
            text=criterion.text,
            max_points=criterion.max_points,
            score=score.score,
            note=score.note,
        )
        for score, criterion in rows
    ]


def _reviews(db: Session, submission_id: int, include_drafts: bool) -> list[ReviewOut]:
    query = select(Review).where(Review.submission_id == submission_id)
    if not include_drafts:
        query = query.where(Review.is_final.is_(True))
    reviews = db.scalars(query.order_by(Review.created_at, Review.id)).all()
    return [
        ReviewOut(
            id=review.id,
            decision=review.decision,
            reason=review.reason,
            is_final=review.is_final,
            actor_type=review.actor_type,
            actor_name=_name_of(db, review.actor_id) if review.actor_type == "person" else None,
            created_at=review.created_at,
            scores=_scores(db, review.id),
        )
        for review in reviews
    ]


def _files(db: Session, keys: list[str]) -> list[FileOut]:
    if not keys:
        return []
    by_key = {
        row.key: row for row in db.scalars(select(StoredFile).where(StoredFile.key.in_(keys)))
    }
    return [
        FileOut(id=row.id, name=row.name, content_type=row.content_type, size_bytes=row.size_bytes)
        for key in keys
        if (row := by_key.get(key)) is not None
    ]


def _comments(db: Session, submission_id: int) -> list[CommentOut]:
    rows = db.execute(
        select(SubmissionComment, Person.full_name)
        .join(Membership, Membership.id == SubmissionComment.author_membership_id)
        .join(Person, Person.id == Membership.person_id)
        .where(SubmissionComment.submission_id == submission_id)
        .order_by(SubmissionComment.created_at, SubmissionComment.id)
    ).all()
    return [
        CommentOut(
            id=comment.id,
            author_membership_id=comment.author_membership_id,
            author_name=name,
            parent_comment_id=comment.parent_comment_id,
            body=comment.body,
            created_at=comment.created_at,
        )
        for comment, name in rows
    ]


def history(db: Session, submission: Submission, viewer_is_owner: bool) -> SubmissionDetail:
    """Everything P14 shows for the work ``submission`` belongs to.

    The member who made it sees final reviews only. A draft (``is_final = false``)
    is the assistant's until a supervisor acts on it (docs/erd.md), so only
    supervisors and admins see drafts.
    """
    assignment = db.get(Assignment, submission.assignment_id)
    versions = db.scalars(
        select(Submission)
        .where(
            Submission.assignment_id == submission.assignment_id,
            Submission.membership_id == submission.membership_id,
        )
        .order_by(Submission.version)
    ).all()
    return SubmissionDetail(
        id=submission.id,
        assignment=AssignmentOut(
            id=assignment.id,
            title=assignment.title,
            points_value=assignment.points_value,
            due_at=assignment.due_at,
        ),
        member=MemberOut(
            membership_id=submission.membership_id,
            full_name=_name_of(db, submission.membership_id) or "A member",
        ),
        versions=[
            VersionOut(
                id=version.id,
                version=version.version,
                status=version.status,
                submitted_at=version.submitted_at,
                file_keys=list(version.file_keys or []),
                files=_files(db, list(version.file_keys or [])),
                submission_kind=version.submission_kind,
                content=version.content,
                reviews=_reviews(db, version.id, include_drafts=not viewer_is_owner),
                comments=_comments(db, version.id),
            )
            for version in versions
        ],
    )


def commenter(db: Session, caller: Person, submission: Submission) -> Membership | None:
    """The membership a comment is written under: the member's own, else a supervisor's or admin's
    in the same organization."""
    owner = db.get(Membership, submission.membership_id)
    if owner is None:
        return None
    if owner.person_id == caller.id:
        return owner
    return work.supervising_membership(db, caller, owner.organization_id)


def add_comment(
    db: Session, submission: Submission, author: Membership, body: str, parent_id: int | None
) -> SubmissionComment | None:
    """Write a comment, or None when ``parent_id`` is not a top-level comment on this submission."""
    if parent_id is not None:
        parent = db.get(SubmissionComment, parent_id)
        if (
            parent is None
            or parent.submission_id != submission.id
            or parent.parent_comment_id is not None
        ):
            return None
    comment = SubmissionComment(
        submission_id=submission.id,
        author_membership_id=author.id,
        parent_comment_id=parent_id,
        body=body,
    )
    db.add(comment)
    db.flush()
    return comment


def previous_feedback(db: Session, assignment_id: int, membership_id: int) -> list[ReviewOut]:
    """The final reviews, with scores, on the member's latest version (SCRUM-21).

    This is what the resubmit screen shows above the form. AI drafts are left
    out; an empty list means there is nothing to show yet.
    """
    latest = db.scalar(
        select(Submission)
        .where(
            Submission.assignment_id == assignment_id,
            Submission.membership_id == membership_id,
        )
        .order_by(Submission.version.desc())
        .limit(1)
    )
    if latest is None:
        return []
    return _reviews(db, latest.id, include_drafts=False)
