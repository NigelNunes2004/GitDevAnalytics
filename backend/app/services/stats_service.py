"""SQL + light Python aggregations over stored GitHub data (not live API calls).

Why aggregate from Postgres: charts need fast, repeatable JSON; re-hitting GitHub
on every page load would burn rate limit and be slow. Sync once, query many times.

Bucketing (day/week) is done in Python so the same code works on local Postgres,
Supabase, and SQLite in tests — easier to explain in interviews than dialect-specific SQL.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Commit, PullRequest, TrackedRepository
from app.schemas import CommitCountPoint, ContributorStat, PRTurnaroundItem


def _resolve_repo_id(db: Session, repo: str | None) -> int | None:
    if not repo:
        return None
    found = db.scalar(select(TrackedRepository).where(TrackedRepository.full_name == repo))
    return found.id if found else None


def _week_start(dt: datetime) -> str:
    # Monday as start of week (ISO)
    monday = (dt.date() - timedelta(days=dt.weekday()))
    return monday.isoformat()


def commits_over_time(
    db: Session, repo: str | None = None, period: str = "day"
) -> list[CommitCountPoint]:
    repo_id = _resolve_repo_id(db, repo)
    stmt = select(Commit)
    if repo_id is not None:
        stmt = stmt.where(Commit.repo_id == repo_id)
    commits = list(db.scalars(stmt).all())

    buckets: dict[str, int] = defaultdict(int)
    for commit in commits:
        if period == "week":
            key = _week_start(commit.committed_at)
        else:
            key = commit.committed_at.date().isoformat()
        buckets[key] += 1

    return [
        CommitCountPoint(date=date, count=count)
        for date, count in sorted(buckets.items(), key=lambda item: item[0])
    ]


def contributor_activity(db: Session, repo: str | None = None) -> list[ContributorStat]:
    repo_id = _resolve_repo_id(db, repo)
    stmt = select(Commit)
    if repo_id is not None:
        stmt = stmt.where(Commit.repo_id == repo_id)
    commits = list(db.scalars(stmt).all())

    counts: dict[str, int] = defaultdict(int)
    for commit in commits:
        author = commit.author_login or commit.author_name or "unknown"
        counts[author] += 1

    return [
        ContributorStat(author=author, commits=count)
        for author, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)
    ]


def pr_turnaround(db: Session, repo: str | None = None) -> list[PRTurnaroundItem]:
    """Hours/days from PR opened → merged (only merged PRs)."""
    repo_id = _resolve_repo_id(db, repo)
    stmt = select(PullRequest).where(PullRequest.merged_at.is_not(None))
    if repo_id is not None:
        stmt = stmt.where(PullRequest.repo_id == repo_id)
    prs = list(db.scalars(stmt.order_by(PullRequest.merged_at.desc())).all())

    items: list[PRTurnaroundItem] = []
    for pr in prs:
        assert pr.merged_at is not None
        delta = pr.merged_at - pr.created_at
        hours = delta.total_seconds() / 3600.0
        items.append(
            PRTurnaroundItem(
                number=pr.number,
                title=pr.title,
                author=pr.author_login,
                hours=round(hours, 2),
                days=round(hours / 24.0, 2),
                created_at=pr.created_at,
                merged_at=pr.merged_at,
            )
        )
    return items
