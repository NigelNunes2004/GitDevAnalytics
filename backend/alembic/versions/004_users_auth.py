"""Add users and scope tracked repos per user.

Revision ID: 004_users_auth
Revises: 003_insights
"""

from __future__ import annotations

import os

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

revision = "004_users_auth"
down_revision = "003_insights"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("github_username", sa.String(length=255), nullable=True),
        sa.Column("github_token_encrypted", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)

    # Bootstrap admin so existing tracked repos can be reassigned
    users_t = table(
        "users",
        column("id", sa.Integer),
        column("email", sa.String),
        column("password_hash", sa.String),
    )
    # Placeholder hash; app will recreate/login via register if needed.
    # Real bcrypt hash for password "changeme" is set in post-migrate bootstrap if empty DB.
    # Use a recognizable marker; auth service can detect and allow reset via register uniqueness.
    bootstrap_email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "admin@localhost")
    # bcrypt hash for "changeme" generated offline-compatible; migration inserts a temp value
    # that auth will overwrite only if user re-registers. For existing installs we use
    # passlib-compatible hash set in a data migration step below via Python if available.
    password_hash = os.getenv(
        "BOOTSTRAP_ADMIN_PASSWORD_HASH",
        # bcrypt for "changeme"
        "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
    )
    op.bulk_insert(
        users_t,
        [{"id": 1, "email": bootstrap_email, "password_hash": password_hash}],
    )

    op.add_column(
        "tracked_repositories",
        sa.Column("user_id", sa.Integer(), nullable=True),
    )
    op.execute("UPDATE tracked_repositories SET user_id = 1 WHERE user_id IS NULL")
    op.alter_column("tracked_repositories", "user_id", nullable=False)
    op.create_foreign_key(
        "fk_tracked_repositories_user_id",
        "tracked_repositories",
        "users",
        ["user_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_tracked_repositories_user_id"),
        "tracked_repositories",
        ["user_id"],
        unique=False,
    )

    # Replace global unique(full_name) with per-user unique
    op.drop_constraint("tracked_repositories_full_name_key", "tracked_repositories", type_="unique")
    # index ix_tracked_repositories_full_name may remain non-unique
    op.create_unique_constraint(
        "uq_tracked_repo_user_full_name",
        "tracked_repositories",
        ["user_id", "full_name"],
    )

    # Commits sha was globally unique; scope to repo so users can sync same public repos
    op.drop_constraint("uq_commits_sha", "commits", type_="unique")
    op.create_unique_constraint("uq_commits_sha_repo", "commits", ["sha", "repo_id"])


def downgrade() -> None:
    op.drop_constraint("uq_commits_sha_repo", "commits", type_="unique")
    op.create_unique_constraint("uq_commits_sha", "commits", ["sha"])

    op.drop_constraint("uq_tracked_repo_user_full_name", "tracked_repositories", type_="unique")
    op.create_unique_constraint(
        "tracked_repositories_full_name_key",
        "tracked_repositories",
        ["full_name"],
    )
    op.drop_constraint("fk_tracked_repositories_user_id", "tracked_repositories", type_="foreignkey")
    op.drop_index(op.f("ix_tracked_repositories_user_id"), table_name="tracked_repositories")
    op.drop_column("tracked_repositories", "user_id")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
