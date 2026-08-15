from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TrackedRepository(Base):
    __tablename__ = "tracked_repositories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(512), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    commits: Mapped[list["Commit"]] = relationship(back_populates="repository")
    pull_requests: Mapped[list["PullRequest"]] = relationship(back_populates="repository")
    issues: Mapped[list["Issue"]] = relationship(back_populates="repository")


class Commit(Base):
    __tablename__ = "commits"
    __table_args__ = (UniqueConstraint("sha", name="uq_commits_sha"),)

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
    github_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    repo_id: Mapped[int] = mapped_column(ForeignKey("tracked_repositories.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    author_login: Mapped[str | None] = mapped_column(String(255), nullable=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    merged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    repository: Mapped["TrackedRepository"] = relationship(back_populates="pull_requests")


class Issue(Base):
    __tablename__ = "issues"
    __table_args__ = (UniqueConstraint("repo_id", "number", name="uq_issue_repo_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    github_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    repo_id: Mapped[int] = mapped_column(ForeignKey("tracked_repositories.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    author_login: Mapped[str | None] = mapped_column(String(255), nullable=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    repository: Mapped["TrackedRepository"] = relationship(back_populates="issues")
