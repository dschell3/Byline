"""SCRUM-17 profile columns on person

Revision ID: e5b8a2c4d6f1
Revises: c7d3e9f1a2b4
Create Date: 2026-10-27

Profile page. Adds the photo URL, contact preference and the three optional
email categories to person. Account emails (sign-in, password reset, invites,
verification) have no column on purpose: they always send.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e5b8a2c4d6f1'
down_revision: Union[str, Sequence[str], None] = 'c7d3e9f1a2b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the profile columns to person."""
    op.add_column('person', sa.Column('photo_url', sa.Text(), nullable=True))
    op.add_column('person', sa.Column('contact_preference', sa.Text(), server_default='email', nullable=False))
    op.add_column('person', sa.Column('contact_detail', sa.Text(), nullable=True))
    op.add_column('person', sa.Column('email_assignments', sa.Boolean(), server_default=sa.text('true'), nullable=False))
    op.add_column('person', sa.Column('email_reminders', sa.Boolean(), server_default=sa.text('true'), nullable=False))
    op.add_column('person', sa.Column('email_digest', sa.Boolean(), server_default=sa.text('true'), nullable=False))
    op.create_check_constraint(
        'ck_person_contact_preference',
        'person',
        "contact_preference IN ('email', 'discord', 'phone')",
    )


def downgrade() -> None:
    """Remove the profile columns from person."""
    op.drop_constraint('ck_person_contact_preference', 'person', type_='check')
    op.drop_column('person', 'email_digest')
    op.drop_column('person', 'email_reminders')
    op.drop_column('person', 'email_assignments')
    op.drop_column('person', 'contact_detail')
    op.drop_column('person', 'contact_preference')
    op.drop_column('person', 'photo_url')