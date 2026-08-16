"""Orchestrate hybrid vulnerability scans for tracked repos."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import TrackedRepository, User, VulnerabilityFinding
from app.schemas import VulnerabilityFindingOut, VulnScanRepoResult, VulnScanResponse
from app.services import vuln_rules
from app.services.github_client import GitHubClient
from app.services.vuln_rules import RuleHit

logger = logging.getLogger(__name__)

MAX_CONTENT_FILES = 40
MAX_TREE_ENTRIES = 5000
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def _info_hit(rule_id: str, title: str, detail: str) -> RuleHit:
    return RuleHit(
        source="github",
        rule_id=rule_id,
        severity="info",
        title=title,
        detail=detail,
        path=None,
        remediation=(
            "Enable Dependabot / secret scanning on the repo, or widen your PAT "
            "(Dependabot alerts: Read, Secret scanning alerts: Read / security_events)."
        ),
        fingerprint=vuln_rules._fp("github", rule_id, ""),
    )


def _map_dependabot(alert: dict) -> RuleHit:
    number = alert.get("number")
    severity = str(
        (alert.get("security_advisory") or {}).get("severity")
        or (alert.get("security_vulnerability") or {}).get("severity")
        or "medium"
    ).lower()
    if severity not in SEVERITY_ORDER:
        severity = "medium"
    advisory = alert.get("security_advisory") or {}
    summary = advisory.get("summary") or "Dependabot dependency alert"
    pkg = ((alert.get("dependency") or {}).get("package") or {}).get("name")
    title = f"Dependabot: {pkg}" if pkg else f"Dependabot alert #{number}"
    html_url = alert.get("html_url")
    ghsa = advisory.get("ghsa_id") or ""
    return RuleHit(
        source="dependabot",
        rule_id=f"dependabot_{number or ghsa or 'alert'}",
        severity=severity,
        title=title,
        detail=str(summary),
        path=((alert.get("dependency") or {}).get("manifest_path")),
        remediation="Upgrade or replace the vulnerable dependency; review the advisory on GitHub.",
        fingerprint=vuln_rules._fp(
            "dependabot", str(number or ghsa), str(pkg or ""), str(html_url or "")
        ),
        html_url=html_url if isinstance(html_url, str) else None,
    )


def _map_secret_alert(alert: dict) -> RuleHit:
    number = alert.get("number")
    secret_type = alert.get("secret_type_display_name") or alert.get("secret_type") or "secret"
    html_url = alert.get("html_url")
    location = alert.get("first_location_detected") or {}
    path = location.get("path")
    return RuleHit(
        source="secret_scanning",
        rule_id=f"secret_scanning_{number or secret_type}",
        severity="critical",
        title=f"GitHub secret scanning: {secret_type}",
        detail="GitHub reported an open secret-scanning alert (value redacted by GitHub).",
        path=path if isinstance(path, str) else None,
        remediation="Revoke/rotate the secret immediately and remove it from git history.",
        fingerprint=vuln_rules._fp(
            "secret_scanning", str(number or ""), str(secret_type), str(path or "")
        ),
        html_url=html_url if isinstance(html_url, str) else None,
    )


def _diy_scan(client: GitHubClient, owner: str, name: str) -> list[RuleHit]:
    hits: list[RuleHit] = []
    meta = client.fetch_repo_meta(owner, name)
    default_branch = meta.get("default_branch") or "main"
    commits = client._paginate(
        f"/repos/{owner}/{name}/commits",
        params={"sha": default_branch, "per_page": 1},
        max_pages=1,
    )
    if not commits:
        return hits
    commit = commits[0]
    tree_sha = ((commit.get("commit") or {}).get("tree") or {}).get("sha")
    if not tree_sha:
        return hits

    tree = client.fetch_git_tree(owner, name, tree_sha)
    blobs = [
        item
        for item in tree[:MAX_TREE_ENTRIES]
        if isinstance(item, dict) and item.get("type") == "blob" and item.get("path")
    ]

    content_candidates: list[str] = []
    for item in blobs:
        path = str(item["path"])
        hits.extend(vuln_rules.scan_path(path))
        if vuln_rules.should_fetch_content(path):
            content_candidates.append(path)

    content_candidates.sort(key=lambda p: (0 if vuln_rules.path_looks_risky(p)[0] else 1, p))
    for path in content_candidates[:MAX_CONTENT_FILES]:
        text = client.fetch_file_text(owner, name, path, ref=default_branch)
        if text is None:
            continue
        hits.extend(vuln_rules.scan_content(path, text))

    return hits


def _github_native(client: GitHubClient, owner: str, name: str) -> list[RuleHit]:
    hits: list[RuleHit] = []

    dep_status, dep_alerts = client.fetch_dependabot_alerts(owner, name)
    if dep_status == "ok":
        hits.extend(_map_dependabot(alert) for alert in dep_alerts)
    elif dep_status in ("forbidden", "not_found"):
        hits.append(
            _info_hit(
                "dependabot_unavailable",
                "Dependabot alerts unavailable",
                "Could not read Dependabot alerts "
                "(not enabled, private visibility, or PAT missing scope).",
            )
        )

    sec_status, sec_alerts = client.fetch_secret_scanning_alerts(owner, name)
    if sec_status == "ok":
        hits.extend(_map_secret_alert(alert) for alert in sec_alerts)
    elif sec_status in ("forbidden", "not_found"):
        hits.append(
            _info_hit(
                "secret_scanning_unavailable",
                "Secret scanning alerts unavailable",
                "Could not read secret scanning alerts (feature off or PAT missing scope).",
            )
        )

    return hits


def _persist_hits(
    db: Session,
    user_id: int,
    repo: TrackedRepository,
    hits: list[RuleHit],
    scanned_at: datetime,
) -> list[VulnerabilityFinding]:
    db.execute(
        delete(VulnerabilityFinding).where(
            VulnerabilityFinding.user_id == user_id,
            VulnerabilityFinding.repo_id == repo.id,
        )
    )

    rows: list[VulnerabilityFinding] = []
    seen: set[str] = set()
    for hit in hits:
        if hit.fingerprint in seen:
            continue
        seen.add(hit.fingerprint)
        row = VulnerabilityFinding(
            user_id=user_id,
            repo_id=repo.id,
            source=hit.source,
            rule_id=hit.rule_id,
            severity=hit.severity,
            title=hit.title,
            detail=hit.detail,
            path=hit.path,
            html_url=hit.html_url,
            remediation=hit.remediation,
            fingerprint=hit.fingerprint,
            scanned_at=scanned_at,
        )
        db.add(row)
        rows.append(row)
    db.commit()
    for row in rows:
        db.refresh(row)
    return rows


def _to_out(row: VulnerabilityFinding, full_name: str) -> VulnerabilityFindingOut:
    return VulnerabilityFindingOut(
        id=row.id,
        repo=full_name,
        source=row.source,
        rule_id=row.rule_id,
        severity=row.severity,
        title=row.title,
        detail=row.detail,
        path=row.path,
        html_url=row.html_url,
        remediation=row.remediation,
        scanned_at=row.scanned_at,
    )


def list_findings(
    db: Session, user_id: int, repo: str | None = None
) -> list[VulnerabilityFindingOut]:
    stmt = (
        select(VulnerabilityFinding, TrackedRepository.full_name)
        .join(TrackedRepository, VulnerabilityFinding.repo_id == TrackedRepository.id)
        .where(VulnerabilityFinding.user_id == user_id)
    )
    if repo:
        stmt = stmt.where(TrackedRepository.full_name == repo)
    rows = db.execute(stmt).all()
    out = [_to_out(finding, full_name) for finding, full_name in rows]
    out.sort(key=lambda f: (SEVERITY_ORDER.get(f.severity, 9), f.repo, f.title))
    return out


def scan_repositories(
    db: Session, user: User, token: str, repo: str | None = None
) -> VulnScanResponse:
    stmt = select(TrackedRepository).where(TrackedRepository.user_id == user.id)
    if repo:
        stmt = stmt.where(TrackedRepository.full_name == repo)
    repos = list(db.scalars(stmt.order_by(TrackedRepository.full_name)).all())
    if not repos:
        return VulnScanResponse(results=[], findings=[])

    client = GitHubClient(token=token)
    scanned_at = datetime.now(timezone.utc)
    results: list[VulnScanRepoResult] = []
    all_findings: list[VulnerabilityFindingOut] = []

    for tracked in repos:
        owner, name = tracked.owner, tracked.name
        logger.info("Vulnerability scan %s", tracked.full_name)
        hits = _diy_scan(client, owner, name)
        hits.extend(_github_native(client, owner, name))
        rows = _persist_hits(db, user.id, tracked, hits, scanned_at)
        results.append(
            VulnScanRepoResult(
                repo=tracked.full_name,
                findings_count=len(rows),
                rate_limit_remaining=client.last_remaining,
            )
        )
        all_findings.extend(_to_out(r, tracked.full_name) for r in rows)

    all_findings.sort(key=lambda f: (SEVERITY_ORDER.get(f.severity, 9), f.repo, f.title))
    return VulnScanResponse(results=results, findings=all_findings)
