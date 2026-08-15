from datetime import datetime, timedelta, timezone

from app.core.security import hash_password
from app.models import Commit, Issue, PullRequest, TrackedRepository, User
from app.services import insights_service


def test_repo_health_and_stale(db_session):
    now = datetime.now(timezone.utc)
    user = User(email="insight@example.com", password_hash=hash_password("password123"))
    db_session.add(user)
    db_session.flush()

    repo = TrackedRepository(
        user_id=user.id, owner="acme", name="demo", full_name="acme/demo"
    )
    db_session.add(repo)
    db_session.flush()
    db_session.add_all(
        [
            Commit(
                sha="d" * 40,
                repo_id=repo.id,
                author_login="alice",
                author_name="Alice",
                message="work",
                committed_at=now,
            ),
            PullRequest(
                github_id=99,
                number=7,
                repo_id=repo.id,
                title="Old open PR",
                author_login="bob",
                state="open",
                created_at=now - timedelta(days=30),
                merged_at=None,
                closed_at=None,
            ),
            Issue(
                github_id=100,
                number=3,
                repo_id=repo.id,
                title="Old issue",
                author_login="bob",
                state="open",
                created_at=now - timedelta(days=40),
                closed_at=None,
            ),
        ]
    )
    db_session.commit()

    health = insights_service.repo_health(db_session, user.id, repo="acme/demo")
    assert len(health) == 1
    assert health[0].stale_prs == 1
    assert health[0].stale_issues == 1
    assert 0 <= health[0].score <= 100

    stale = insights_service.stale_alerts(db_session, user.id, repo="acme/demo")
    assert stale.stale_days >= 1
    assert len(stale.items) == 2
