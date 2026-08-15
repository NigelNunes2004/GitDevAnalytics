"""APScheduler: GitHub sync + uptime probes."""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.services.sync_service import sync_all_users_with_tokens
from app.services.uptime_service import run_uptime_probe

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def _scheduled_sync() -> None:
    logger.info("Starting scheduled per-user GitHub sync")
    db = SessionLocal()
    try:
        results = sync_all_users_with_tokens(db)
        for result in results:
            logger.info(
                "Synced %s (commits=%s prs=%s issues=%s remaining=%s)",
                result.repo,
                result.commits_upserted,
                result.pull_requests_upserted,
                result.issues_upserted,
                result.rate_limit_remaining,
            )
    except Exception:
        logger.exception("Scheduled sync failed")
    finally:
        db.close()


def start_scheduler() -> None:
    settings = get_settings()
    if scheduler.running:
        return
    minutes = max(1, settings.sync_interval_minutes)
    scheduler.add_job(
        _scheduled_sync,
        trigger="interval",
        minutes=minutes,
        id="github_sync",
        replace_existing=True,
    )
    uptime_minutes = max(1, settings.uptime_interval_minutes)
    scheduler.add_job(
        run_uptime_probe,
        trigger="interval",
        minutes=uptime_minutes,
        id="uptime_probe",
        replace_existing=True,
    )
    scheduler.start()
    # Immediate baseline probe so the panel isn't empty
    try:
        run_uptime_probe()
    except Exception:
        logger.exception("Initial uptime probe failed")
    logger.info(
        "APScheduler started; sync every %sm, uptime every %sm",
        minutes,
        uptime_minutes,
    )


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")
