#!/bin/bash
cd /app/backend || exit 1

echo "Running database migrations..."
alembic upgrade head

echo "Starting Uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1

