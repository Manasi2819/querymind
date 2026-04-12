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
import json
from datetime import datetime, date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from core.db_init import initialize_database
from config import get_settings

# Simple serializer for JSON columns to handle Timestamps/Datetimes
def sa_json_serializer(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    # Handle pandas Timestamps if pandas is installed
    try:
        import pandas as pd
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
    except ImportError:
        pass
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

logger = logging.getLogger(__name__)
settings = get_settings()

# Use centralized settings for the DB connection
DATABASE_URL: str = settings.database_url

# ── Step 1: Auto-create the database on the server if needed ─────────────────
initialize_database(DATABASE_URL)


def _build_engine(db_url: str):
    """
    Constructs a SQLAlchemy engine with dialect-appropriate settings.
    """
    url_lower = db_url.lower()
    
    # Common engine args
    engine_kwargs = {
        "json_serializer": lambda obj: json.dumps(obj, default=sa_json_serializer)
    }

    if url_lower.startswith("sqlite"):
        logger.info("[database] Using SQLite database.")
        return create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            **engine_kwargs
        )

    elif url_lower.startswith("mysql"):
        logger.info("[database] Using MySQL database.")
        return create_engine(
            db_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_size=10,
            max_overflow=20,
            **engine_kwargs
        )

    elif url_lower.startswith("postgresql") or url_lower.startswith("postgres"):
        logger.info("[database] Using PostgreSQL database.")
        return create_engine(
            db_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            **engine_kwargs
        )

    else:
        logger.warning(f"[database] Unknown dialect in DATABASE_URL. Using generic engine.")
        return create_engine(db_url, pool_pre_ping=True, **engine_kwargs)


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
