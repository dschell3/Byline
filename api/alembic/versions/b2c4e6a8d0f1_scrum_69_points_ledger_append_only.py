"""SCRUM-69 points_ledger append-only

Revision ID: b2c4e6a8d0f1
Revises: 7a43f0f5698d
Create Date: 2026-10-18

Rows in points_ledger are never updated or deleted. A correction is a new row
with a negative amount and reverses_ledger_id pointing at the original
(docs/erd.md, "Points ledger is append-only"). This trigger makes the
database enforce that, so no code path can bypass it.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b2c4e6a8d0f1'
down_revision: Union[str, Sequence[str], None] = '7a43f0f5698d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the trigger that rejects UPDATE and DELETE on points_ledger."""
    op.execute(
        """
        CREATE FUNCTION points_ledger_append_only() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'points_ledger is append-only: % is not allowed', TG_OP
                USING ERRCODE = 'restrict_violation';
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER points_ledger_no_update_delete
        BEFORE UPDATE OR DELETE ON points_ledger
        FOR EACH ROW EXECUTE FUNCTION points_ledger_append_only();
        """
    )
    # TRUNCATE skips row-level triggers, so it needs its own statement-level one.
    op.execute(
        """
        CREATE TRIGGER points_ledger_no_truncate
        BEFORE TRUNCATE ON points_ledger
        FOR EACH STATEMENT EXECUTE FUNCTION points_ledger_append_only();
        """
    )


def downgrade() -> None:
    """Remove the trigger and its function."""
    op.execute("DROP TRIGGER IF EXISTS points_ledger_no_truncate ON points_ledger")
    op.execute("DROP TRIGGER IF EXISTS points_ledger_no_update_delete ON points_ledger")
    op.execute("DROP FUNCTION IF EXISTS points_ledger_append_only()")
