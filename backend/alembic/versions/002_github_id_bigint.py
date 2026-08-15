"""Widen github_id columns to BIGINT.

Revision ID: 002_bigint_github_ids
Revises: 001_initial
Create Date: 2026-08-16

GitHub PR/issue IDs can exceed PostgreSQL INTEGER max (~2.1B).
"""

from alembic import op
import sqlalchemy as sa

revision = "002_bigint_github_ids"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "pull_requests",
        "github_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )
    op.alter_column(
        "issues",
        "github_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "issues",
        "github_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "pull_requests",
        "github_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
