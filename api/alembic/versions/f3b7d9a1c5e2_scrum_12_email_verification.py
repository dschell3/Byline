"""SCRUM-12 email verification

Revision ID: f3b7d9a1c5e2
Revises: e5b8a2c4d6f1
Create Date: 2026-10-31

Email verification links. As with invites and sessions, the URL carries a
random token and this table holds only its SHA-256. used_at makes a link
single-use; expires_at is 24 hours after it was created. person gains
email_verified_at, stamped when a link is used.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f3b7d9a1c5e2'
down_revision: Union[str, Sequence[str], None] = 'e5b8a2c4d6f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add person.email_verified_at and create email_verification."""
    op.add_column('person', sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True))
    op.create_table('email_verification',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('person_id', sa.BigInteger(), nullable=False),
    sa.Column('email', sa.Text(), nullable=False),
    sa.Column('token_hash', sa.Text(), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['person_id'], ['person.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_hash')
    )


def downgrade() -> None:
    """Drop email_verification and person.email_verified_at."""
    op.drop_table('email_verification')
    op.drop_column('person', 'email_verified_at')
