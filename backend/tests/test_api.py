from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models import Commit, PullRequest, TrackedRepository
from app.services.scheduler import stop_scheduler


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    # Avoid scheduler side effects during tests
    stop_scheduler()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_track_repos_validation(client):
    response = client.post("/repos", json={"repos": ["not-a-repo"]})
    assert response.status_code == 422


def test_track_repos_happy_path(client):
    response = client.post("/repos", json={"repos": ["octocat/Hello-World"]})
    assert response.status_code == 201
    body = response.json()
    assert len(body) == 1
    assert body[0]["full_name"] == "octocat/Hello-World"

    listed = client.get("/repos")
    assert listed.status_code == 200
    assert listed.json()[0]["full_name"] == "octocat/Hello-World"


def test_stats_endpoints(client, db_session):
    repo = TrackedRepository(owner="acme", name="demo", full_name="acme/demo")
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

    commits = client.get("/stats/commits", params={"repo": "acme/demo", "period": "day"})
    assert commits.status_code == 200
    assert sum(point["count"] for point in commits.json()) == 3

    contributors = client.get("/stats/contributors", params={"repo": "acme/demo"})
    assert contributors.status_code == 200
    by_author = {row["author"]: row["commits"] for row in contributors.json()}
    assert by_author["alice"] == 2
    assert by_author["bob"] == 1

    turnaround = client.get("/stats/pr-turnaround", params={"repo": "acme/demo"})
    assert turnaround.status_code == 200
    assert len(turnaround.json()) == 1
    assert turnaround.json()[0]["hours"] == pytest.approx(24.0, abs=0.1)
