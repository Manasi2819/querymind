"""
manage.py
───────────────────────────────────────────────────────────────────────────────
QueryMind Management CLI
──────────────────────────
A simple command-line wrapper to run common backend management tasks
without needing to remember full command syntax.

Commands:
  init-db                        Initialize the database (create DB + tables)
  migrate <SOURCE_URL> <TARGET>  Migrate data between databases

Usage:
  python manage.py init-db
  python manage.py migrate "sqlite:///./querymind_metadata.db" "mysql+pymysql://root:admin@localhost:3306/queryminddb"
───────────────────────────────────────────────────────────────────────────────
"""

import sys
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("manage")


def cmd_init_db():
    """Initializes the database using the current DATABASE_URL from .env."""
    db_url = os.getenv("DATABASE_URL", "sqlite:///./querymind_metadata.db")
    logger.info(f"[manage] Initializing database: {db_url}")

    # db_init: auto-create the database if needed
    from core.db_init import initialize_database
    initialize_database(db_url)

    # Create all tables using the ORM models
    from database import Base, engine
    from models import db_models  # noqa: F401  — ensures all models are registered

    logger.info("[manage] Creating tables via SQLAlchemy...")
    Base.metadata.create_all(bind=engine)
    logger.info("[manage] ✅ Database initialized successfully.")


def cmd_migrate(source_url: str, target_url: str):
    """Runs the full migration from source to target database."""
    from migrate_db import migrate
    migrate(source_url, target_url)


def main():
    args = sys.argv[1:]

    if not args:
        print("\nQueryMind Management CLI")
        print("────────────────────────")
        print("Commands:")
        print("  python manage.py init-db")
        print("  python manage.py migrate <SOURCE_URL> <TARGET_URL>")
        print()
        sys.exit(0)

    command = args[0]

    if command == "init-db":
        cmd_init_db()

    elif command == "migrate":
        if len(args) != 3:
            print("\nUsage: python manage.py migrate <SOURCE_URL> <TARGET_URL>")
            print('Example: python manage.py migrate "sqlite:///./querymind_metadata.db" "mysql+pymysql://root:admin@localhost:3306/queryminddb"')
            sys.exit(1)
        cmd_migrate(args[1], args[2])

    else:
        logger.error(f"Unknown command: '{command}'. Run 'python manage.py' for usage.")
        sys.exit(1)


if __name__ == "__main__":
    main()
