from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App config loaded from environment variables / .env file.

    DevOps note: secrets and connection strings never live in code.
    Local uses .env; Render/Vercel inject the same names in their dashboards.
    """

    model_config = SettingsConfigDict(
        # Prefer repo-root .env when running uvicorn from backend/
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg2://gitdash:gitdash@localhost:5432/gitdash"
    github_token: str = ""
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    sync_interval_minutes: int = 60
    stale_days: int = 14
    github_webhook_secret: str = ""
    uptime_check_url: str = "http://127.0.0.1:8000/health"
    uptime_interval_minutes: int = 5

    # Auth / multi-user
    jwt_secret: str = "dev-only-change-me-in-production"
    jwt_expire_minutes: int = 10080
    # Fernet key (url-safe base64 32-byte). Generate with Fernet.generate_key().
    token_encryption_key: str = ""
    bootstrap_admin_email: str = "admin@localhost"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
