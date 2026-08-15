"""GitHub webhook receiver (best-effort / advanced).

Uses the server GITHUB_TOKEN when present; syncs every tracked copy of that
full_name across users. Documented as global/advanced in the README.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import TrackedRepository
from app.schemas import WebhookAck
from app.services import sync_service
from app.services.github_client import GitHubClient

logger = logging.getLogger(__name__)


def verify_signature(body: bytes, signature_header: str | None) -> bool:
    settings = get_settings()
    secret = settings.github_webhook_secret
    if not secret:
        logger.warning("GITHUB_WEBHOOK_SECRET not set — skipping signature verification")
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    expected = f"sha256={digest}"
    return hmac.compare_digest(expected, signature_header)


def handle_webhook(db: Session, event: str | None, payload: dict[str, Any]) -> WebhookAck:
    repo_info = payload.get("repository") or {}
    full_name = repo_info.get("full_name")
    if not full_name or "/" not in full_name:
        return WebhookAck(status="ignored", detail="No repository.full_name in payload")

    interesting = {"push", "pull_request", "issues", "workflow_run", "ping"}
    if event == "ping":
        return WebhookAck(status="ok", detail="pong")
    if event not in interesting:
        return WebhookAck(status="ignored", detail=f"Unhandled event '{event}'")

    settings = get_settings()
    if not settings.github_token:
        return WebhookAck(
            status="ignored",
            detail="Server GITHUB_TOKEN not set; webhook sync skipped",
        )

    tracked = list(
        db.scalars(
            select(TrackedRepository).where(TrackedRepository.full_name == full_name)
        ).all()
    )
    if not tracked:
        return WebhookAck(status="ignored", detail=f"No user tracks {full_name}")

    try:
        client = GitHubClient(token=settings.github_token)
        details = []
        for repo in tracked:
            result = sync_service.sync_repository(db, repo, client=client)
            details.append(
                f"user={repo.user_id} commits={result.commits_upserted} "
                f"prs={result.pull_requests_upserted}"
            )
    except Exception as exc:
        logger.exception("Webhook sync failed for %s", full_name)
        return WebhookAck(status="error", detail=str(exc))

    return WebhookAck(status="synced", detail="; ".join(details))
