"""Remove AI execution plans from goals.

Revision ID: 0005_remove_goal_plans
Revises: 0004_goal_due_date
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_remove_goal_plans"
down_revision: Union[str, None] = "0004_goal_due_date"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text("UPDATE goals SET status = 'draft' WHERE status = 'planned'")
    )
    op.drop_column("goals", "execution_plan")


def downgrade() -> None:
    op.add_column("goals", sa.Column("execution_plan", sa.JSON(), nullable=True))
