#!/bin/bash
echo "Running database migrations..."
alembic upgrade head

echo "Starting Uvicorn..."
exec uvicorn main:app --host 127.0.0.1 --port 8000
