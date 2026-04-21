# ══════════════════════════════════════════════════════════════════════════════
#  QueryMind — Single Container Dockerfile
#  Multi-stage build: Node (build frontend) → Python Slim (run Nginx + FastAPI)
# ══════════════════════════════════════════════════════════════════════════════

# ── Stage 1: Build Frontend ──────────────────────────────────────────────────
FROM node:20-alpine AS build-frontend

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci --prefer-offline

# Nginx handles routing so base URL is /
ARG VITE_API_URL=/
ENV VITE_API_URL=$VITE_API_URL

COPY frontend/ .
RUN npm run build

# ── Stage 2: Serve (Nginx + Uvicorn) ─────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (Nginx, Supervisor, C build tools for dependencies)
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    supervisor \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Setup backend Python environment
COPY backend/requirements.txt backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend source code
COPY backend/ backend/

# Replace the default nginx site with our custom config
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
RUN rm /etc/nginx/sites-enabled/default || true

# Copy built frontend assets from Stage 1 into Nginx HTML dir
RUN rm -rf /usr/share/nginx/html/*
COPY --from=build-frontend /app/frontend/dist /usr/share/nginx/html

# Copy Supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Setup volumes for persistence
RUN mkdir -p /app/data && \
    mkdir -p /app/chroma_db && \
    mkdir -p /app/uploads

EXPOSE 80

# Use supervisor to run both Nginx and Uvicorn
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
