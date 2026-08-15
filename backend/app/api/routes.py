from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import TrackedRepository
from app.schemas import (
    CommitCountPoint,
    ContributorStat,
    PRTurnaroundItem,
    RepositoryOut,
    SyncResponse,
    TrackReposRequest,
)
from app.services import stats_service, sync_service
from app.services.github_client import GitHubRateLimitError

router = APIRouter()


@router.post("/repos", response_model=list[RepositoryOut], status_code=status.HTTP_201_CREATED)
def track_repos(
    payload: TrackReposRequest, db: Session = Depends(get_db)
) -> list[TrackedRepository]:
    return sync_service.upsert_repositories(db, payload.repos)


@router.get("/repos", response_model=list[RepositoryOut])
def list_repos(db: Session = Depends(get_db)) -> list[TrackedRepository]:
    return list(db.scalars(select(TrackedRepository).order_by(TrackedRepository.full_name)).all())


@router.post("/sync", response_model=SyncResponse)
def sync_all(db: Session = Depends(get_db)) -> SyncResponse:
    try:
        results = sync_service.sync_all_repositories(db)
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
def sync_one(repo_id: int, db: Session = Depends(get_db)) -> SyncResponse:
    repo = db.get(TrackedRepository, repo_id)
    if repo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
    try:
        result = sync_service.sync_repository(db, repo)
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
    repo: str | None = Query(None, description="Filter by owner/repo"),
    period: str = Query("day", pattern="^(day|week)$"),
    db: Session = Depends(get_db),
) -> list[CommitCountPoint]:
    if repo and _repo_missing(db, repo):
        raise HTTPException(status_code=404, detail=f"Repository '{repo}' is not tracked")
    return stats_service.commits_over_time(db, repo=repo, period=period)


@router.get("/stats/pr-turnaround", response_model=list[PRTurnaroundItem])
def stats_pr_turnaround(
    repo: str | None = Query(None),
    db: Session = Depends(get_db),
) -> list[PRTurnaroundItem]:
    if repo and _repo_missing(db, repo):
        raise HTTPException(status_code=404, detail=f"Repository '{repo}' is not tracked")
    return stats_service.pr_turnaround(db, repo=repo)


@router.get("/stats/contributors", response_model=list[ContributorStat])
def stats_contributors(
    repo: str | None = Query(None),
    db: Session = Depends(get_db),
) -> list[ContributorStat]:
    if repo and _repo_missing(db, repo):
        raise HTTPException(status_code=404, detail=f"Repository '{repo}' is not tracked")
    return stats_service.contributor_activity(db, repo=repo)


def _repo_missing(db: Session, full_name: str) -> bool:
    return (
        db.scalar(select(TrackedRepository).where(TrackedRepository.full_name == full_name))
        is None
    )
