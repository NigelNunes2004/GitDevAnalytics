"""APScheduler background sync.

For a single FastAPI service this size, running a scheduler inside the same
process is enough — no Redis/Celery broker. Tradeoff: when Render free tier
spins the process down, the schedule pauses until the next request wakes it;
on-demand POST /sync still works.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.services.sync_service import sync_all_repositories

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def _scheduled_sync() -> None:
    logger.info("Starting scheduled GitHub sync")
    db = SessionLocal()
    try:
        results = sync_all_repositories(db)
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
    scheduler.start()
    logger.info("APScheduler started; sync every %s minute(s)", minutes)


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")
