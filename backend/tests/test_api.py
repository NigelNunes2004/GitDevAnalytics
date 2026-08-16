from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.models import Commit, PullRequest, TrackedRepository


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_repos_require_auth(client):
    assert client.get("/repos").status_code == 401
    assert client.post("/repos", json={"repos": ["octocat/Hello-World"]}).status_code == 401


def test_track_repos_validation(client, auth_headers):
    response = client.post("/repos", json={"repos": ["not-a-repo"]}, headers=auth_headers)
    assert response.status_code == 422


def test_track_repos_happy_path(client, auth_headers):
    response = client.post(
        "/repos", json={"repos": ["octocat/Hello-World"]}, headers=auth_headers
    )
    assert response.status_code == 201
    body = response.json()
    assert len(body) == 1
    assert body[0]["full_name"] == "octocat/Hello-World"

    listed = client.get("/repos", headers=auth_headers)
    assert listed.status_code == 200
    assert listed.json()[0]["full_name"] == "octocat/Hello-World"

    deleted = client.delete(f"/repos/{body[0]['id']}", headers=auth_headers)
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"
    assert client.get("/repos", headers=auth_headers).json() == []


def test_repo_isolation_between_users(client, auth_headers, second_auth_headers):
    client.post("/repos", json={"repos": ["octocat/Hello-World"]}, headers=auth_headers)
    client.post("/repos", json={"repos": ["octocat/Spoon-Knife"]}, headers=second_auth_headers)

    alice = client.get("/repos", headers=auth_headers).json()
    bob = client.get("/repos", headers=second_auth_headers).json()
    assert [r["full_name"] for r in alice] == ["octocat/Hello-World"]
    assert [r["full_name"] for r in bob] == ["octocat/Spoon-Knife"]


def test_stats_endpoints(client, db_session, auth_headers):
    me = client.get("/auth/me", headers=auth_headers).json()
    repo = TrackedRepository(
        user_id=me["id"], owner="acme", name="demo", full_name="acme/demo"
    )
    db_session.add(repo)
    db_session.flush()

    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            Commit(
                sha="a" * 40,
                repo_id=repo.id,
                author_login="alice",
                author_name="Alice",
                message="first",
                committed_at=now,
            ),
            Commit(
                sha="b" * 40,
                repo_id=repo.id,
                author_login="alice",
                author_name="Alice",
                message="second",
                committed_at=now - timedelta(days=1),
            ),
            Commit(
                sha="c" * 40,
                repo_id=repo.id,
                author_login="bob",
                author_name="Bob",
                message="third",
                committed_at=now,
            ),
            PullRequest(
                github_id=1,
                number=10,
                repo_id=repo.id,
                title="Speed up builds",
                author_login="alice",
                state="closed",
                created_at=now - timedelta(hours=48),
                merged_at=now - timedelta(hours=24),
                closed_at=now - timedelta(hours=24),
            ),
        ]
    )
    db_session.commit()

    commits = client.get(
        "/stats/commits",
        params={"repo": "acme/demo", "period": "day"},
        headers=auth_headers,
    )
    assert commits.status_code == 200
    assert sum(point["count"] for point in commits.json()) == 3

    contributors = client.get(
        "/stats/contributors",
        params={"repo": "acme/demo"},
        headers=auth_headers,
    )
    assert contributors.status_code == 200
    by_author = {row["author"]: row["commits"] for row in contributors.json()}
    assert by_author["alice"] == 2
    assert by_author["bob"] == 1

    turnaround = client.get(
        "/stats/pr-turnaround",
        params={"repo": "acme/demo"},
        headers=auth_headers,
    )
    assert turnaround.status_code == 200
    assert len(turnaround.json()) == 1
    assert turnaround.json()[0]["hours"] == pytest.approx(24.0, abs=0.1)


def test_register_login_and_bad_password(client):
    created = client.post(
        "/auth/register",
        json={"email": "new@example.com", "password": "password123"},
    )
    assert created.status_code == 201
    assert "access_token" in created.json()
    assert created.json()["user"]["email"] == "new@example.com"

    bad = client.post(
        "/auth/login",
        json={"email": "new@example.com", "password": "wrong-password"},
    )
    assert bad.status_code == 401

    ok = client.post(
        "/auth/login",
        json={"email": "new@example.com", "password": "password123"},
    )
    assert ok.status_code == 200
    assert ok.json()["access_token"]


def test_sync_without_token_returns_400(client, auth_headers):
    client.post("/repos", json={"repos": ["octocat/Hello-World"]}, headers=auth_headers)
    response = client.post("/sync", headers=auth_headers)
    assert response.status_code == 400
    assert "Settings" in response.json()["detail"]


def test_settings_save_masks_token(client, auth_headers):
    before = client.get("/settings/github", headers=auth_headers)
    assert before.status_code == 200
    assert before.json()["token_configured"] is False

    fake_user = MagicMock()
    fake_user.status_code = 200
    fake_user.json.return_value = {"login": "octocat"}

    with patch("app.api.routes.httpx.Client") as client_cls:
        instance = client_cls.return_value.__enter__.return_value
        instance.get.return_value = fake_user
        saved = client.put(
            "/settings/github",
            headers=auth_headers,
            json={"github_username": "octocat", "github_token": "ghp_secret_token_value"},
        )

    assert saved.status_code == 200
    body = saved.json()
    assert body["token_configured"] is True
    assert body["github_username"] == "octocat"
    assert body["token_hint"] is not None
    assert "secret_token_value" not in body["token_hint"]
    assert "ghp_secret_token_value" not in str(body)


def test_vuln_scan_diy_and_dependabot_soft_fail(client, auth_headers, db_session):
    from app.core.security import encrypt_secret
    from app.models import User

    # Persist a PAT so get_user_github_token succeeds
    me = client.get("/auth/me", headers=auth_headers).json()
    user = db_session.get(User, me["id"])
    assert user is not None
    user.github_token_encrypted = encrypt_secret("ghp_test_token_value_xx")
    db_session.add(user)
    db_session.commit()

    client.post("/repos", json={"repos": ["acme/demo"]}, headers=auth_headers)

    fake = MagicMock()
    fake.last_remaining = 4999
    fake.fetch_repo_meta.return_value = {"default_branch": "main"}
    fake._paginate.return_value = [
        {"sha": "abc", "commit": {"tree": {"sha": "treesha"}}}
    ]
    fake.fetch_git_tree.return_value = [
        {"type": "blob", "path": ".env", "size": 20},
        {"type": "blob", "path": "README.md", "size": 10},
    ]
    fake.fetch_file_text.side_effect = lambda owner, repo, path, ref: (
        "SECRET=ghp_abcdefghijklmnopqrstuvwxyz012345" if path == ".env" else None
    )
    fake.fetch_dependabot_alerts.return_value = ("forbidden", [])
    fake.fetch_secret_scanning_alerts.return_value = ("forbidden", [])

    with patch("app.services.vuln_service.GitHubClient", return_value=fake):
        response = client.post(
            "/vuln/scan",
            params={"repo": "acme/demo"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["results"][0]["repo"] == "acme/demo"
    severities = {f["severity"] for f in body["findings"]}
    assert "critical" in severities
    assert any(f["rule_id"] == "path_dotenv" for f in body["findings"])
    assert any(f["rule_id"] == "dependabot_unavailable" for f in body["findings"])
    # Secrets redacted
    assert all(
        "ghp_abcdefghijklmnopqrstuvwxyz012345" not in (f.get("detail") or "")
        for f in body["findings"]
    )
    listed = client.get("/vuln/findings", params={"repo": "acme/demo"}, headers=auth_headers)
    assert listed.status_code == 200
    assert len(listed.json()) >= 1
