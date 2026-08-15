from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class TrackReposRequest(BaseModel):
    repos: list[str] = Field(..., min_length=1, description="List of owner/repo strings")

    @field_validator("repos")
    @classmethod
    def validate_repo_format(cls, repos: list[str]) -> list[str]:
        cleaned: list[str] = []
        for repo in repos:
            value = repo.strip()
            parts = value.split("/")
            if len(parts) != 2 or not parts[0] or not parts[1]:
                raise ValueError(f"Invalid repo format '{repo}'. Expected 'owner/repo'.")
            cleaned.append(f"{parts[0]}/{parts[1]}")
        return cleaned


class RepositoryOut(BaseModel):
    id: int
    owner: str
    name: str
    full_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SyncResult(BaseModel):
    repo: str
    commits_upserted: int
    pull_requests_upserted: int
    issues_upserted: int
    rate_limit_remaining: int | None = None


class SyncResponse(BaseModel):
    results: list[SyncResult]


class CommitCountPoint(BaseModel):
    date: str
    count: int


class ContributorStat(BaseModel):
    author: str
    commits: int


class PRTurnaroundItem(BaseModel):
    number: int
    title: str
    author: str | None
    hours: float
    days: float
    created_at: datetime
    merged_at: datetime


class HealthResponse(BaseModel):
    status: str
