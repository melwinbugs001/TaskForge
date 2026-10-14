"""Track worker progress within a shared team task.

Revision ID: 0008_shared_task_assignments
Revises: 0007_backfill_task_requesters
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0008_shared_task_assignments"
down_revision: Union[str, None] = "0007_backfill_task_requesters"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "team_task_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "task_id",
            sa.Integer(),
            sa.ForeignKey("team_tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=24), server_default="assigned", nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_comment", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("task_id", "user_id", name="uq_task_assignments_task_user"),
    )
    op.create_index(
        "ix_task_assignments_user_status",
        "team_task_assignments",
        ["user_id", "status"],
        unique=False,
    )
    op.execute(
        sa.text(
            """
            INSERT INTO team_task_assignments (
                task_id, user_id, status, submitted_at, completed_at,
                review_comment, created_at, updated_at
            )
            SELECT id, assignee_id, status, submitted_at, completed_at,
                   review_comment, created_at, updated_at
            FROM team_tasks
            """
        )
    )


def downgrade() -> None:
    op.drop_index(
        "ix_task_assignments_user_status", table_name="team_task_assignments"
    )
    op.drop_table("team_task_assignments")