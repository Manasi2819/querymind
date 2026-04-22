# ══════════════════════════════════════════════════════════════════════════════
#  QueryMind — Optimized Single-Image Dockerfile
#  3-stage build:
#    Stage 1 (build-frontend) : Node  → compile React → dist/
#    Stage 2 (pip-builder)    : Python + build-essential → compile wheels
#    Stage 3 (final)          : Python slim → install wheels + copy dist/
#  Result: NO Nginx, NO Supervisor. Only uvicorn serves everything.
# ══════════════════════════════════════════════════════════════════════════════

# ── Stage 1: Build Frontend ───────────────────────────────────────────────────
FROM node:20-alpine AS build-frontend

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci --prefer-offline

# API calls go to /api/* — Vite base is / so React Router works
ARG VITE_API_URL=/
ENV VITE_API_URL=$VITE_API_URL

COPY frontend/ .
RUN npm run build

# ── Stage 2: Build Python Wheels ─────────────────────────────────────────────
# We compile ALL wheels here so build-essential never lands in the final image.
FROM python:3.11-slim AS pip-builder

WORKDIR /wheels

# Install C build tools ONLY in this throwaway stage
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .

# Force CPU-only PyTorch (saves ~400-600 MB vs the default GPU build)
RUN pip wheel --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt \
    -w /wheels

# ── Stage 3: Final Runtime Image ─────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Minimal runtime deps only — no build tools, no nginx, no supervisor
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install pre-compiled wheels (no compiler needed, no internet hit for packages)
COPY --from=pip-builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*.whl \
    && rm -rf /wheels

# Copy backend source
COPY backend/ backend/

# Copy React build output → backend/static/ (FastAPI will serve this)
COPY --from=build-frontend /app/frontend/dist backend/static/

# Create persistence directories (volumes will be mounted here)
RUN mkdir -p /app/data /app/chroma_db /app/uploads

# Update start.sh to bind on 0.0.0.0:8000 (not 127.0.0.1 which is localhost-only)
RUN sed -i 's/--host 127.0.0.1/--host 0.0.0.0/' /app/backend/start.sh || true

EXPOSE 8000

# Single process — no supervisor needed
CMD ["/bin/bash", "/app/backend/start.sh"]
