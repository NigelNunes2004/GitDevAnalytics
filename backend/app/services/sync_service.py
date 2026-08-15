"""Orchestrates GitHub fetch → Postgres upsert."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Commit, Issue, PullRequest, TrackedRepository
from app.schemas import SyncResult
from app.services.github_client import GitHubClient, parse_github_datetime

logger = logging.getLogger(__name__)


def parse_full_name(full_name: str) -> tuple[str, str]:
    owner, name = full_name.split("/", 1)
    return owner, name


def upsert_repositories(db: Session, full_names: list[str]) -> list[TrackedRepository]:
    repos: list[TrackedRepository] = []
    for full_name in full_names:
        owner, name = parse_full_name(full_name)
        existing = db.scalar(
            select(TrackedRepository).where(TrackedRepository.full_name == full_name)
        )
        if existing:
            repos.append(existing)
            continue
        repo = TrackedRepository(owner=owner, name=name, full_name=full_name)
        db.add(repo)
        db.flush()
        repos.append(repo)
    db.commit()
    for repo in repos:
        db.refresh(repo)
    return repos


def sync_repository(
    db: Session, repo: TrackedRepository, client: GitHubClient | None = None
) -> SyncResult:
    client = client or GitHubClient()
    logger.info("Syncing %s", repo.full_name)

    commits_data = client.fetch_commits(repo.owner, repo.name)
    prs_data = client.fetch_pull_requests(repo.owner, repo.name)
    issues_data = client.fetch_issues(repo.owner, repo.name)

    commits_upserted = _upsert_commits(db, repo, commits_data)
    prs_upserted = _upsert_pull_requests(db, repo, prs_data)
    issues_upserted = _upsert_issues(db, repo, issues_data)
    db.commit()

    return SyncResult(
        repo=repo.full_name,
        commits_upserted=commits_upserted,
        pull_requests_upserted=prs_upserted,
        issues_upserted=issues_upserted,
        rate_limit_remaining=client.last_remaining,
    )


def sync_all_repositories(db: Session, client: GitHubClient | None = None) -> list[SyncResult]:
    repos = list(db.scalars(select(TrackedRepository)).all())
    if not repos:
        return []
    client = client or GitHubClient()
    return [sync_repository(db, repo, client=client) for repo in repos]


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

        existing = db.scalar(select(Commit).where(Commit.sha == sha))
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
        # Issues API returns pull requests too; skip those
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
