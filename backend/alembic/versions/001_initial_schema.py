"""Generic single-database configuration with SQLAlchemy."""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tracked_repositories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("full_name"),
    )
    op.create_index(
        op.f("ix_tracked_repositories_full_name"),
        "tracked_repositories",
        ["full_name"],
        unique=False,
    )

    op.create_table(
        "commits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sha", sa.String(length=40), nullable=False),
        sa.Column("repo_id", sa.Integer(), nullable=False),
        sa.Column("author_login", sa.String(length=255), nullable=True),
        sa.Column("author_name", sa.String(length=255), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["repo_id"], ["tracked_repositories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sha", name="uq_commits_sha"),
    )
    op.create_index(op.f("ix_commits_sha"), "commits", ["sha"], unique=False)
    op.create_index(op.f("ix_commits_committed_at"), "commits", ["committed_at"], unique=False)

    op.create_table(
        "pull_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("github_id", sa.BigInteger(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("repo_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("author_login", sa.String(length=255), nullable=True),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("merged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["repo_id"], ["tracked_repositories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repo_id", "number", name="uq_pr_repo_number"),
    )
    op.create_index(op.f("ix_pull_requests_github_id"), "pull_requests", ["github_id"], unique=False)

    op.create_table(
        "issues",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("github_id", sa.BigInteger(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("repo_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("author_login", sa.String(length=255), nullable=True),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["repo_id"], ["tracked_repositories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repo_id", "number", name="uq_issue_repo_number"),
    )
    op.create_index(op.f("ix_issues_github_id"), "issues", ["github_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_issues_github_id"), table_name="issues")
    op.drop_table("issues")
    op.drop_index(op.f("ix_pull_requests_github_id"), table_name="pull_requests")
    op.drop_table("pull_requests")
    op.drop_index(op.f("ix_commits_committed_at"), table_name="commits")
    op.drop_index(op.f("ix_commits_sha"), table_name="commits")
    op.drop_table("commits")
    op.drop_index(op.f("ix_tracked_repositories_full_name"), table_name="tracked_repositories")
    op.drop_table("tracked_repositories")
