from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


settings = get_settings()

# pool_pre_ping: drops dead connections (important after Render/Supabase idle timeouts)
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: one DB session per request, always closed afterward."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
