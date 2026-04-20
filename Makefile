# ══════════════════════════════════════════════════════════════════════════════
#  QueryMind — Makefile
#  Convenience commands for the Docker Compose deployment.
#  Usage: make <command>
# ══════════════════════════════════════════════════════════════════════════════

.PHONY: up down logs restart build reset status shell-backend shell-mysql pull-model help

# ── Start the full stack (build + detached) ─────────────────────────────────
up:
	docker compose up --build -d
	@echo ""
	@echo "✅ QueryMind is starting up!"
	@echo "   Frontend : http://localhost"
	@echo "   API Docs : http://localhost:8000/docs"
	@echo "   Ollama   : http://localhost:11434"
	@echo ""
	@echo "Run 'make logs' to follow container output."

# ── Build images without starting ───────────────────────────────────────────
build:
	docker compose build --no-cache

# ── Stop all containers (keep volumes) ──────────────────────────────────────
down:
	docker compose down

# ── Follow live logs for all services ───────────────────────────────────────
logs:
	docker compose logs -f

# ── Follow logs for a specific service: make logs-backend ───────────────────
logs-backend:
	docker compose logs -f backend

logs-frontend:
	docker compose logs -f frontend

logs-mysql:
	docker compose logs -f mysql

logs-ollama:
	docker compose logs -f ollama

# ── Restart a single service: make restart s=backend ────────────────────────
restart:
	docker compose restart $(s)

# ── Show running container status ───────────────────────────────────────────
status:
	docker compose ps

# ── Open a shell inside the backend container ───────────────────────────────
shell-backend:
	docker exec -it querymind-backend /bin/bash

# ── Open a MySQL shell ───────────────────────────────────────────────────────
shell-mysql:
	docker exec -it querymind-mysql mysql -u querymind_user -p queryminddb

# ── Pull an Ollama model (inside the running container) ─────────────────────
# Usage: make pull-model model=llama3.2
pull-model:
	docker exec querymind-ollama ollama pull $(model)

# ── List downloaded Ollama models ───────────────────────────────────────────
list-models:
	docker exec querymind-ollama ollama list

# ── Run Alembic migration manually ──────────────────────────────────────────
migrate:
	docker exec querymind-backend alembic upgrade head

# ── DANGER: Remove all containers AND volumes (wipes all data!) ─────────────
reset:
	@echo "⚠️  WARNING: This will delete ALL containers, images, and data volumes!"
	@echo "   Press Ctrl+C within 5 seconds to cancel..."
	@sleep 5
	docker compose down -v --rmi local
	@echo "🗑️  Stack reset complete."

# ── Help ────────────────────────────────────────────────────────────────────
help:
	@echo "QueryMind Docker Commands:"
	@echo "  make up            — Build and start all services"
	@echo "  make build         — Rebuild images (no cache)"
	@echo "  make down          — Stop all containers"
	@echo "  make logs          — Follow all logs"
	@echo "  make logs-backend  — Follow backend logs only"
	@echo "  make status        — Show container health status"
	@echo "  make shell-backend — Open bash in backend container"
	@echo "  make shell-mysql   — Open MySQL shell"
	@echo "  make pull-model model=llama3.2:3b — Pull an Ollama model"
	@echo "  make list-models   — List downloaded Ollama models"
	@echo "  make migrate       — Run Alembic migrations"
	@echo "  make reset         — ⚠️  DESTROY all data and rebuild"
