"""SQLModel database engine and session management."""
from __future__ import annotations

from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from valiant.config import settings

# SQLite needs check_same_thread=False for multi-threaded use
_connect_args = {"check_same_thread": False} if "sqlite" in settings.database_url else {}

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    echo=False,
)


def init_db() -> None:
    """Create all tables. Safe to call multiple times (no-op if tables exist)."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a DB session per request."""
    with Session(engine) as session:
        yield session
