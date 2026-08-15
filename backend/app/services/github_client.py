"""GitHub REST client with rate-limit awareness.

GitHub allows a fixed number of API requests per hour (typically 5,000 with a
Personal Access Token). Every response includes X-RateLimit-Remaining and
X-RateLimit-Reset. When we hit 403/429, we read those headers and either wait
briefly or surface a clear error instead of crashing the sync.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


class GitHubRateLimitError(Exception):
    def __init__(self, message: str, reset_at: int | None = None) -> None:
        super().__init__(message)
        self.reset_at = reset_at


class GitHubClient:
    def __init__(self, token: str | None = None, max_retries: int = 3) -> None:
        settings = get_settings()
        self.token = token if token is not None else settings.github_token
        self.max_retries = max_retries
        self.last_remaining: int | None = None
        if not self.token:
            raise ValueError(
                "GITHUB_TOKEN is not set. Add it to your .env (see .env.example)."
            )

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "git-activity-dashboard",
        }

    def _update_rate_limit(self, response: httpx.Response) -> None:
        remaining = response.headers.get("X-RateLimit-Remaining")
        if remaining is not None:
            self.last_remaining = int(remaining)
            logger.info("GitHub rate limit remaining: %s", self.last_remaining)

    def _request(self, method: str, url: str, params: dict[str, Any] | None = None) -> Any:
        delay = 1.0
        with httpx.Client(timeout=30.0, headers=self._headers()) as client:
            for attempt in range(self.max_retries):
                response = client.request(method, url, params=params)
                self._update_rate_limit(response)

                if response.status_code in (403, 429):
                    reset_header = response.headers.get("X-RateLimit-Reset")
                    reset_at = int(reset_header) if reset_header else None
                    # If GitHub says we have remaining quota, treat as secondary rate limit
                    remaining = response.headers.get("X-RateLimit-Remaining")
                    if remaining == "0" or response.status_code == 429:
                        wait = 1
                        if reset_at:
                            wait = max(1, min(reset_at - int(time.time()), 60))
                        if attempt < self.max_retries - 1 and wait <= 60:
                            logger.warning(
                                "Rate limited; sleeping %ss then retrying (%s/%s)",
                                wait,
                                attempt + 1,
                                self.max_retries,
                            )
                            time.sleep(wait)
                            continue
                        raise GitHubRateLimitError(
                            "GitHub API rate limit exceeded. Try again after the reset window.",
                            reset_at=reset_at,
                        )

                if response.status_code >= 500 and attempt < self.max_retries - 1:
                    logger.warning(
                        "GitHub %s; retrying in %ss (%s/%s)",
                        response.status_code,
                        delay,
                        attempt + 1,
                        self.max_retries,
                    )
                    time.sleep(delay)
                    delay *= 2
                    continue

                response.raise_for_status()
                return response.json()

        raise RuntimeError("GitHub request failed after retries")

    def _paginate(
        self, path: str, params: dict[str, Any] | None = None, max_pages: int = 5
    ) -> list[dict]:
        """Fetch up to max_pages of results (keeps demos fast / within rate limits)."""
        params = dict(params or {})
        params.setdefault("per_page", 100)
        items: list[dict] = []
        page = 1
        while page <= max_pages:
            params["page"] = page
            batch = self._request("GET", f"{GITHUB_API}{path}", params=params)
            if not isinstance(batch, list) or not batch:
                break
            items.extend(batch)
            if len(batch) < params["per_page"]:
                break
            page += 1
        return items

    def fetch_commits(self, owner: str, repo: str) -> list[dict]:
        return self._paginate(f"/repos/{owner}/{repo}/commits")

    def fetch_pull_requests(self, owner: str, repo: str) -> list[dict]:
        # state=all includes open + closed/merged
        return self._paginate(f"/repos/{owner}/{repo}/pulls", params={"state": "all"})

    def fetch_issues(self, owner: str, repo: str) -> list[dict]:
        # GitHub's issues endpoint also returns PRs; we filter those out in the sync service
        return self._paginate(f"/repos/{owner}/{repo}/issues", params={"state": "all"})

    def fetch_languages(self, owner: str, repo: str) -> dict[str, int]:
        data = self._request("GET", f"{GITHUB_API}/repos/{owner}/{repo}/languages")
        if not isinstance(data, dict):
            return {}
        return {str(k): int(v) for k, v in data.items()}

    def fetch_workflow_runs(self, owner: str, repo: str, per_page: int = 15) -> list[dict]:
        data = self._request(
            "GET",
            f"{GITHUB_API}/repos/{owner}/{repo}/actions/runs",
            params={"per_page": per_page},
        )
        if isinstance(data, dict):
            runs = data.get("workflow_runs") or []
            return runs if isinstance(runs, list) else []
        return []

    def fetch_pull_reviews(self, owner: str, repo: str, number: int) -> list[dict]:
        return self._paginate(
            f"/repos/{owner}/{repo}/pulls/{number}/reviews",
            params={"per_page": 50},
            max_pages=1,
        )


def parse_github_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    # GitHub returns ISO-8601 like 2024-01-01T12:00:00Z
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
