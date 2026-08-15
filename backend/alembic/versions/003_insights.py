"""Add CI runs, languages, uptime, and PR first_review_at.

Revision ID: 003_insights
Revises: 002_bigint_github_ids
"""

from alembic import op
import sqlalchemy as sa

revision = "003_insights"
down_revision = "002_bigint_github_ids"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pull_requests",
        sa.Column("first_review_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("github_run_id", sa.BigInteger(), nullable=False),
        sa.Column("repo_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("conclusion", sa.String(length=64), nullable=True),
        sa.Column("html_url", sa.String(length=1024), nullable=True),
        sa.Column("run_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["repo_id"], ["tracked_repositories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("github_run_id", name="uq_workflow_run_id"),
    )
    op.create_index(op.f("ix_workflow_runs_github_run_id"), "workflow_runs", ["github_run_id"])

    op.create_table(
        "repo_languages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repo_id", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(length=128), nullable=False),
        sa.Column("bytes", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["repo_id"], ["tracked_repositories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repo_id", "language", name="uq_repo_language"),
    )

    op.create_table(
        "uptime_checks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ok", sa.Boolean(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("detail", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_uptime_checks_checked_at"), "uptime_checks", ["checked_at"])


def downgrade() -> None:
    op.drop_index(op.f("ix_uptime_checks_checked_at"), table_name="uptime_checks")
    op.drop_table("uptime_checks")
    op.drop_table("repo_languages")
    op.drop_index(op.f("ix_workflow_runs_github_run_id"), table_name="workflow_runs")
    op.drop_table("workflow_runs")
    op.drop_column("pull_requests", "first_review_at")
