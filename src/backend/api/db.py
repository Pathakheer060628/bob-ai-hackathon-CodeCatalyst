"""SQLAlchemy engine/session setup for the local SQLite persistence layer.

Runs are persisted to a single-file SQLite database at
`backend/data/gridsentinel.db` (gitignored -- it's local run history, not
the committed analytical dataset). `init_db()` creates the schema on app
startup; no separate migration framework is used since this is a single-file
SQLite store with one table.
"""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_DB_PATH = DATA_DIR / "gridsentinel.db"

# Allow overriding the DB location (e.g. ":memory:" or a temp file) for tests.
DATABASE_URL = os.environ.get("GRIDSENTINEL_DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str = DATABASE_URL):
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    if database_url.startswith("sqlite:///") and database_url != "sqlite:///:memory:":
        db_file = database_url.replace("sqlite:///", "", 1)
        Path(db_file).resolve().parent.mkdir(parents=True, exist_ok=True)
    return create_engine(database_url, connect_args=connect_args, future=True)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db(bind=None) -> None:
    """Create all tables if they don't already exist. Safe to call repeatedly."""
    # Import models here so they're registered on Base.metadata before create_all.
    from backend.api import models  # noqa: F401

    Base.metadata.create_all(bind or engine)
