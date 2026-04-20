# ══════════════════════════════════════════════════════════════════════════════
#  QueryMind Backend — Dockerfile
#  Production-grade, CPU-optimized FastAPI image.
#
#  Layers (ordered for best cache reuse):
#    1. Base OS + system packages
#    2. CPU-only PyTorch (massive, isolated to its own layer)
#    3. Python dependencies from requirements.txt
#    4. Application source code
#    5. Healthcheck + entrypoint
# ══════════════════════════════════════════════════════════════════════════════

FROM python:3.11-slim-bookworm

# Prevent .pyc files and enable unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ── System Dependencies ──────────────────────────────────────────────────────
# curl: required for healthcheck
# build-essential + libpq-dev: required for psycopg2
# default-libmysqlclient-dev: required for mysqlclient
# pkg-config: required for building C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    default-libmysqlclient-dev \
    pkg-config \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# ── CPU-only PyTorch (kept in its own layer for caching) ───────────────────
# This avoids downloading CUDA drivers (~3GB) by using the cpu whl index.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# ── Python Dependencies ──────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application Source ───────────────────────────────────────────────────────
COPY . .

# ── Entrypoint Script ────────────────────────────────────────────────────────
# Use dos2unix to ensure LF line endings (required for Linux)
RUN dos2unix entrypoint.sh && chmod +x entrypoint.sh

# ── Healthcheck ─────────────────────────────────────────────────────────────
HEALTHCHECK --interval=15s --timeout=10s --start-period=40s --retries=5 \
    CMD curl -sf http://localhost:8000/ || exit 1

EXPOSE 8000

CMD ["sh", "./entrypoint.sh"]
