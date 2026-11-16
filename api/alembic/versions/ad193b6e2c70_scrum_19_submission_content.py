"""SCRUM-19: store text, link, and GitHub PR submissions.

Revision ID: ad193b6e2c70
Revises: 4d2e8b7c1a90
"""

import sqlalchemy as sa
from alembic import op

revision = "ad193b6e2c70"
down_revision = "4d2e8b7c1a90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add content fields without changing existing submissions."""
    op.add_column(
        "submission",
        sa.Column("submission_kind", sa.Text(), nullable=True),
    )
    op.add_column(
        "submission",
        sa.Column("content", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Remove SCRUM-19 content fields."""
    op.drop_column("submission", "content")
    op.drop_column("submission", "submission_kind")
