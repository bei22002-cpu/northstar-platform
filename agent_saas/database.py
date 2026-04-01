"""SQLite database setup with SQLAlchemy."""

from __future__ import annotations

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from agent_saas.config import DATABASE_PATH


class Base(DeclarativeBase):
    pass


# Ensure the directory for the SQLite file exists
Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    f"sqlite:///{DATABASE_PATH}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency — yields a DB session and closes it after."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables."""
    from agent_saas import models as _m  # noqa: F401

    Base.metadata.create_all(bind=engine)
