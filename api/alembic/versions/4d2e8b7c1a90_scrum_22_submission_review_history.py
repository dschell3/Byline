"""SCRUM-22 review reason, criterion scores and submission comments

Revision ID: 4d2e8b7c1a90
Revises: f3b7d9a1c5e2
Create Date: 2026-11-07

The submission page (P14) shows every version of a submission, each review
with the reason behind it and a score per assessment criterion, and the
comments between member and supervisor. None of that had a home:

- assessment_criterion: the checklist an assignment is scored against
  (also what SCRUM-18 renders on P12).
- review.reason: the written reason behind a decision (SCRUM-21 shows it
  while the member fixes their work).
- review_criterion_score: one row per criterion per review.
- submission_comment: one thread per submission version, one level of replies.

review.decision also gains a check constraint for the two spellings work.py
already relies on, the same way SCRUM-23 constrained assignment.late_policy.

Revises the head at the time of writing. If SCRUM-23's 07c3e0d206fd merges
first, this re-parents onto it (CONTRIBUTING, Migrations).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '4d2e8b7c1a90'
down_revision: Union[str, Sequence[str], None] = 'f3b7d9a1c5e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DECISIONS = "decision IN ('approved', 'changes_requested')"


def upgrade() -> None:
    """Add review.reason and the decision check, then the three new tables."""
    op.add_column('review', sa.Column('reason', sa.Text(), nullable=True))
    op.create_check_constraint('ck_review_decision', 'review', DECISIONS)
    op.create_table('assessment_criterion',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('assignment_id', sa.BigInteger(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('max_points', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('max_points >= 0', name='ck_assessment_criterion_max_points'),
    sa.ForeignKeyConstraint(['assignment_id'], ['assignment.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('assignment_id', 'position', name='uq_assessment_criterion_position')
    )
    op.create_table('review_criterion_score',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('review_id', sa.BigInteger(), nullable=False),
    sa.Column('criterion_id', sa.BigInteger(), nullable=False),
    sa.Column('score', sa.Integer(), nullable=False),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('score >= 0', name='ck_review_criterion_score_score'),
    sa.ForeignKeyConstraint(['criterion_id'], ['assessment_criterion.id'], ),
    sa.ForeignKeyConstraint(['review_id'], ['review.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('review_id', 'criterion_id', name='uq_review_criterion_score')
    )
    op.create_table('submission_comment',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('submission_id', sa.BigInteger(), nullable=False),
    sa.Column('author_membership_id', sa.BigInteger(), nullable=False),
    sa.Column('parent_comment_id', sa.BigInteger(), nullable=True),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['author_membership_id'], ['membership.id'], ),
    sa.ForeignKeyConstraint(['parent_comment_id'], ['submission_comment.id'], ),
    sa.ForeignKeyConstraint(['submission_id'], ['submission.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Drop the three tables, then the decision check and review.reason."""
    op.drop_table('submission_comment')
    op.drop_table('review_criterion_score')
    op.drop_table('assessment_criterion')
    op.drop_constraint('ck_review_decision', 'review', type_='check')
    op.drop_column('review', 'reason')
