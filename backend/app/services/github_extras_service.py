"""Live GitHub extras: statuses, deployments, notifications, packages, workflow PRs."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import TrackedRepository, User
from app.schemas import (
    CommitDiffOut,
    CommitStatusOut,
    CommitStatusSummary,
    DeploymentOut,
    NotificationOut,
    PackageOut,
    WorkflowTemplateApplyResult,
    WorkflowTemplateOut,
)
from app.services.github_client import GitHubClient, parse_github_datetime
from app.services.workflow_templates import TEMPLATES


def _tracked(db: Session, user_id: int, full_name: str) -> TrackedRepository:
    repo = db.scalar(
        select(TrackedRepository).where(
            TrackedRepository.user_id == user_id,
            TrackedRepository.full_name == full_name,
        )
    )
    if repo is None:
        raise ValueError(f"Repository '{full_name}' is not tracked")
    return repo


def _commit_diff(row: dict) -> CommitDiffOut:
    commit = row.get("commit") or {}
    stats = row.get("stats") or {}
    author = (commit.get("author") or {}).get("name") or (row.get("author") or {}).get(
        "login"
    )
    message = str(commit.get("message") or "").strip() or "(no message)"
    # First line only for list views
    message_one = message.split("\n", 1)[0]
    return CommitDiffOut(
        sha=str(row.get("sha") or ""),
        message=message_one,
        author=str(author) if author else None,
        html_url=row.get("html_url"),
        additions=int(stats.get("additions") or 0),
        deletions=int(stats.get("deletions") or 0),
        total=int(stats.get("total") or 0),
        committed_at=parse_github_datetime((commit.get("author") or {}).get("date")),
    )


def commit_statuses(
    db: Session, user: User, token: str, full_name: str, ref: str | None = None
) -> CommitStatusSummary:
    repo = _tracked(db, user.id, full_name)
    client = GitHubClient(token=token)
    meta = client.fetch_repo_meta(repo.owner, repo.name)
    branch = ref or meta.get("default_branch") or "main"
    combined = client.fetch_combined_status(repo.owner, repo.name, branch)
    tip_sha = str(combined.get("sha") or "") or branch

    tip = client.fetch_commit(repo.owner, repo.name, tip_sha)
    tip_diff = _commit_diff(tip)

    # Recent commits: list SHAs then fetch detail (includes stats) for each
    listed = client.fetch_commits_on_ref(repo.owner, repo.name, branch, per_page=8)
    recent: list[CommitDiffOut] = []
    for row in listed:
        sha = str(row.get("sha") or "")
        if not sha:
            continue
        if sha == tip_diff.sha and tip.get("stats"):
            recent.append(tip_diff)
            continue
        detail = client.fetch_commit(repo.owner, repo.name, sha)
        recent.append(_commit_diff(detail))

    statuses_raw = client.fetch_commit_statuses(repo.owner, repo.name, branch)
    by_context: dict[str, dict] = {}
    for row in statuses_raw:
        ctx = str(row.get("context") or "default")
        if ctx not in by_context:
            by_context[ctx] = row
    items = [
        CommitStatusOut(
            context=str(s.get("context") or "default"),
            state=str(s.get("state") or "pending"),
            description=s.get("description"),
            target_url=s.get("target_url"),
            created_at=parse_github_datetime(s.get("created_at")),
        )
        for s in by_context.values()
    ]
    return CommitStatusSummary(
        repo=full_name,
        ref=branch,
        state=str(combined.get("state") or "pending"),
        sha=tip_diff.sha or tip_sha,
        message=tip_diff.message,
        author=tip_diff.author,
        html_url=tip_diff.html_url,
        additions=tip_diff.additions,
        deletions=tip_diff.deletions,
        total_count=int(combined.get("total_count") or len(items)),
        statuses=items,
        recent_commits=recent,
        rate_limit_remaining=client.last_remaining,
    )


def deployments(
    db: Session, user: User, token: str, full_name: str
) -> list[DeploymentOut]:
    repo = _tracked(db, user.id, full_name)
    client = GitHubClient(token=token)
    rows = client.fetch_deployments(repo.owner, repo.name)
    out: list[DeploymentOut] = []
    for dep in rows[:15]:
        dep_id = int(dep.get("id") or 0)
        statuses = client.fetch_deployment_statuses(repo.owner, repo.name, dep_id) if dep_id else []
        latest = statuses[0] if statuses else {}
        env = dep.get("environment")
        out.append(
            DeploymentOut(
                id=dep_id,
                environment=str(env) if env else "unknown",
                ref=str(dep.get("ref") or ""),
                sha=str(dep.get("sha") or ""),
                task=str(dep.get("task") or "deploy"),
                description=dep.get("description"),
                created_at=parse_github_datetime(dep.get("created_at")),
                latest_state=(str(latest.get("state")) if latest else None),
                latest_description=latest.get("description") if latest else None,
                latest_url=latest.get("environment_url") or latest.get("log_url"),
            )
        )
    return out


def notifications(token: str, all_notifications: bool = False) -> list[NotificationOut]:
    client = GitHubClient(token=token)
    rows = client.fetch_notifications(all_notifications=all_notifications)
    out: list[NotificationOut] = []
    for row in rows:
        repo = (row.get("repository") or {}).get("full_name")
        subject = row.get("subject") or {}
        out.append(
            NotificationOut(
                id=str(row.get("id") or ""),
                reason=str(row.get("reason") or ""),
                unread=bool(row.get("unread")),
                updated_at=parse_github_datetime(row.get("updated_at")),
                repo=str(repo) if repo else None,
                title=str(subject.get("title") or ""),
                type=str(subject.get("type") or ""),
                url=subject.get("url"),
                latest_comment_url=subject.get("latest_comment_url"),
            )
        )
    return out


def enrich_profile_from_github(db: Session, user: User, token: str) -> User:
    client = GitHubClient(token=token)
    gh = client.fetch_authenticated_user()
    login = gh.get("login")
    name = gh.get("name")
    avatar = gh.get("avatar_url")
    if isinstance(login, str) and login.strip():
        user.github_username = login.strip()
    if isinstance(name, str) and name.strip():
        user.display_name = name.strip()
    if isinstance(avatar, str) and avatar.strip():
        user.avatar_url = avatar.strip()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_packages(token: str, package_type: str = "npm") -> list[PackageOut]:
    client = GitHubClient(token=token)
    # Try a few common types; API requires one type per call
    types = [package_type] if package_type else ["npm", "container", "maven", "rubygems"]
    seen: set[str] = set()
    out: list[PackageOut] = []
    for ptype in types:
        for row in client.fetch_user_packages(package_type=ptype):
            name = str(row.get("name") or "")
            key = f"{ptype}:{name}"
            if not name or key in seen:
                continue
            seen.add(key)
            out.append(
                PackageOut(
                    id=int(row.get("id") or 0),
                    name=name,
                    package_type=str(row.get("package_type") or ptype),
                    visibility=str(row.get("visibility") or "unknown"),
                    html_url=row.get("html_url"),
                    created_at=parse_github_datetime(row.get("created_at")),
                    updated_at=parse_github_datetime(row.get("updated_at")),
                )
            )
    return out


def list_workflow_templates() -> list[WorkflowTemplateOut]:
    return [
        WorkflowTemplateOut(
            id=t["id"],
            name=t["name"],
            description=t["description"],
            path=t["path"],
            content=t["content"],
        )
        for t in TEMPLATES
    ]


def apply_workflow_template(
    db: Session,
    user: User,
    token: str,
    full_name: str,
    template_id: str,
) -> WorkflowTemplateApplyResult:
    template = next((t for t in TEMPLATES if t["id"] == template_id), None)
    if template is None:
        raise ValueError(f"Unknown template '{template_id}'")

    repo = _tracked(db, user.id, full_name)
    client = GitHubClient(token=token)
    meta = client.fetch_repo_meta(repo.owner, repo.name)
    base = str(meta.get("default_branch") or "main")
    base_sha = client.get_ref_sha(repo.owner, repo.name, base)
    if not base_sha:
        raise ValueError(f"Could not resolve default branch '{base}'")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    branch = f"gitdash/{template['id']}-{stamp}"
    client.create_branch(repo.owner, repo.name, branch, base_sha)
    client.create_or_update_file(
        repo.owner,
        repo.name,
        template["path"],
        template["content"],
        message=f"Add {template['name']} via GitDash",
        branch=branch,
    )
    pr = client.create_pull_request(
        repo.owner,
        repo.name,
        title=f"Add {template['name']}",
        head=branch,
        base=base,
        body=(
            f"This PR was opened by Git Activity Dashboard.\n\n"
            f"**Template:** {template['name']}\n\n"
            f"{template['description']}\n\n"
            "Requires a PAT with `workflow` (for `.github/workflows/*`) and repo contents write."
        ),
    )
    return WorkflowTemplateApplyResult(
        repo=full_name,
        branch=branch,
        path=template["path"],
        pr_number=int(pr.get("number") or 0) or None,
        pr_url=pr.get("html_url"),
        message="Pull request created with workflow template.",
    )
