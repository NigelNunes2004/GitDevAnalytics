"""Heuristic secret / misconfig detectors for committed files.

Static detection only — redacts matched secrets; never logs raw values.
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass

SAFE_ENV_NAMES = {
    ".env.example",
    ".env.sample",
    ".env.template",
    ".env.placeholder",
}

RISKY_PATH_SUFFIXES = (
    ".pem",
    ".p12",
    ".pfx",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
)

RISKY_PATH_PARTS = (
    "/.env",
    "/credentials.json",
    "/aws/credentials",
    "/google-services.json",
    "/service-account.json",
)

AWS_KEY = re.compile(r"(?<![A-Z0-9])(AKIA[0-9A-Z]{16})(?![A-Z0-9])")
GITHUB_PAT = re.compile(r"\b(gh[pousr]_[A-Za-z0-9_]{20,})\b")
PRIVATE_KEY = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")
GENERIC_SECRET_ASSIGN = re.compile(
    r"(?i)\b(password|passwd|secret|api[_-]?key|token|access[_-]?key|private[_-]?key|"
    r"database_url|db_url|connection_string)\b\s*[=:]\s*['\"]?([^\s'\"]{8,})"
)


@dataclass
class RuleHit:
    source: str
    rule_id: str
    severity: str
    title: str
    detail: str
    path: str | None
    remediation: str
    fingerprint: str
    html_url: str | None = None


def _fp(*parts: str) -> str:
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]


def _redact(value: str) -> str:
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}…{value[-4:]}"


def _entropy(s: str) -> float:
    if not s:
        return 0.0
    freq: dict[str, int] = {}
    for ch in s:
        freq[ch] = freq.get(ch, 0) + 1
    length = len(s)
    return -sum((c / length) * math.log2(c / length) for c in freq.values())


def _basename(path: str) -> str:
    return path.replace("\\", "/").rsplit("/", 1)[-1]


def path_looks_risky(path: str) -> tuple[bool, str | None]:
    """Return (is_risky_path, rule_id). Safe example env names are not path-risky alone."""
    norm = path.replace("\\", "/").lower()
    base = _basename(norm)

    if base in SAFE_ENV_NAMES:
        return False, None

    if base == ".env" or base.startswith(".env."):
        return True, "path_dotenv"

    for suffix in RISKY_PATH_SUFFIXES:
        if base.endswith(suffix) or base == suffix:
            return True, "path_private_key_file"

    for part in RISKY_PATH_PARTS:
        if norm.endswith(part) or f"/{part.lstrip('/')}" in f"/{norm}":
            return True, "path_credentials_file"

    return False, None


def scan_path(path: str) -> list[RuleHit]:
    risky, rule_id = path_looks_risky(path)
    if not risky or not rule_id:
        return []

    if rule_id == "path_dotenv":
        return [
            RuleHit(
                source="diy",
                rule_id=rule_id,
                severity="critical",
                title="Environment file committed",
                detail=f"Path `{path}` looks like a live `.env` file (secrets often live here).",
                path=path,
                remediation=(
                    "Remove the file from the repo, rotate any exposed secrets, add `.env` to "
                    "`.gitignore`, and purge it from git history if it was ever pushed."
                ),
                fingerprint=_fp("diy", rule_id, path),
            )
        ]

    if rule_id == "path_private_key_file":
        return [
            RuleHit(
                source="diy",
                rule_id=rule_id,
                severity="critical",
                title="Private key / certificate file committed",
                detail=f"Path `{path}` matches a private key or certificate pattern.",
                path=path,
                remediation=(
                    "Remove the key from the repository, revoke/rotate it, and store secrets "
                    "outside git (password manager, CI secrets, or a vault)."
                ),
                fingerprint=_fp("diy", rule_id, path),
            )
        ]

    return [
        RuleHit(
            source="diy",
            rule_id=rule_id,
            severity="high",
            title="Credentials file committed",
            detail=f"Path `{path}` looks like a credentials document.",
            path=path,
            remediation=(
                "Remove the file, rotate credentials, and prefer environment variables or a "
                "secret manager."
            ),
            fingerprint=_fp("diy", rule_id, path),
        )
    ]


def scan_content(path: str, content: str) -> list[RuleHit]:
    hits: list[RuleHit] = []
    base = _basename(path).lower()

    # Skip huge binary-ish content
    if "\x00" in content[:2048]:
        return hits

    for match in AWS_KEY.finditer(content):
        value = match.group(1)
        hits.append(
            RuleHit(
                source="diy",
                rule_id="content_aws_access_key",
                severity="critical",
                title="AWS access key id detected",
                detail=f"Possible AWS key `{_redact(value)}` in `{path}`.",
                path=path,
                remediation=(
                    "Rotate the IAM key in AWS, remove it from git history, "
                    "and use IAM roles or env secrets."
                ),
                fingerprint=_fp("diy", "content_aws_access_key", path, value[-4:]),
            )
        )

    for match in GITHUB_PAT.finditer(content):
        value = match.group(1)
        hits.append(
            RuleHit(
                source="diy",
                rule_id="content_github_pat",
                severity="critical",
                title="GitHub personal access token detected",
                detail=f"Possible GitHub token `{_redact(value)}` in `{path}`.",
                path=path,
                remediation=(
                    "Revoke the PAT in GitHub settings immediately and store "
                    "tokens only in CI/secret managers."
                ),
                fingerprint=_fp("diy", "content_github_pat", path, value[-4:]),
            )
        )

    if PRIVATE_KEY.search(content):
        hits.append(
            RuleHit(
                source="diy",
                rule_id="content_private_key",
                severity="critical",
                title="Private key material detected",
                detail=f"PEM/OpenSSH private key header found in `{path}`.",
                path=path,
                remediation="Remove the key, rotate it, and never commit private keys.",
                fingerprint=_fp("diy", "content_private_key", path),
            )
        )

    for match in GENERIC_SECRET_ASSIGN.finditer(content):
        key, value = match.group(1), match.group(2)
        lower_val = value.lower()
        if lower_val in {
            "password",
            "secret",
            "changeme",
            "xxxxx",
            "your_token_here",
            "null",
            "none",
        }:
            continue
        if value.startswith("${") or value.startswith("{{"):
            continue
        # Prefer high-entropy or long values to reduce noise
        if len(value) < 12 and _entropy(value) < 3.0:
            continue
        # Example env files: only flag if value looks live
        if base in SAFE_ENV_NAMES and _entropy(value) < 3.5:
            continue
        hits.append(
            RuleHit(
                source="diy",
                rule_id="content_secret_assignment",
                severity="high",
                title=f"Possible secret assignment ({key})",
                detail=f"`{key}` appears assigned to `{_redact(value)}` in `{path}`.",
                path=path,
                remediation=(
                    "Move secrets to environment variables or a vault; "
                    "rotate if this was a real credential."
                ),
                fingerprint=_fp(
                    "diy", "content_secret_assignment", path, key.lower(), value[-4:]
                ),
            )
        )

    return hits


def should_fetch_content(path: str) -> bool:
    """Limit which blobs we download for content scanning."""
    norm = path.replace("\\", "/").lower()
    base = _basename(norm)
    if path_looks_risky(path)[0] or base in SAFE_ENV_NAMES:
        return True
    if base in {
        "config.json",
        "settings.py",
        "settings.json",
        "application.properties",
        "application.yml",
        "application.yaml",
        "docker-compose.yml",
        "docker-compose.yaml",
        ".npmrc",
        ".pypirc",
    }:
        return True
    if base.endswith(
        (".env", ".pem", ".key", ".yml", ".yaml", ".json", ".py", ".ts", ".js", ".toml", ".ini")
    ):
        return True
    return False
