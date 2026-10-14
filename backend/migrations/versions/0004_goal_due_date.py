"""Add optional due dates to goals.

Revision ID: 0004_goal_due_date
Revises: 0003_team_discovery
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_goal_due_date"
down_revision: Union[str, None] = "0003_team_discovery"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("goals", sa.Column("due_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("goals", "due_at")
