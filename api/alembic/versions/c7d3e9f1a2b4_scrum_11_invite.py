"""SCRUM-11 invite

Revision ID: c7d3e9f1a2b4
Revises: a9018d52447c
Create Date: 2026-10-25

Invite links. The URL carries a random token and this table holds only its
SHA-256, so a leaked row cannot be turned back into a working link. Accepting
stamps accepted_at, which is what makes a link single-use.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c7d3e9f1a2b4'
down_revision: Union[str, Sequence[str], None] = 'a9018d52447c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create invite."""
    op.create_table('invite',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('organization_id', sa.BigInteger(), nullable=False),
    sa.Column('invited_by_membership_id', sa.BigInteger(), nullable=False),
    sa.Column('email', sa.Text(), nullable=False),
    sa.Column('role', sa.Text(), server_default='member', nullable=False),
    sa.Column('team_id', sa.BigInteger(), nullable=True),
    sa.Column('cohort_id', sa.BigInteger(), nullable=True),
    sa.Column('track_id', sa.BigInteger(), nullable=True),
    sa.Column('token_hash', sa.Text(), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("role IN ('member', 'supervisor', 'admin')", name='ck_invite_role'),
    sa.ForeignKeyConstraint(['cohort_id'], ['cohort.id'], ),
    sa.ForeignKeyConstraint(['invited_by_membership_id'], ['membership.id'], ),
    sa.ForeignKeyConstraint(['organization_id'], ['organization.id'], ),
    sa.ForeignKeyConstraint(['team_id'], ['team.id'], ),
    sa.ForeignKeyConstraint(['track_id'], ['track.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_hash')
    )


def downgrade() -> None:
    """Drop invite."""
    op.drop_table('invite')
