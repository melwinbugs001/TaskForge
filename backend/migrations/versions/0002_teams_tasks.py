"""Add teams, invitations, and scheduled team tasks.

Revision ID: 0002_teams_tasks
Revises: 0001_auth_goals
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_teams_tasks"
down_revision: Union[str, None] = "0001_auth_goals"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "name",
            sa.String(length=120),
            nullable=False,
        ),
        sa.Column(
            "leader_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_teams_leader_id", "teams", ["leader_id"], unique=False)
    op.create_index(
        "ix_teams_leader_created",
        "teams",
        ["leader_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "team_members",
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
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("team_id", "user_id", name="uq_team_members_team_user"),
    )
    op.create_index(
        "ix_team_members_user_team",
        "team_members",
        ["user_id", "team_id"],
        unique=False,
    )

    op.create_table(
        "team_invites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "team_id",
            sa.Integer(),
            sa.ForeignKey("teams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column(
            "invited_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("team_id", "email", name="uq_team_invites_team_email"),
    )
    op.create_index(
        "ix_team_invites_email",
        "team_invites",
        ["email"],
        unique=False,
    )

    op.create_table(
        "team_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "team_id",
            sa.Integer(),
            sa.ForeignKey("teams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "assignee_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "assigned_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.String(length=24),
            server_default="assigned",
            nullable=False,
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_comment", sa.String(length=2000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_team_tasks_team_created",
        "team_tasks",
        ["team_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_team_tasks_assignee_status",
        "team_tasks",
        ["assignee_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_team_tasks_assignee_status", table_name="team_tasks")
    op.drop_index("ix_team_tasks_team_created", table_name="team_tasks")
    op.drop_table("team_tasks")
    op.drop_index("ix_team_invites_email", table_name="team_invites")
    op.drop_table("team_invites")
    op.drop_index("ix_team_members_user_team", table_name="team_members")
    op.drop_table("team_members")
    op.drop_index("ix_teams_leader_created", table_name="teams")
    op.drop_index("ix_teams_leader_id", table_name="teams")
    op.drop_table("teams")
