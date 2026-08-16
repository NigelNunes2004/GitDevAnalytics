from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


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
    workflow_runs_upserted: int = 0
    reviews_updated: int = 0
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


class RepoHealthScore(BaseModel):
    repo: str
    score: float
    commits_last_7_days: int
    open_prs: int
    stale_prs: int
    open_issues: int
    stale_issues: int
    recent_ci_failures: int


class StaleAlert(BaseModel):
    kind: str
    repo: str
    number: int
    title: str
    author: str | None
    age_days: float
    created_at: datetime


class StaleAlertsResponse(BaseModel):
    stale_days: int
    items: list[StaleAlert]


class WorkflowRunOut(BaseModel):
    repo: str
    name: str
    status: str
    conclusion: str | None
    html_url: str | None
    run_started_at: datetime | None
    duration_seconds: float | None


class ReviewLatencyItem(BaseModel):
    number: int
    title: str
    author: str | None
    hours_to_first_review: float
    days_to_first_review: float
    created_at: datetime
    first_review_at: datetime


class LanguageStat(BaseModel):
    language: str
    bytes: int
    percent: float


class CompareSide(BaseModel):
    repo: str
    commits: int
    contributors: int
    open_prs: int
    merged_prs: int
    avg_pr_turnaround_hours: float | None
    avg_review_latency_hours: float | None


class CompareResponse(BaseModel):
    a: CompareSide
    b: CompareSide


class UptimePoint(BaseModel):
    checked_at: datetime
    ok: bool
    latency_ms: float | None
    detail: str | None


class UptimeSummary(BaseModel):
    total_checks: int
    up_percent: float
    latest: UptimePoint | None
    recent: list[UptimePoint]


class WebhookAck(BaseModel):
    status: str
    detail: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    display_name: str | None = None
    avatar_url: str | None = None
    github_username: str | None = None
    token_configured: bool = False

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class GitHubSettingsOut(BaseModel):
    github_username: str | None
    token_configured: bool
    token_hint: str | None = None


class GitHubSettingsUpdate(BaseModel):
    github_token: str = Field(min_length=8, max_length=200)
    github_username: str | None = Field(default=None, max_length=255)


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=255)
    github_username: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = None


class VulnerabilityFindingOut(BaseModel):
    id: int
    repo: str
    source: str
    rule_id: str
    severity: str
    title: str
    detail: str | None = None
    path: str | None = None
    html_url: str | None = None
    remediation: str | None = None
    scanned_at: datetime

    model_config = {"from_attributes": True}


class VulnScanRepoResult(BaseModel):
    repo: str
    findings_count: int
    rate_limit_remaining: int | None = None


class VulnScanResponse(BaseModel):
    results: list[VulnScanRepoResult]
    findings: list[VulnerabilityFindingOut]


class CommitStatusOut(BaseModel):
    context: str
    state: str
    description: str | None = None
    target_url: str | None = None
    created_at: datetime | None = None


class CommitDiffOut(BaseModel):
    sha: str
    message: str
    author: str | None = None
    html_url: str | None = None
    additions: int = 0
    deletions: int = 0
    total: int = 0
    committed_at: datetime | None = None


class CommitStatusSummary(BaseModel):
    repo: str
    ref: str
    state: str
    sha: str
    message: str | None = None
    author: str | None = None
    html_url: str | None = None
    additions: int = 0
    deletions: int = 0
    total_count: int
    statuses: list[CommitStatusOut]
    recent_commits: list[CommitDiffOut] = []
    rate_limit_remaining: int | None = None


class DeploymentOut(BaseModel):
    id: int
    environment: str
    ref: str
    sha: str
    task: str
    description: str | None = None
    created_at: datetime | None = None
    latest_state: str | None = None
    latest_description: str | None = None
    latest_url: str | None = None


class NotificationOut(BaseModel):
    id: str
    reason: str
    unread: bool
    updated_at: datetime | None = None
    repo: str | None = None
    title: str
    type: str
    url: str | None = None
    latest_comment_url: str | None = None


class PackageOut(BaseModel):
    id: int
    name: str
    package_type: str
    visibility: str
    html_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class WorkflowTemplateOut(BaseModel):
    id: str
    name: str
    description: str
    path: str
    content: str


class WorkflowTemplateApplyRequest(BaseModel):
    repo: str = Field(min_length=3, max_length=512)
    template_id: str = Field(min_length=1, max_length=64)


class WorkflowTemplateApplyResult(BaseModel):
    repo: str
    branch: str
    path: str
    pr_number: int | None = None
    pr_url: str | None = None
    message: str

