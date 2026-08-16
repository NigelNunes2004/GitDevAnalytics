from unittest.mock import MagicMock, patch

from app.core.security import encrypt_secret
from app.models import User
from app.services import github_extras_service
from app.services.workflow_templates import TEMPLATES


def _attach_token(client, auth_headers, db_session):
    me = client.get("/auth/me", headers=auth_headers).json()
    user = db_session.get(User, me["id"])
    assert user is not None
    user.github_token_encrypted = encrypt_secret("ghp_test_token_value_xx")
    db_session.add(user)
    db_session.commit()
    return me


def test_workflow_templates_listed(client, auth_headers):
    response = client.get("/github/workflow-templates", headers=auth_headers)
    assert response.status_code == 200
    ids = {row["id"] for row in response.json()}
    assert "ci-python" in ids
    assert len(TEMPLATES) == len(response.json())


def test_commit_status_endpoint(client, auth_headers, db_session):
    _attach_token(client, auth_headers, db_session)
    client.post("/repos", json={"repos": ["acme/demo"]}, headers=auth_headers)

    fake = MagicMock()
    fake.last_remaining = 100
    fake.fetch_repo_meta.return_value = {"default_branch": "main"}
    fake.fetch_combined_status.return_value = {
        "state": "success",
        "sha": "abc123def",
        "total_count": 1,
    }
    fake.fetch_commit.return_value = {
        "sha": "abc123def",
        "html_url": "https://github.com/acme/demo/commit/abc123def",
        "commit": {
            "message": "Fix login flow\n\nDetails here",
            "author": {"name": "Ada", "date": "2024-01-01T00:00:00Z"},
        },
        "stats": {"additions": 12, "deletions": 3, "total": 15},
        "author": {"login": "ada"},
    }
    fake.fetch_commits_on_ref.return_value = [{"sha": "abc123def"}]
    fake.fetch_commit_statuses.return_value = [
        {
            "context": "ci/tests",
            "state": "success",
            "description": "ok",
            "target_url": "https://example.com",
            "created_at": "2024-01-01T00:00:00Z",
        }
    ]

    with patch("app.services.github_extras_service.GitHubClient", return_value=fake):
        response = client.get(
            "/github/commit-status",
            params={"repo": "acme/demo"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "success"
    assert body["message"] == "Fix login flow"
    assert body["additions"] == 12
    assert body["deletions"] == 3
    assert body["statuses"][0]["context"] == "ci/tests"
    assert body["recent_commits"][0]["additions"] == 12


def test_profile_from_github(client, auth_headers, db_session):
    _attach_token(client, auth_headers, db_session)
    fake = MagicMock()
    fake.fetch_authenticated_user.return_value = {
        "login": "octocat",
        "name": "The Octocat",
        "avatar_url": "https://example.com/a.png",
    }
    with patch("app.services.github_extras_service.GitHubClient", return_value=fake):
        response = client.post("/settings/profile/from-github", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["github_username"] == "octocat"
    assert body["display_name"] == "The Octocat"
    assert body["avatar_url"] == "https://example.com/a.png"


def test_list_workflow_templates_service():
    templates = github_extras_service.list_workflow_templates()
    assert all(t.path.startswith(".github/workflows/") for t in templates)
