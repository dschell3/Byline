"""SCRUM-83 file storage

Revision ID: d8e2f4a6b1c3
Revises: 9c1f4a7e2b53
Create Date: 2026-11-17

- stored_file: one uploaded object, ``pending`` until the bucket confirms it.
  ``key`` is the object key submission.file_keys already expects.
- assignment.submission_kind: the kind the submit form opens on. Nullable.
- person.photo_file_id: the profile photo. Its FK is added last because
  stored_file reaches person through membership. It replaces the pasted-link
  person.photo_url, dropped here; nothing on staging had set one.

Follows SCRUM-18's 9c1f4a7e2b53 (CONTRIBUTING, Migrations).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd8e2f4a6b1c3'
down_revision: Union[str, Sequence[str], None] = '9c1f4a7e2b53'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create stored_file and the two columns that reference it."""
    op.create_table(
        'stored_file',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('organization_id', sa.BigInteger(), sa.ForeignKey('organization.id'), nullable=False),
        sa.Column(
            'uploaded_by_membership_id',
            sa.BigInteger(),
            sa.ForeignKey('membership.id'),
            nullable=False,
        ),
        sa.Column('key', sa.Text(), nullable=False, unique=True),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('content_type', sa.Text(), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False, server_default='pending'),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'complete')", name='ck_stored_file_status'),
        sa.CheckConstraint('size_bytes >= 0', name='ck_stored_file_size_bytes'),
    )
    op.add_column('assignment', sa.Column('submission_kind', sa.Text(), nullable=True))
    op.create_check_constraint(
        'ck_assignment_submission_kind',
        'assignment',
        "submission_kind IN ('text', 'link', 'pr', 'file')",
    )
    op.add_column('person', sa.Column('photo_file_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key('fk_person_photo_file', 'person', 'stored_file', ['photo_file_id'], ['id'])
    op.drop_column('person', 'photo_url')


def downgrade() -> None:
    """Drop them again, references first, and bring the link column back."""
    op.add_column('person', sa.Column('photo_url', sa.Text(), nullable=True))
    op.drop_constraint('fk_person_photo_file', 'person', type_='foreignkey')
    op.drop_column('person', 'photo_file_id')
    op.drop_constraint('ck_assignment_submission_kind', 'assignment', type_='check')
    op.drop_column('assignment', 'submission_kind')
    op.drop_table('stored_file')
