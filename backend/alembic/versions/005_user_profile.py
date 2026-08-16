"""Add profile display_name and avatar_url on users.

Revision ID: 005_user_profile
Revises: 004_users_auth
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "005_user_profile"
down_revision = "004_users_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("display_name", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "display_name")
