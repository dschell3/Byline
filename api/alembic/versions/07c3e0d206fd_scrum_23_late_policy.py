"""SCRUM-23 late policy values and cutoff

Revision ID: 07c3e0d206fd
Revises: f3b7d9a1c5e2
Create Date: 2026-11-04

assignment.late_policy was free text with no agreed values. It now holds one
of three, enforced by the database, and late_cutoff_hours says how long after
the due date late work is still taken.

Nothing enforced lateness before this, so late work was in effect always
accepted at full points. Existing rows keep that meaning.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '07c3e0d206fd'
down_revision: Union[str, Sequence[str], None] = 'f3b7d9a1c5e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LATE_POLICIES = "late_policy IN ('not_accepted', 'accepted_full_points', 'accepted_half_points')"


def upgrade() -> None:
    """Give old free-text values their real meaning, then add the cutoff and the checks."""
    op.execute(
        "UPDATE assignment SET late_policy = 'accepted_full_points' "
        f"WHERE NOT ({LATE_POLICIES})"
    )
    op.add_column('assignment', sa.Column('late_cutoff_hours', sa.Integer(), nullable=True))
    op.create_check_constraint('ck_assignment_late_policy', 'assignment', LATE_POLICIES)
    op.create_check_constraint(
        'ck_assignment_late_cutoff_hours', 'assignment', 'late_cutoff_hours > 0'
    )


def downgrade() -> None:
    """Drop the checks and the cutoff. late_policy keeps its new values as plain text."""
    op.drop_constraint('ck_assignment_late_cutoff_hours', 'assignment', type_='check')
    op.drop_constraint('ck_assignment_late_policy', 'assignment', type_='check')
    op.drop_column('assignment', 'late_cutoff_hours')
