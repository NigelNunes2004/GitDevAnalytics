from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    github_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    github_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    repositories: Mapped[list["TrackedRepository"]] = relationship(back_populates="owner_user")


class TrackedRepository(Base):
    __tablename__ = "tracked_repositories"
    __table_args__ = (
        UniqueConstraint("user_id", "full_name", name="uq_tracked_repo_user_full_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    owner_user: Mapped["User"] = relationship(back_populates="repositories")
    commits: Mapped[list["Commit"]] = relationship(back_populates="repository")
    pull_requests: Mapped[list["PullRequest"]] = relationship(back_populates="repository")
    issues: Mapped[list["Issue"]] = relationship(back_populates="repository")
    workflow_runs: Mapped[list["WorkflowRun"]] = relationship(back_populates="repository")
    languages: Mapped[list["RepoLanguage"]] = relationship(back_populates="repository")


class Commit(Base):
    __tablename__ = "commits"
    __table_args__ = (UniqueConstraint("sha", "repo_id", name="uq_commits_sha_repo"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sha: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    repo_id: Mapped[int] = mapped_column(ForeignKey("tracked_repositories.id"), nullable=False)
    author_login: Mapped[str | None] = mapped_column(String(255), nullable=True)
    author_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    committed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    repository: Mapped["TrackedRepository"] = relationship(back_populates="commits")


class PullRequest(Base):
    __tablename__ = "pull_requests"
    __table_args__ = (UniqueConstraint("repo_id", "number", name="uq_pr_repo_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    github_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    repo_id: Mapped[int] = mapped_column(ForeignKey("tracked_repositories.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    author_login: Mapped[str | None] = mapped_column(String(255), nullable=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    merged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    repository: Mapped["TrackedRepository"] = relationship(back_populates="pull_requests")


class Issue(Base):
    __tablename__ = "issues"
    __table_args__ = (UniqueConstraint("repo_id", "number", name="uq_issue_repo_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    github_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    repo_id: Mapped[int] = mapped_column(ForeignKey("tracked_repositories.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    author_login: Mapped[str | None] = mapped_column(String(255), nullable=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    repository: Mapped["TrackedRepository"] = relationship(back_populates="issues")


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"
    __table_args__ = (UniqueConstraint("github_run_id", name="uq_workflow_run_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    github_run_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    repo_id: Mapped[int] = mapped_column(ForeignKey("tracked_repositories.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    conclusion: Mapped[str | None] = mapped_column(String(64), nullable=True)
    html_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    run_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    repository: Mapped["TrackedRepository"] = relationship(back_populates="workflow_runs")


class RepoLanguage(Base):
    __tablename__ = "repo_languages"
    __table_args__ = (UniqueConstraint("repo_id", "language", name="uq_repo_language"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repo_id: Mapped[int] = mapped_column(ForeignKey("tracked_repositories.id"), nullable=False)
    language: Mapped[str] = mapped_column(String(128), nullable=False)
    bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    repository: Mapped["TrackedRepository"] = relationship(back_populates="languages")


class UptimeCheck(Base):
    __tablename__ = "uptime_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    ok: Mapped[bool] = mapped_column(Boolean, nullable=False)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    detail: Mapped[str | None] = mapped_column(String(255), nullable=True)
