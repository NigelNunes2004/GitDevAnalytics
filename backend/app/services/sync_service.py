"""Orchestrates GitHub fetch → Postgres upsert."""

from __future__ import annotations

import logging

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import (
    Commit,
    Issue,
    PullRequest,
    RepoLanguage,
    TrackedRepository,
    User,
    WorkflowRun,
)
from app.schemas import SyncResult
from app.services.github_client import GitHubClient, parse_github_datetime

logger = logging.getLogger(__name__)

# Cap review API calls so sync stays within rate limits on busy repos
MAX_PR_REVIEW_LOOKUPS = 20


def parse_full_name(full_name: str) -> tuple[str, str]:
    owner, name = full_name.split("/", 1)
    return owner, name


def upsert_repositories(
    db: Session, full_names: list[str], user_id: int
) -> list[TrackedRepository]:
    repos: list[TrackedRepository] = []
    for full_name in full_names:
        owner, name = parse_full_name(full_name)
        existing = db.scalar(
            select(TrackedRepository).where(
                TrackedRepository.user_id == user_id,
                TrackedRepository.full_name == full_name,
            )
        )
        if existing:
            repos.append(existing)
            continue
        repo = TrackedRepository(
            user_id=user_id, owner=owner, name=name, full_name=full_name
        )
        db.add(repo)
        db.flush()
        repos.append(repo)
    db.commit()
    for repo in repos:
        db.refresh(repo)
    return repos


def delete_repository(db: Session, repo_id: int, user_id: int) -> str | None:
    """Remove a tracked repo owned by this user and all related synced rows."""
    repo = db.scalar(
        select(TrackedRepository).where(
            TrackedRepository.id == repo_id,
            TrackedRepository.user_id == user_id,
        )
    )
    if repo is None:
        return None
    full_name = repo.full_name
    db.execute(delete(Commit).where(Commit.repo_id == repo_id))
    db.execute(delete(PullRequest).where(PullRequest.repo_id == repo_id))
    db.execute(delete(Issue).where(Issue.repo_id == repo_id))
    db.execute(delete(WorkflowRun).where(WorkflowRun.repo_id == repo_id))
    db.execute(delete(RepoLanguage).where(RepoLanguage.repo_id == repo_id))
    db.delete(repo)
    db.commit()
    return full_name


def sync_repository(
    db: Session, repo: TrackedRepository, client: GitHubClient | None = None
) -> SyncResult:
    client = client or GitHubClient()
    logger.info("Syncing %s", repo.full_name)

    commits_data = client.fetch_commits(repo.owner, repo.name)
    prs_data = client.fetch_pull_requests(repo.owner, repo.name)
    issues_data = client.fetch_issues(repo.owner, repo.name)
    languages = client.fetch_languages(repo.owner, repo.name)
    runs_data = client.fetch_workflow_runs(repo.owner, repo.name)

    commits_upserted = _upsert_commits(db, repo, commits_data)
    prs_upserted = _upsert_pull_requests(db, repo, prs_data)
    issues_upserted = _upsert_issues(db, repo, issues_data)
    _upsert_languages(db, repo, languages)
    runs_upserted = _upsert_workflow_runs(db, repo, runs_data)
    reviews_updated = _enrich_pr_reviews(db, repo, client)
    db.commit()

    return SyncResult(
        repo=repo.full_name,
        commits_upserted=commits_upserted,
        pull_requests_upserted=prs_upserted,
        issues_upserted=issues_upserted,
        workflow_runs_upserted=runs_upserted,
        reviews_updated=reviews_updated,
        rate_limit_remaining=client.last_remaining,
    )


def sync_user_repositories(db: Session, user: User, token: str) -> list[SyncResult]:
    client = GitHubClient(token=token)
    repos = list(
        db.scalars(
            select(TrackedRepository).where(TrackedRepository.user_id == user.id)
        ).all()
    )
    if not repos:
        return []
    return [sync_repository(db, repo, client=client) for repo in repos]


def sync_all_users_with_tokens(db: Session) -> list[SyncResult]:
    """Background job: sync every user who has a saved PAT."""
    from app.core.security import decrypt_secret

    users = list(
        db.scalars(select(User).where(User.github_token_encrypted.is_not(None))).all()
    )
    results: list[SyncResult] = []
    for user in users:
        try:
            token = decrypt_secret(user.github_token_encrypted or "")
        except ValueError:
            logger.warning("Skipping user %s — token decrypt failed", user.email)
            continue
        try:
            results.extend(sync_user_repositories(db, user, token))
        except Exception:
            logger.exception("Scheduled sync failed for user %s", user.email)
    return results


def sync_repository_by_full_name(
    db: Session, full_name: str, user_id: int | None = None, token: str | None = None
) -> SyncResult | None:
    stmt = select(TrackedRepository).where(TrackedRepository.full_name == full_name)
    if user_id is not None:
        stmt = stmt.where(TrackedRepository.user_id == user_id)
    repo = db.scalar(stmt)
    if repo is None:
        if user_id is None:
            return None
        repos = upsert_repositories(db, [full_name], user_id=user_id)
        repo = repos[0]
    client = GitHubClient(token=token) if token else GitHubClient()
    return sync_repository(db, repo, client=client)


def _upsert_commits(db: Session, repo: TrackedRepository, items: list[dict]) -> int:
    count = 0
    for item in items:
        sha = item.get("sha")
        if not sha:
            continue
        commit_block = item.get("commit") or {}
        author_block = commit_block.get("author") or {}
        github_author = item.get("author") or {}
        committed_at = parse_github_datetime(author_block.get("date"))
        if committed_at is None:
            continue

        existing = db.scalar(
            select(Commit).where(Commit.sha == sha, Commit.repo_id == repo.id)
        )
        message = (commit_block.get("message") or "")[:4000]
        author_login = github_author.get("login")
        author_name = author_block.get("name")

        if existing:
            existing.author_login = author_login
            existing.author_name = author_name
            existing.message = message
            existing.committed_at = committed_at
            existing.repo_id = repo.id
        else:
            db.add(
                Commit(
                    sha=sha,
                    repo_id=repo.id,
                    author_login=author_login,
                    author_name=author_name,
                    message=message,
                    committed_at=committed_at,
                )
            )
        count += 1
    db.flush()
    return count


def _upsert_pull_requests(db: Session, repo: TrackedRepository, items: list[dict]) -> int:
    count = 0
    for item in items:
        number = item.get("number")
        github_id = item.get("id")
        if number is None or github_id is None:
            continue
        created_at = parse_github_datetime(item.get("created_at"))
        if created_at is None:
            continue
        user = item.get("user") or {}
        existing = db.scalar(
            select(PullRequest).where(
                PullRequest.repo_id == repo.id,
                PullRequest.number == number,
            )
        )
        fields = {
            "github_id": github_id,
            "title": (item.get("title") or "")[:512],
            "author_login": user.get("login"),
            "state": item.get("state") or "open",
            "created_at": created_at,
            "merged_at": parse_github_datetime(item.get("merged_at")),
            "closed_at": parse_github_datetime(item.get("closed_at")),
        }
        if existing:
            for key, value in fields.items():
                setattr(existing, key, value)
        else:
            db.add(PullRequest(repo_id=repo.id, number=number, **fields))
        count += 1
    db.flush()
    return count


def _upsert_issues(db: Session, repo: TrackedRepository, items: list[dict]) -> int:
    count = 0
    for item in items:
        if item.get("pull_request") is not None:
            continue
        number = item.get("number")
        github_id = item.get("id")
        if number is None or github_id is None:
            continue
        created_at = parse_github_datetime(item.get("created_at"))
        if created_at is None:
            continue
        user = item.get("user") or {}
        existing = db.scalar(
            select(Issue).where(Issue.repo_id == repo.id, Issue.number == number)
        )
        fields = {
            "github_id": github_id,
            "title": (item.get("title") or "")[:512],
            "author_login": user.get("login"),
            "state": item.get("state") or "open",
            "created_at": created_at,
            "closed_at": parse_github_datetime(item.get("closed_at")),
        }
        if existing:
            for key, value in fields.items():
                setattr(existing, key, value)
        else:
            db.add(Issue(repo_id=repo.id, number=number, **fields))
        count += 1
    db.flush()
    return count


def _upsert_languages(db: Session, repo: TrackedRepository, languages: dict[str, int]) -> int:
    # Replace snapshot for this repo
    existing = list(db.scalars(select(RepoLanguage).where(RepoLanguage.repo_id == repo.id)).all())
    for row in existing:
        db.delete(row)
    db.flush()
    for language, byte_count in languages.items():
        db.add(
            RepoLanguage(
                repo_id=repo.id,
                language=language[:128],
                bytes=int(byte_count),
            )
        )
    db.flush()
    return len(languages)


def _upsert_workflow_runs(db: Session, repo: TrackedRepository, items: list[dict]) -> int:
    count = 0
    for item in items:
        run_id = item.get("id")
        if run_id is None:
            continue
        started = parse_github_datetime(item.get("run_started_at") or item.get("created_at"))
        updated = parse_github_datetime(item.get("updated_at"))
        duration = None
        if started and updated:
            duration = max(0.0, (updated - started).total_seconds())

        existing = db.scalar(select(WorkflowRun).where(WorkflowRun.github_run_id == run_id))
        fields = {
            "repo_id": repo.id,
            "name": (item.get("name") or item.get("display_title") or "workflow")[:255],
            "status": item.get("status") or "unknown",
            "conclusion": item.get("conclusion"),
            "html_url": item.get("html_url"),
            "run_started_at": started,
            "updated_at": updated,
            "duration_seconds": duration,
        }
        if existing:
            for key, value in fields.items():
                setattr(existing, key, value)
        else:
            db.add(WorkflowRun(github_run_id=run_id, **fields))
        count += 1
    db.flush()
    return count


def _enrich_pr_reviews(db: Session, repo: TrackedRepository, client: GitHubClient) -> int:
    """Fetch first review timestamp for a capped set of recent PRs."""
    prs = list(
        db.scalars(
            select(PullRequest)
            .where(PullRequest.repo_id == repo.id)
            .order_by(PullRequest.created_at.desc())
            .limit(MAX_PR_REVIEW_LOOKUPS)
        ).all()
    )
    updated = 0
    for pr in prs:
        try:
            reviews = client.fetch_pull_reviews(repo.owner, repo.name, pr.number)
        except Exception:
            logger.exception("Failed to fetch reviews for %s#%s", repo.full_name, pr.number)
            continue
        times = []
        for review in reviews:
            submitted = parse_github_datetime(review.get("submitted_at"))
            if submitted is not None:
                times.append(submitted)
        if times:
            pr.first_review_at = min(times)
            updated += 1
    db.flush()
    return updated
