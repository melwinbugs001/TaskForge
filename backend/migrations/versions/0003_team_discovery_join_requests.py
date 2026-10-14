"""Add team discovery and leader-reviewed join requests.

Revision ID: 0003_team_discovery
Revises: 0002_teams_tasks
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_team_discovery"
down_revision: Union[str, None] = "0002_teams_tasks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "teams",
        sa.Column(
            "is_discoverable",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.create_table(
        "team_join_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "team_id",
            sa.Integer(),
            sa.ForeignKey("teams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "resolved_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.UniqueConstraint(
            "team_id",
            "user_id",
            name="uq_team_join_requests_team_user",
        ),
    )
    op.create_index(
        "ix_team_join_requests_team_status",
        "team_join_requests",
        ["team_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_team_join_requests_team_status",
        table_name="team_join_requests",
    )
    op.drop_table("team_join_requests")
    op.drop_column("teams", "is_discoverable")
