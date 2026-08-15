"""Self uptime probes — record whether this API is reachable.

On Render free tier the process sleeps; these checks still help locally and on
always-on hosts. The dashboard charts recent latency and up percentage.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import UptimeCheck
from app.schemas import UptimePoint, UptimeSummary

logger = logging.getLogger(__name__)


def record_check(
    db: Session, ok: bool, latency_ms: float | None, detail: str | None = None
) -> UptimeCheck:
    row = UptimeCheck(
        checked_at=datetime.now(timezone.utc),
        ok=ok,
        latency_ms=latency_ms,
        detail=(detail or "")[:255] or None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def run_uptime_probe() -> None:
    settings = get_settings()
    url = settings.uptime_check_url
    db = SessionLocal()
    started = time.perf_counter()
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url)
        latency = (time.perf_counter() - started) * 1000.0
        ok = response.status_code < 500
        record_check(db, ok=ok, latency_ms=round(latency, 2), detail=f"HTTP {response.status_code}")
    except Exception as exc:
        latency = (time.perf_counter() - started) * 1000.0
        logger.warning("Uptime probe failed: %s", exc)
        record_check(db, ok=False, latency_ms=round(latency, 2), detail=str(exc)[:255])
    finally:
        db.close()


def uptime_summary(db: Session, limit: int = 48) -> UptimeSummary:
    rows = list(
        db.scalars(
            select(UptimeCheck).order_by(UptimeCheck.checked_at.desc()).limit(limit)
        ).all()
    )
    points = [
        UptimePoint(
            checked_at=row.checked_at,
            ok=row.ok,
            latency_ms=row.latency_ms,
            detail=row.detail,
        )
        for row in rows
    ]
    total = len(points)
    up = sum(1 for p in points if p.ok)
    return UptimeSummary(
        total_checks=total,
        up_percent=round(100.0 * up / total, 2) if total else 100.0,
        latest=points[0] if points else None,
        recent=list(reversed(points)),
    )
