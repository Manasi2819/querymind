"""
database.py
───────────────────────────────────────────────────────────────────────────────
SQLAlchemy engine, session, and base configuration.

This module is the single point of truth for database connectivity.
It supports SQLite, MySQL, and PostgreSQL via a single DATABASE_URL
environment variable.

On startup it:
  1. Calls `initialize_database()` to auto-create the target DB if needed.
  2. Builds the engine with dialect-specific optimizations.
  3. Exposes `Base`, `engine`, `SessionLocal`, and `get_db` for use across
     the entire application.
───────────────────────────────────────────────────────────────────────────────
"""

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from core.db_init import initialize_database

logger = logging.getLogger(__name__)

# ── Single source of truth for the DB connection ─────────────────────────────
# Override with any SQLAlchemy-compatible connection URL:
#   SQLite  : sqlite:///./querymind_metadata.db              (default)
#   MySQL   : mysql+pymysql://user:pass@localhost:3306/queryminddb
#   Postgres: postgresql+psycopg2://user:pass@host:5432/queryminddb
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./querymind_metadata.db")

# ── Step 1: Auto-create the database on the server if needed ─────────────────
initialize_database(DATABASE_URL)


def _build_engine(db_url: str):
    """
    Constructs a SQLAlchemy engine with dialect-appropriate settings.

    - SQLite   : check_same_thread=False (required for FastAPI multi-threading)
    - MySQL    : pool_recycle=3600 (prevents 'MySQL server has gone away' error)
    - Postgres : pool_pre_ping=True (validates connections before checkout)
    """
    url_lower = db_url.lower()

    if url_lower.startswith("sqlite"):
        logger.info("[database] Using SQLite database.")
        return create_engine(
            db_url,
            connect_args={"check_same_thread": False},
        )

    elif url_lower.startswith("mysql"):
        logger.info("[database] Using MySQL database.")
        return create_engine(
            db_url,
            pool_pre_ping=True,       # Detect stale connections
            pool_recycle=3600,        # Recycle connections every hour
            pool_size=10,             # Connection pool size
            max_overflow=20,          # Allow up to 20 extra connections
        )

    elif url_lower.startswith("postgresql") or url_lower.startswith("postgres"):
        logger.info("[database] Using PostgreSQL database.")
        return create_engine(
            db_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )

    else:
        # Fallback for other dialects (e.g. MSSQL, Oracle)
        logger.warning(f"[database] Unknown dialect in DATABASE_URL. Using generic engine.")
        return create_engine(db_url, pool_pre_ping=True)


# ── Step 2: Build engine and session factory ──────────────────────────────────
engine = _build_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ── ORM Base (shared across all models) ──────────────────────────────────────
Base = declarative_base()


# ── FastAPI dependency: yields a DB session per request ──────────────────────
def get_db():
    """
    FastAPI dependency injection for database sessions.
    Ensures the session is always closed after the request completes.

    Usage:
        @router.get("/")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
