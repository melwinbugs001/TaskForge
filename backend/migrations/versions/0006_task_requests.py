"""Add worker task requests and leader approval."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006_task_requests"
down_revision: Union[str, None] = "0005_remove_goal_plans"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("team_tasks") as batch_op:
        batch_op.add_column(
            sa.Column(
                "requested_by",
                sa.Integer(),
                sa.ForeignKey(
                    "users.id",
                    name="fk_team_tasks_requested_by_users",
                    ondelete="SET NULL",
                ),
                nullable=True,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("team_tasks") as batch_op:
        batch_op.drop_column("requested_by")
