# Git Engineering Analytics Platform - Makefile

.PHONY: help build up down logs shell test clean

# Default target
help:
	@echo "Git Engineering Analytics Platform"
	@echo ""
	@echo "Available commands:"
	@echo "  make up          - Start all services"
	@echo "  make down        - Stop all services"
	@echo "  make build       - Build all Docker images"
	@echo "  make logs        - View logs from all services"
	@echo "  make shell       - Open shell in backend container"
	@echo "  make db-shell    - Open PostgreSQL shell"
	@echo "  make test        - Run tests"
	@echo "  make clean       - Clean up Docker resources"
	@echo "  make dev         - Start in development mode"

# Production commands
up:
	docker-compose up -d

down:
	docker-compose down

build:
	docker-compose build

logs:
	docker-compose logs -f

# Development commands
dev:
	docker-compose up postgres redis -d
	@echo "Database and Redis started. Run backend manually with:"
	@echo "cd backend && uvicorn app.main:app --reload"

shell:
	docker-compose exec backend bash

db-shell:
	docker-compose exec postgres psql -U postgres -d git_analyzer

# Testing
test:
	docker-compose exec backend python -m pytest

# Maintenance
clean:
	docker-compose down -v
	docker system prune -f

# Setup
setup:
	cp .env.example .env
	@echo "Environment file created. Please edit .env with your configuration."

# Database operations
db-migrate:
	docker-compose exec backend alembic upgrade head

db-reset:
	docker-compose down -v
	docker-compose up postgres -d
	sleep 5
	docker-compose exec backend alembic upgrade head