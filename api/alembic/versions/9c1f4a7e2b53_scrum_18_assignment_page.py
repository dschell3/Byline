"""SCRUM-18 what the assignment page shows

Revision ID: 9c1f4a7e2b53
Revises: 4d2e8b7c1a90
Create Date: 2026-11-15

The assignment page (P12) shows the full description, reference links,
attachments, and a second line under each assessment criterion. None of those
had a column:

- assignment.description: the brief, plain text.
- assignment.reference_links: [{"label", "url"}] in the supervisor's order.
- assignment.attachments: [{"name", "key", "size_bytes"}]; key is the R2
  object key, as with submission.file_keys.
- assessment_criterion.detail: the optional hint under a criterion.

All four are nullable, so existing rows are untouched.

Follows SCRUM-22's 4d2e8b7c1a90 (CONTRIBUTING, Migrations).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9c1f4a7e2b53'
down_revision: Union[str, Sequence[str], None] = '4d2e8b7c1a90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the four nullable columns P12 reads."""
    op.add_column('assignment', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('assignment', sa.Column('reference_links', postgresql.JSONB(), nullable=True))
    op.add_column('assignment', sa.Column('attachments', postgresql.JSONB(), nullable=True))
    op.add_column('assessment_criterion', sa.Column('detail', sa.Text(), nullable=True))


def downgrade() -> None:
    """Drop them again."""
    op.drop_column('assessment_criterion', 'detail')
    op.drop_column('assignment', 'attachments')
    op.drop_column('assignment', 'reference_links')
    op.drop_column('assignment', 'description')
