"""One assignment as the intern it was set for sees it (SCRUM-18, P12).

``GET /assignments/{id}`` answers the assignment page: the brief, the
assessment criteria as the checklist the work will be scored against, the
reference links and attachments, the late policy fields, and whether the
page should offer Submit (P13) or View submission (P14).

Who may look: only a member the assignment was targeted at, by the shared
``assignments.assigned_to`` rule that My Work uses. Anyone else, and any id
that does not exist, gets the same 403, so the answer never says which ids
are real.
"""

from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

import sessions
import work
from assignments import assigned_to
from late_policy import can_still_be_handed_in
from models import (
    AssessmentCriterion,
    Assignment,
    Cohort,
    Membership,
    Person,
    Submission,
    Track,
)


class CriterionOut(BaseModel):
    id: int
    position: int
    text: str
    detail: str | None
    max_points: int


class LinkOut(BaseModel):
    label: str
    url: str


class AttachmentOut(BaseModel):
    # The object key stays on the server until file storage can hand out downloads (SCRUM-19).
    name: str
    size_bytes: int | None


class AssignmentDetail(BaseModel):
    id: int
    title: str
    description: str | None
    set_by: str
    set_at: datetime
    due_at: datetime | None
    points: int
    is_mandatory: bool
    # One of the six My Work group keys, worked out by the same rule (work.status_of).
    status: str
    # Names of the track and cohort the assignment targets, when it targets one.
    track: str | None
    cohort: str | None
    criteria: list[CriterionOut]
    reference_links: list[LinkOut]
    attachments: list[AttachmentOut]
    # SCRUM-23: the web app turns these into the "Late policy" sentence.
    late_policy: str
    late_cutoff_hours: int | None
    # The member's latest submission, when there is one: P12 then links to P14.
    submission_id: int | None
    # False once the late policy has stopped taking hand-ins. Only meaningful with no submission.
    can_submit: bool


def membership_reached(db: Session, person: Person, assignment_id: int) -> Membership | None:
    """The caller's active membership that ``assignment_id`` was targeted at, if any."""
    memberships = db.scalars(
        select(Membership)
        .where(Membership.person_id == person.id, Membership.is_active.is_(True))
        .order_by(Membership.id)
    ).all()
    for member in memberships:
        reached = db.scalar(
            select(Assignment.id).where(Assignment.id == assignment_id, assigned_to(member))
        )
        if reached is not None:
            return member
    return None


def _links(assignment: Assignment) -> list[LinkOut]:
    """Only http(s) links leave the server, so a stored link can never run script in the page."""
    links = []
    for link in assignment.reference_links or []:
        url = str(link.get("url", "")).strip()
        if url.lower().startswith(("https://", "http://")):
            links.append(LinkOut(label=str(link.get("label") or url), url=url))
    return links


def _attachments(assignment: Assignment) -> list[AttachmentOut]:
    return [
        AttachmentOut(name=str(item["name"]), size_bytes=item.get("size_bytes"))
        for item in assignment.attachments or []
        if item.get("name")
    ]


def detail(
    db: Session, assignment: Assignment, member: Membership, at: datetime | None = None
) -> AssignmentDetail:
    """Everything P12 shows for ``assignment`` as it stands for ``member``."""
    at = at or sessions.now()
    latest = db.execute(
        select(Submission.id, Submission.status)
        .where(Submission.assignment_id == assignment.id, Submission.membership_id == member.id)
        .order_by(Submission.version.desc())
        .limit(1)
    ).first()
    set_by = db.scalar(
        select(Person.full_name)
        .join(Membership, Membership.person_id == Person.id)
        .where(Membership.id == assignment.created_by_membership_id)
    )
    criteria = db.scalars(
        select(AssessmentCriterion)
        .where(AssessmentCriterion.assignment_id == assignment.id)
        .order_by(AssessmentCriterion.position)
    ).all()
    status = work.status_of(
        work.Row(
            id=assignment.id,
            title=assignment.title,
            set_by=set_by or "Your supervisor",
            due_at=assignment.due_at,
            points=assignment.points_value,
            is_mandatory=assignment.is_mandatory,
            submission_status=latest.status if latest else None,
        ),
        at,
    )
    return AssignmentDetail(
        id=assignment.id,
        title=assignment.title,
        description=assignment.description,
        set_by=set_by or "Your supervisor",
        set_at=assignment.created_at,
        due_at=assignment.due_at,
        points=assignment.points_value,
        is_mandatory=assignment.is_mandatory,
        status=status,
        track=db.scalar(select(Track.name).where(Track.id == assignment.track_id)),
        cohort=db.scalar(select(Cohort.name).where(Cohort.id == assignment.cohort_id)),
        criteria=[
            CriterionOut(
                id=c.id, position=c.position, text=c.text, detail=c.detail, max_points=c.max_points
            )
            for c in criteria
        ],
        reference_links=_links(assignment),
        attachments=_attachments(assignment),
        late_policy=assignment.late_policy,
        late_cutoff_hours=assignment.late_cutoff_hours,
        submission_id=latest.id if latest else None,
        can_submit=can_still_be_handed_in(assignment, at),
    )
