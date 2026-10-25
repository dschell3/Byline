"""SCRUM-13 auth_session

Revision ID: a9018d52447c
Revises: b2c4e6a8d0f1
Create Date: 2026-10-25

Server-side sessions. The cookie holds a random token and this table holds
only its SHA-256, so sign-out, idle expiry and a password change can revoke
a session in the database rather than trusting the browser to forget it.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a9018d52447c'
down_revision: Union[str, Sequence[str], None] = 'b2c4e6a8d0f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create auth_session."""
    op.create_table('auth_session',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('person_id', sa.BigInteger(), nullable=False),
    sa.Column('token_hash', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['person_id'], ['person.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_hash')
    )
    op.create_index(op.f('ix_auth_session_person_id'), 'auth_session', ['person_id'], unique=False)


def downgrade() -> None:
    """Drop auth_session."""
    op.drop_index(op.f('ix_auth_session_person_id'), table_name='auth_session')
    op.drop_table('auth_session')
