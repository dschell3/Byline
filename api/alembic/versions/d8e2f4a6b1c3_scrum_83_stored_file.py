"""SCRUM-83 file storage

Revision ID: d8e2f4a6b1c3
Revises: 9c1f4a7e2b53
Create Date: 2026-11-17

Nothing on main could store a file. This adds the table the three screens
plug into, and the two columns that point at it:

- stored_file: one uploaded object. Written as ``pending`` before the bytes
  leave the browser, ``complete`` once the object is confirmed in the bucket.
  ``key`` is the object key, as submission.file_keys and
  assignment.attachments already expect.
- assignment.submission_kind: how the supervisor wants work handed in
  (text, link, pr, file). The submit form opens on it. Nullable, so existing
  assignments leave the choice to the member.
- person.photo_file_id: the profile photo (P18), deferred since SCRUM-17.
  Added as a separate constraint because stored_file reaches person through
  membership, so the two tables must both exist first.

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


def downgrade() -> None:
    """Drop them again, references first."""
    op.drop_constraint('fk_person_photo_file', 'person', type_='foreignkey')
    op.drop_column('person', 'photo_file_id')
    op.drop_constraint('ck_assignment_submission_kind', 'assignment', type_='check')
    op.drop_column('assignment', 'submission_kind')
    op.drop_table('stored_file')
