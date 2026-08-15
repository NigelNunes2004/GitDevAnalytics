import httpx
import pytest

from app.services.github_client import GitHubClient, GitHubRateLimitError


def test_request_retries_on_rate_limit(monkeypatch):
    """When remaining is 0, client raises GitHubRateLimitError after retries."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            headers={
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": "1",
            },
            json={"message": "API rate limit exceeded"},
            request=request,
        )

    transport = httpx.MockTransport(handler)

    original_client = httpx.Client

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", client_factory)
    # Avoid sleeping during tests
    monkeypatch.setattr("app.services.github_client.time.sleep", lambda _s: None)

    client = GitHubClient(token="test-token", max_retries=2)
    with pytest.raises(GitHubRateLimitError):
        client._request("GET", "https://api.github.com/rate_limit")
