import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import encrypt_secret, hash_password
from app.main import app
from app.models import User
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
    stop_scheduler()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client):
    """Register a user and return Authorization headers."""
    response = client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": "password123"},
    )
    assert response.status_code == 201
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def second_auth_headers(client):
    response = client.post(
        "/auth/register",
        json={"email": "bob@example.com", "password": "password123"},
    )
    assert response.status_code == 201
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def user_with_token(db_session, client):
    """Create a user that already has an encrypted GitHub PAT (skips live verify)."""
    user = User(
        email="pat@example.com",
        password_hash=hash_password("password123"),
        github_username="octocat",
        github_token_encrypted=encrypt_secret("ghp_test_token_not_real"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    login = client.post(
        "/auth/login",
        json={"email": "pat@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return user, {"Authorization": f"Bearer {token}"}
