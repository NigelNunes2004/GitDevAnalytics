"""Derived insights: health score, stale items, CI, languages, compare, reviews."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Commit, Issue, PullRequest, RepoLanguage, TrackedRepository, WorkflowRun
from app.schemas import (
    CompareResponse,
    CompareSide,
    LanguageStat,
    RepoHealthScore,
    ReviewLatencyItem,
    StaleAlert,
    StaleAlertsResponse,
    WorkflowRunOut,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    """Normalize SQLite-naive datetimes to UTC-aware for comparisons."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _resolve_repo(
    db: Session, user_id: int, repo: str | None
) -> TrackedRepository | None:
    if not repo:
        return None
    return db.scalar(
        select(TrackedRepository).where(
            TrackedRepository.user_id == user_id,
            TrackedRepository.full_name == repo,
        )
    )


def _resolve_repo_id(db: Session, user_id: int, repo: str | None) -> int | None:
    found = _resolve_repo(db, user_id, repo)
    return found.id if found else None


def repo_health(
    db: Session, user_id: int, repo: str | None = None
) -> list[RepoHealthScore]:
    settings = get_settings()
    stale_days = settings.stale_days
    cutoff = _now() - timedelta(days=stale_days)
    week_ago = _now() - timedelta(days=7)

    repos = []
    if repo:
        found = _resolve_repo(db, user_id, repo)
        if found:
            repos = [found]
    else:
        stmt = (
            select(TrackedRepository)
            .where(TrackedRepository.user_id == user_id)
            .order_by(TrackedRepository.full_name)
        )
        repos = list(db.scalars(stmt).all())

    results: list[RepoHealthScore] = []
    for tracked in repos:
        commits_7d = len(
            list(
                db.scalars(
                    select(Commit).where(
                        Commit.repo_id == tracked.id,
                        Commit.committed_at >= week_ago,
                    )
                ).all()
            )
        )
        open_prs = list(
            db.scalars(
                select(PullRequest).where(
                    PullRequest.repo_id == tracked.id,
                    PullRequest.state == "open",
                )
            ).all()
        )
        stale_prs = sum(1 for pr in open_prs if _aware(pr.created_at) < cutoff)
        open_issues = list(
            db.scalars(
                select(Issue).where(Issue.repo_id == tracked.id, Issue.state == "open")
            ).all()
        )
        stale_issues = sum(1 for issue in open_issues if _aware(issue.created_at) < cutoff)

        recent_runs = list(
            db.scalars(
                select(WorkflowRun)
                .where(WorkflowRun.repo_id == tracked.id)
                .order_by(WorkflowRun.run_started_at.desc())
                .limit(10)
            ).all()
        )
        failed_runs = sum(1 for run in recent_runs if run.conclusion == "failure")

        # Simple 0–100 score: activity helps, staleness and CI failures hurt
        score = 50.0
        score += min(30.0, commits_7d * 3.0)
        score -= min(25.0, stale_prs * 5.0)
        score -= min(15.0, stale_issues * 3.0)
        score -= min(20.0, failed_runs * 4.0)
        score = max(0.0, min(100.0, round(score, 1)))

        results.append(
            RepoHealthScore(
                repo=tracked.full_name,
                score=score,
                commits_last_7_days=commits_7d,
                open_prs=len(open_prs),
                stale_prs=stale_prs,
                open_issues=len(open_issues),
                stale_issues=stale_issues,
                recent_ci_failures=failed_runs,
            )
        )
    return results


def stale_alerts(
    db: Session, user_id: int, repo: str | None = None
) -> StaleAlertsResponse:
    settings = get_settings()
    cutoff = _now() - timedelta(days=settings.stale_days)
    repo_id = _resolve_repo_id(db, user_id, repo)

    pr_stmt = (
        select(PullRequest, TrackedRepository)
        .join(TrackedRepository, PullRequest.repo_id == TrackedRepository.id)
        .where(
            TrackedRepository.user_id == user_id,
            PullRequest.state == "open",
            PullRequest.created_at < cutoff,
        )
    )
    issue_stmt = (
        select(Issue, TrackedRepository)
        .join(TrackedRepository, Issue.repo_id == TrackedRepository.id)
        .where(
            TrackedRepository.user_id == user_id,
            Issue.state == "open",
            Issue.created_at < cutoff,
        )
    )
    if repo_id is not None:
        pr_stmt = pr_stmt.where(PullRequest.repo_id == repo_id)
        issue_stmt = issue_stmt.where(Issue.repo_id == repo_id)

    alerts: list[StaleAlert] = []
    for pr, tracked in db.execute(pr_stmt).all():
        age = (_now() - _aware(pr.created_at)).total_seconds() / 86400.0
        alerts.append(
            StaleAlert(
                kind="pr",
                repo=tracked.full_name,
                number=pr.number,
                title=pr.title,
                author=pr.author_login,
                age_days=round(age, 1),
                created_at=pr.created_at,
            )
        )
    for issue, tracked in db.execute(issue_stmt).all():
        age = (_now() - _aware(issue.created_at)).total_seconds() / 86400.0
        alerts.append(
            StaleAlert(
                kind="issue",
                repo=tracked.full_name,
                number=issue.number,
                title=issue.title,
                author=issue.author_login,
                age_days=round(age, 1),
                created_at=issue.created_at,
            )
        )
    alerts.sort(key=lambda a: a.age_days, reverse=True)
    return StaleAlertsResponse(stale_days=settings.stale_days, items=alerts)


def workflow_runs(
    db: Session, user_id: int, repo: str | None = None, limit: int = 20
) -> list[WorkflowRunOut]:
    repo_id = _resolve_repo_id(db, user_id, repo)
    stmt = (
        select(WorkflowRun, TrackedRepository)
        .join(TrackedRepository, WorkflowRun.repo_id == TrackedRepository.id)
        .where(TrackedRepository.user_id == user_id)
        .order_by(WorkflowRun.run_started_at.desc())
        .limit(limit)
    )
    if repo_id is not None:
        stmt = stmt.where(WorkflowRun.repo_id == repo_id)

    out: list[WorkflowRunOut] = []
    for run, tracked in db.execute(stmt).all():
        out.append(
            WorkflowRunOut(
                repo=tracked.full_name,
                name=run.name,
                status=run.status,
                conclusion=run.conclusion,
                html_url=run.html_url,
                run_started_at=run.run_started_at,
                duration_seconds=run.duration_seconds,
            )
        )
    return out


def review_latency(
    db: Session, user_id: int, repo: str | None = None
) -> list[ReviewLatencyItem]:
    repo_id = _resolve_repo_id(db, user_id, repo)
    stmt = (
        select(PullRequest)
        .join(TrackedRepository, PullRequest.repo_id == TrackedRepository.id)
        .where(
            TrackedRepository.user_id == user_id,
            PullRequest.first_review_at.is_not(None),
        )
    )
    if repo_id is not None:
        stmt = stmt.where(PullRequest.repo_id == repo_id)
    stmt = stmt.order_by(PullRequest.first_review_at.desc())

    items: list[ReviewLatencyItem] = []
    for pr in db.scalars(stmt).all():
        assert pr.first_review_at is not None
        hours = (pr.first_review_at - pr.created_at).total_seconds() / 3600.0
        items.append(
            ReviewLatencyItem(
                number=pr.number,
                title=pr.title,
                author=pr.author_login,
                hours_to_first_review=round(hours, 2),
                days_to_first_review=round(hours / 24.0, 2),
                created_at=pr.created_at,
                first_review_at=pr.first_review_at,
            )
        )
    return items


def languages(
    db: Session, user_id: int, repo: str | None = None
) -> list[LanguageStat]:
    repo_id = _resolve_repo_id(db, user_id, repo)
    stmt = (
        select(RepoLanguage)
        .join(TrackedRepository, RepoLanguage.repo_id == TrackedRepository.id)
        .where(TrackedRepository.user_id == user_id)
    )
    if repo_id is not None:
        stmt = stmt.where(RepoLanguage.repo_id == repo_id)
    rows = list(db.scalars(stmt).all())

    totals: dict[str, int] = {}
    for row in rows:
        totals[row.language] = totals.get(row.language, 0) + int(row.bytes)

    total_bytes = sum(totals.values()) or 1
    return [
        LanguageStat(
            language=lang,
            bytes=byte_count,
            percent=round(100.0 * byte_count / total_bytes, 2),
        )
        for lang, byte_count in sorted(totals.items(), key=lambda x: x[1], reverse=True)
    ]


def _side_stats(db: Session, user_id: int, full_name: str) -> CompareSide:
    tracked = _resolve_repo(db, user_id, full_name)
    if tracked is None:
        return CompareSide(
            repo=full_name,
            commits=0,
            contributors=0,
            open_prs=0,
            merged_prs=0,
            avg_pr_turnaround_hours=None,
            avg_review_latency_hours=None,
        )

    commits = list(db.scalars(select(Commit).where(Commit.repo_id == tracked.id)).all())
    authors = {(c.author_login or c.author_name or "bob") for c in commits}
    prs = list(db.scalars(select(PullRequest).where(PullRequest.repo_id == tracked.id)).all())
    open_prs = sum(1 for pr in prs if pr.state == "open")
    merged = [pr for pr in prs if pr.merged_at is not None]
    avg_turnaround = None
    if merged:
        hours = [
            (pr.merged_at - pr.created_at).total_seconds() / 3600.0  # type: ignore[operator]
            for pr in merged
        ]
        avg_turnaround = round(sum(hours) / len(hours), 2)

    reviewed = [pr for pr in prs if pr.first_review_at is not None]
    avg_review = None
    if reviewed:
        hours = [
            (pr.first_review_at - pr.created_at).total_seconds() / 3600.0  # type: ignore[operator]
            for pr in reviewed
        ]
        avg_review = round(sum(hours) / len(hours), 2)

    return CompareSide(
        repo=full_name,
        commits=len(commits),
        contributors=len(authors),
        open_prs=open_prs,
        merged_prs=len(merged),
        avg_pr_turnaround_hours=avg_turnaround,
        avg_review_latency_hours=avg_review,
    )


def compare_repos(
    db: Session, user_id: int, repo_a: str, repo_b: str
) -> CompareResponse:
    return CompareResponse(
        a=_side_stats(db, user_id, repo_a),
        b=_side_stats(db, user_id, repo_b),
    )
