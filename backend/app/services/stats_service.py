"""SQL + light Python aggregations over stored GitHub data (not live API calls)."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Commit, PullRequest, TrackedRepository
from app.schemas import CommitCountPoint, ContributorStat, PRTurnaroundItem


def _user_repo_ids(db: Session, user_id: int, repo: str | None = None) -> list[int]:
    stmt = select(TrackedRepository.id).where(TrackedRepository.user_id == user_id)
    if repo:
        stmt = stmt.where(TrackedRepository.full_name == repo)
    return list(db.scalars(stmt).all())


def _week_start(dt: datetime) -> str:
    monday = (dt.date() - timedelta(days=dt.weekday()))
    return monday.isoformat()


def commits_over_time(
    db: Session,
    user_id: int,
    repo: str | None = None,
    period: str = "day",
) -> list[CommitCountPoint]:
    repo_ids = _user_repo_ids(db, user_id, repo)
    if not repo_ids:
        return []
    commits = list(db.scalars(select(Commit).where(Commit.repo_id.in_(repo_ids))).all())

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


def contributor_activity(
    db: Session, user_id: int, repo: str | None = None
) -> list[ContributorStat]:
    repo_ids = _user_repo_ids(db, user_id, repo)
    if not repo_ids:
        return []
    commits = list(db.scalars(select(Commit).where(Commit.repo_id.in_(repo_ids))).all())

    counts: dict[str, int] = defaultdict(int)
    for commit in commits:
        author = commit.author_login or commit.author_name or "bob"
        counts[author] += 1

    return [
        ContributorStat(author=author, commits=count)
        for author, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)
    ]


def pr_turnaround(
    db: Session, user_id: int, repo: str | None = None
) -> list[PRTurnaroundItem]:
    repo_ids = _user_repo_ids(db, user_id, repo)
    if not repo_ids:
        return []
    stmt = (
        select(PullRequest)
        .where(PullRequest.merged_at.is_not(None), PullRequest.repo_id.in_(repo_ids))
        .order_by(PullRequest.merged_at.desc())
    )
    prs = list(db.scalars(stmt).all())

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
