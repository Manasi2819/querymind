#!/bin/sh
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# backend/entrypoint.sh
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Container startup script.
#   1. Waits for the database to be reachable (with retry).
#   2. Runs Alembic migrations to keep the schema up-to-date.
#   3. Launches the Uvicorn server.
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

set -e

echo "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”"
echo "  QueryMind Backend â€” Container Startup"
echo "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”"

# â”€â”€ Step 1: Wait for the database â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
echo "â³ Waiting for database to be ready..."
python - <<'EOF'
import time
import sys
import os
from sqlalchemy import create_engine, text

db_url = os.getenv("DATABASE_URL", "sqlite:///./querymind_metadata.db")

# Skip wait for SQLite
if db_url.startswith("sqlite"):
    print("  â†’ SQLite detected. No wait needed.")
    sys.exit(0)

max_retries = 30
for attempt in range(1, max_retries + 1):
    try:
        engine = create_engine(db_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        print(f"  âœ… Database is ready (attempt {attempt})")
        sys.exit(0)
    except Exception as e:
        print(f"  [{attempt}/{max_retries}] DB not ready yet: {e}")
        time.sleep(3)

print("  âŒ Could not connect to database after maximum retries. Exiting.")
sys.exit(1)
EOF

# â”€â”€ Step 2: Run Alembic Migrations â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
echo "ðŸ”„ Running database migrations (alembic upgrade head)..."
alembic upgrade head && echo "  âœ… Migrations applied." || echo "  âš ï¸  Migration warning â€” continuing anyway."

# â”€â”€ Step 3: Start the API server â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
echo "ðŸš€ Starting QueryMind API server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
