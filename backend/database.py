from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from config import get_settings

settings = get_settings()

# Use SQLite by default if no postgres_url is fully configured
# For production, settings.postgres_url would be used.
# Since we want to be safe, let's allow an environment variable or default to local sqlite.
DB_URL = os.getenv("DATABASE_URL", "sqlite:///./querymind_metadata.db")

# If postgres prefix is found in the URL, use it, else use SQLite
if DB_URL.startswith("postgresql") or DB_URL.startswith("mysql"):
    engine = create_engine(DB_URL)
else:
    # SQLite needs special args for multi-threading
    engine = create_engine(DB_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
