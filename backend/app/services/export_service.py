"""CSV/JSON export of stored aggregates."""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from sqlalchemy.orm import Session

from app.services import insights_service, stats_service


def build_export_payload(
    db: Session, user_id: int, repo: str | None = None
) -> dict[str, Any]:
    contributors = stats_service.contributor_activity(db, user_id, repo=repo)
    turnaround = stats_service.pr_turnaround(db, user_id, repo=repo)
    reviews = insights_service.review_latency(db, user_id, repo=repo)
    langs = insights_service.languages(db, user_id, repo=repo)
    return {
        "repo": repo or "all",
        "commits": [
            p.model_dump()
            for p in stats_service.commits_over_time(db, user_id, repo=repo)
        ],
        "contributors": [c.model_dump(mode="json") for c in contributors],
        "pr_turnaround": [p.model_dump(mode="json") for p in turnaround],
        "health": [
            h.model_dump() for h in insights_service.repo_health(db, user_id, repo=repo)
        ],
        "stale": insights_service.stale_alerts(db, user_id, repo=repo).model_dump(
            mode="json"
        ),
        "ci": [
            r.model_dump(mode="json")
            for r in insights_service.workflow_runs(db, user_id, repo=repo)
        ],
        "review_latency": [r.model_dump(mode="json") for r in reviews],
        "languages": [lang.model_dump() for lang in langs],
    }


def export_json(db: Session, user_id: int, repo: str | None = None) -> str:
    return json.dumps(
        build_export_payload(db, user_id, repo=repo), indent=2, default=str
    )


def export_csv(db: Session, user_id: int, repo: str | None = None) -> str:
    payload = build_export_payload(db, user_id, repo=repo)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["section", "key", "value"])

    for point in payload["commits"]:
        writer.writerow(["commits", point["date"], point["count"]])
    for row in payload["contributors"]:
        writer.writerow(["contributors", row["author"], row["commits"]])
    for row in payload["languages"]:
        writer.writerow(["languages", row["language"], row["percent"]])
    for row in payload["health"]:
        writer.writerow(["health_score", row["repo"], row["score"]])
    for row in payload["ci"]:
        writer.writerow(
            ["ci", f"{row['repo']}:{row['name']}", row.get("conclusion") or row["status"]]
        )
    return buf.getvalue()
