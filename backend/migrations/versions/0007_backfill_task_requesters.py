"""Backfill requester IDs for existing worker task requests."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007_backfill_task_requesters"
down_revision: Union[str, None] = "0006_task_requests"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE team_tasks
            SET requested_by = assignee_id
            WHERE requested_by IS NULL
              AND status IN ('pending_approval', 'declined')
            """
        )
    )


def downgrade() -> None:
    pass
