"""Auth + Settings + scoped dashboard routes."""

from __future__ import annotations

import json

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    encrypt_secret,
    get_current_user,
    get_user_github_token,
    hash_password,
    mask_token,
    verify_password,
)
from app.models import TrackedRepository, User
from app.schemas import (
    CommitCountPoint,
    CommitStatusSummary,
    CompareResponse,
    ContributorStat,
    DeploymentOut,
    GitHubSettingsOut,
    GitHubSettingsUpdate,
    LanguageStat,
    LoginRequest,
    NotificationOut,
    PackageOut,
    ProfileUpdate,
    PRTurnaroundItem,
    RegisterRequest,
    RepoHealthScore,
    RepositoryOut,
    ReviewLatencyItem,
    StaleAlertsResponse,
    SyncResponse,
    TokenResponse,
    TrackReposRequest,
    UptimeSummary,
    UserOut,
    VulnerabilityFindingOut,
    VulnScanResponse,
    WebhookAck,
    WorkflowRunOut,
    WorkflowTemplateApplyRequest,
    WorkflowTemplateApplyResult,
    WorkflowTemplateOut,
)
from app.services import (
    export_service,
    github_extras_service,
    insights_service,
    stats_service,
    sync_service,
    uptime_service,
    vuln_service,
    webhook_service,
)
from app.services.github_client import GitHubRateLimitError

router = APIRouter()


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        github_username=user.github_username,
        token_configured=bool(user.github_token_encrypted),
    )


@router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id, user.email)
    return TokenResponse(access_token=token, user=_user_out(user))


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(user.id, user.email)
    return TokenResponse(access_token=token, user=_user_out(user))


@router.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return _user_out(user)


@router.get("/settings/github", response_model=GitHubSettingsOut)
def get_github_settings(user: User = Depends(get_current_user)) -> GitHubSettingsOut:
    hint = None
    if user.github_token_encrypted:
        try:
            hint = mask_token(get_user_github_token(user))
        except HTTPException:
            hint = "****"
    return GitHubSettingsOut(
        github_username=user.github_username,
        token_configured=bool(user.github_token_encrypted),
        token_hint=hint,
    )


@router.put("/settings/github", response_model=GitHubSettingsOut)
def put_github_settings(
    payload: GitHubSettingsUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GitHubSettingsOut:
    # Verify token against GitHub before saving
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {payload.github_token}",
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "git-activity-dashboard",
                },
            )
        if response.status_code >= 400:
            raise HTTPException(
                status_code=400,
                detail="GitHub rejected this token. Check the PAT and try again.",
            )
        gh_login = response.json().get("login")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not verify token: {exc}") from exc

    if payload.github_username and payload.github_username.strip():
        user.github_username = payload.github_username.strip()
    elif isinstance(gh_login, str) and gh_login:
        user.github_username = gh_login

    user.github_token_encrypted = encrypt_secret(payload.github_token.strip())
    db.add(user)
    db.commit()
    db.refresh(user)
    return GitHubSettingsOut(
        github_username=user.github_username,
        token_configured=True,
        token_hint=mask_token(payload.github_token.strip()),
    )


@router.put("/settings/profile", response_model=UserOut)
def put_profile(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UserOut:
    if payload.display_name is not None:
        name = payload.display_name.strip()
        user.display_name = name or None
    if payload.github_username is not None:
        uname = payload.github_username.strip()
        user.github_username = uname or None
    if payload.avatar_url is not None:
        avatar = payload.avatar_url.strip()
        if len(avatar) > 400_000:
            raise HTTPException(
                status_code=400,
                detail="Avatar too large. Use a smaller image (under ~300KB) or an image URL.",
            )
        user.avatar_url = avatar or None
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_out(user)


@router.post("/repos", response_model=list[RepositoryOut], status_code=status.HTTP_201_CREATED)
def track_repos(
    payload: TrackReposRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[TrackedRepository]:
    return sync_service.upsert_repositories(db, payload.repos, user_id=user.id)


@router.get("/repos", response_model=list[RepositoryOut])
def list_repos(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[TrackedRepository]:
    return list(
        db.scalars(
            select(TrackedRepository)
            .where(TrackedRepository.user_id == user.id)
            .order_by(TrackedRepository.full_name)
        ).all()
    )


@router.delete("/repos/{repo_id}")
def delete_repo(
    repo_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    full_name = sync_service.delete_repository(db, repo_id, user_id=user.id)
    if full_name is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
    return {"status": "deleted", "full_name": full_name}


@router.post("/sync", response_model=SyncResponse)
def sync_all(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SyncResponse:
    token = get_user_github_token(user)
    try:
        results = sync_service.sync_user_repositories(db, user, token)
    except GitHubRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
            headers={"Retry-After": str(max(1, (exc.reset_at or 0)))},
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return SyncResponse(results=results)


@router.post("/repos/{repo_id}/sync", response_model=SyncResponse)
def sync_one(
    repo_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SyncResponse:
    repo = db.scalar(
        select(TrackedRepository).where(
            TrackedRepository.id == repo_id,
            TrackedRepository.user_id == user.id,
        )
    )
    if repo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
    token = get_user_github_token(user)
    try:
        from app.services.github_client import GitHubClient

        result = sync_service.sync_repository(db, repo, client=GitHubClient(token=token))
    except GitHubRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return SyncResponse(results=[result])


@router.get("/stats/commits", response_model=list[CommitCountPoint])
def stats_commits(
    repo: str | None = Query(None),
    period: str = Query("day", pattern="^(day|week)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[CommitCountPoint]:
    _ensure_repo(db, user.id, repo)
    return stats_service.commits_over_time(db, user.id, repo=repo, period=period)


@router.get("/stats/pr-turnaround", response_model=list[PRTurnaroundItem])
def stats_pr_turnaround(
    repo: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[PRTurnaroundItem]:
    _ensure_repo(db, user.id, repo)
    return stats_service.pr_turnaround(db, user.id, repo=repo)


@router.get("/stats/contributors", response_model=list[ContributorStat])
def stats_contributors(
    repo: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ContributorStat]:
    _ensure_repo(db, user.id, repo)
    return stats_service.contributor_activity(db, user.id, repo=repo)


@router.get("/stats/health", response_model=list[RepoHealthScore])
def stats_health(
    repo: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[RepoHealthScore]:
    _ensure_repo(db, user.id, repo)
    return insights_service.repo_health(db, user.id, repo=repo)


@router.get("/stats/stale", response_model=StaleAlertsResponse)
def stats_stale(
    repo: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StaleAlertsResponse:
    _ensure_repo(db, user.id, repo)
    return insights_service.stale_alerts(db, user.id, repo=repo)


@router.get("/stats/ci", response_model=list[WorkflowRunOut])
def stats_ci(
    repo: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[WorkflowRunOut]:
    _ensure_repo(db, user.id, repo)
    return insights_service.workflow_runs(db, user.id, repo=repo)


@router.get("/stats/review-latency", response_model=list[ReviewLatencyItem])
def stats_review_latency(
    repo: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ReviewLatencyItem]:
    _ensure_repo(db, user.id, repo)
    return insights_service.review_latency(db, user.id, repo=repo)


@router.get("/stats/languages", response_model=list[LanguageStat])
def stats_languages(
    repo: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[LanguageStat]:
    _ensure_repo(db, user.id, repo)
    return insights_service.languages(db, user.id, repo=repo)


@router.get("/stats/compare", response_model=CompareResponse)
def stats_compare(
    repo_a: str = Query(...),
    repo_b: str = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CompareResponse:
    _ensure_repo(db, user.id, repo_a)
    _ensure_repo(db, user.id, repo_b)
    return insights_service.compare_repos(db, user.id, repo_a, repo_b)


@router.get("/export")
def export_data(
    repo: str | None = Query(None),
    format: str = Query("json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    _ensure_repo(db, user.id, repo)
    if format == "csv":
        body = export_service.export_csv(db, user.id, repo=repo)
        return Response(
            content=body,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=gitdash-export.csv"},
        )
    body = export_service.export_json(db, user.id, repo=repo)
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=gitdash-export.json"},
    )


@router.get("/uptime", response_model=UptimeSummary)
def uptime(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> UptimeSummary:
    return uptime_service.uptime_summary(db)


@router.post("/vuln/scan", response_model=VulnScanResponse)
def vuln_scan(
    repo: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> VulnScanResponse:
    _ensure_repo(db, user.id, repo)
    token = get_user_github_token(user)
    try:
        return vuln_service.scan_repositories(db, user, token, repo=repo)
    except GitHubRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
            headers={"Retry-After": str(max(1, (exc.reset_at or 0)))},
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/vuln/findings", response_model=list[VulnerabilityFindingOut])
def vuln_findings(
    repo: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[VulnerabilityFindingOut]:
    _ensure_repo(db, user.id, repo)
    return vuln_service.list_findings(db, user.id, repo=repo)


@router.get("/github/commit-status", response_model=CommitStatusSummary)
def github_commit_status(
    repo: str = Query(..., min_length=3),
    ref: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CommitStatusSummary:
    _ensure_repo(db, user.id, repo)
    token = get_user_github_token(user)
    try:
        return github_extras_service.commit_statuses(db, user, token, repo, ref=ref)
    except GitHubRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not load commit statuses (need repo:status?): {exc}",
        ) from exc


@router.get("/github/deployments", response_model=list[DeploymentOut])
def github_deployments(
    repo: str = Query(..., min_length=3),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[DeploymentOut]:
    _ensure_repo(db, user.id, repo)
    token = get_user_github_token(user)
    try:
        return github_extras_service.deployments(db, user, token, repo)
    except GitHubRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not load deployments (need repo_deployment?): {exc}",
        ) from exc


@router.get("/github/notifications", response_model=list[NotificationOut])
def github_notifications(
    include_read: bool = Query(False),
    user: User = Depends(get_current_user),
) -> list[NotificationOut]:
    token = get_user_github_token(user)
    try:
        return github_extras_service.notifications(
            token, all_notifications=include_read
        )
    except GitHubRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not load notifications (need notifications scope?): {exc}",
        ) from exc


@router.post("/settings/profile/from-github", response_model=UserOut)
def profile_from_github(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UserOut:
    token = get_user_github_token(user)
    try:
        updated = github_extras_service.enrich_profile_from_github(db, user, token)
    except GitHubRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not load GitHub profile (need read:user?): {exc}",
        ) from exc
    return _user_out(updated)


@router.get("/github/packages", response_model=list[PackageOut])
def github_packages(
    package_type: str = Query("npm"),
    user: User = Depends(get_current_user),
) -> list[PackageOut]:
    token = get_user_github_token(user)
    try:
        return github_extras_service.list_packages(token, package_type=package_type)
    except GitHubRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not load packages (need read:packages?): {exc}",
        ) from exc


@router.get("/github/workflow-templates", response_model=list[WorkflowTemplateOut])
def workflow_templates(
    _user: User = Depends(get_current_user),
) -> list[WorkflowTemplateOut]:
    return github_extras_service.list_workflow_templates()


@router.post("/github/workflow-templates/apply", response_model=WorkflowTemplateApplyResult)
def apply_workflow_template(
    payload: WorkflowTemplateApplyRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WorkflowTemplateApplyResult:
    _ensure_repo(db, user.id, payload.repo)
    token = get_user_github_token(user)
    try:
        return github_extras_service.apply_workflow_template(
            db, user, token, payload.repo, payload.template_id
        )
    except GitHubRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                f"Could not open workflow PR (need `workflow` + contents write): {exc}"
            ),
        ) from exc


@router.post("/webhooks/github", response_model=WebhookAck)
async def github_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
) -> WebhookAck:
    body = await request.body()
    if not webhook_service.verify_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    payload = json.loads(body.decode("utf-8") or "{}")
    return webhook_service.handle_webhook(db, x_github_event, payload)


def _ensure_repo(db: Session, user_id: int, full_name: str | None) -> None:
    if not full_name:
        return
    found = db.scalar(
        select(TrackedRepository).where(
            TrackedRepository.user_id == user_id,
            TrackedRepository.full_name == full_name,
        )
    )
    if found is None:
        raise HTTPException(
            status_code=404, detail=f"Repository '{full_name}' is not tracked"
        )
