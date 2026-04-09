"""
core/db_init.py
───────────────────────────────────────────────────────────────────────────────
Database Initialization Layer
──────────────────────────────
Detects the database dialect from DATABASE_URL and attempts to auto-create
the target database on the server (if it does not already exist).

Supported Dialects:
  - SQLite     → No action needed; SQLite creates its own file automatically.
  - MySQL      → Connects to MySQL server root and runs:
                   CREATE DATABASE IF NOT EXISTS <db_name>
                   CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
  - PostgreSQL → Connects to the 'postgres' default DB and creates the target
                   database using autocommit mode (required by Postgres).

Safety:
  - ALL database creation is wrapped in try/except.
  - On any permission or connection failure → logs a WARNING and continues.
  - NEVER crashes the application.
───────────────────────────────────────────────────────────────────────────────
"""

import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def _get_db_name_from_url(db_url: str) -> str:
    """Extracts just the database name from a SQLAlchemy URL string."""
    parsed = urlparse(db_url)
    # The path starts with '/', remove it to get the DB name
    return parsed.path.lstrip("/")


def _get_server_url(db_url: str) -> str:
    """
    Strips the database name from the URL so we can connect to the
    server root (without specifying a database), e.g.:
      mysql+pymysql://root:admin@localhost:3306/queryminddb
      → mysql+pymysql://root:admin@localhost:3306
    """
    parsed = urlparse(db_url)
    # Rebuild URL without the path (database name)
    port_part = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme}://{parsed.username}:{parsed.password}@{parsed.hostname}{port_part}"


def _init_mysql(db_url: str) -> None:
    """
    Attempts to create a MySQL database if it does not already exist.
    Connects to the MySQL server WITHOUT a database, then issues:
      CREATE DATABASE IF NOT EXISTS `<db_name>`
    """
    try:
        from sqlalchemy import create_engine, text

        db_name = _get_db_name_from_url(db_url)
        server_url = _get_server_url(db_url)

        logger.info(f"[db_init] MySQL detected. Attempting to create database '{db_name}' if not exists...")
        engine = create_engine(server_url, isolation_level="AUTOCOMMIT")
        with engine.connect() as conn:
            conn.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                    f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            )
        logger.info(f"[db_init] ✅ MySQL database '{db_name}' is ready.")
        engine.dispose()

    except Exception as e:
        logger.warning(
            f"[db_init] ⚠️  Could not auto-create MySQL database. "
            f"Please create it manually: CREATE DATABASE `{_get_db_name_from_url(db_url)}`;  "
            f"Error: {e}"
        )


def _init_postgresql(db_url: str) -> None:
    """
    Attempts to create a PostgreSQL database if it does not already exist.
    Postgres requires AUTOCOMMIT mode for CREATE DATABASE statements.
    Connects to the default 'postgres' catalog database first.
    """
    try:
        from sqlalchemy import create_engine, text

        db_name = _get_db_name_from_url(db_url)
        # Connect to the default 'postgres' system database
        server_url = _get_server_url(db_url) + "/postgres"

        logger.info(f"[db_init] PostgreSQL detected. Checking if database '{db_name}' exists...")
        engine = create_engine(server_url, isolation_level="AUTOCOMMIT")
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                {"db_name": db_name},
            )
            exists = result.fetchone()
            if not exists:
                logger.info(f"[db_init] Creating PostgreSQL database '{db_name}'...")
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                logger.info(f"[db_init] ✅ PostgreSQL database '{db_name}' created successfully.")
            else:
                logger.info(f"[db_init] ✅ PostgreSQL database '{db_name}' already exists.")
        engine.dispose()

    except Exception as e:
        logger.warning(
            f"[db_init] ⚠️  Could not auto-create PostgreSQL database. "
            f"Please create it manually: CREATE DATABASE \"{_get_db_name_from_url(db_url)}\";  "
            f"Error: {e}"
        )


def initialize_database(db_url: str) -> None:
    """
    Main entry point. Detects the DB dialect from the URL and runs
    the appropriate auto-creation routine.

    Args:
        db_url: Full SQLAlchemy database URL (e.g. from DATABASE_URL env var)

    Usage:
        from core.db_init import initialize_database
        initialize_database(os.getenv("DATABASE_URL", "sqlite:///./querymind_metadata.db"))
    """
    if not db_url:
        logger.warning("[db_init] DATABASE_URL is empty. Defaulting to SQLite.")
        return

    url_lower = db_url.lower()

    if url_lower.startswith("sqlite"):
        # SQLite creates its file automatically — nothing to do
        logger.info("[db_init] SQLite detected. No database creation needed.")
        return

    elif url_lower.startswith("mysql"):
        _init_mysql(db_url)

    elif url_lower.startswith("postgresql") or url_lower.startswith("postgres"):
        _init_postgresql(db_url)

    else:
        logger.warning(
            f"[db_init] Unknown database dialect in URL. "
            f"Please create the database manually before starting the server."
        )
