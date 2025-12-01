.PHONY: help build up down restart logs shell db-shell migrate seed clean test test-cov test-unit test-integration

# Default target
help:
	@echo "FastBus Docker Commands"
	@echo "========================="
	@echo ""
	@echo "Basic Commands:"
	@echo "  build      - Build Docker images"
	@echo "  up         - Start all services"
	@echo "  down       - Stop all services"
	@echo "  restart    - Restart all services"
	@echo ""
	@echo "Logs & Shell:"
	@echo "  logs       - View application logs"
	@echo "  logs-db    - View database logs"
	@echo "  shell      - Open shell in web container"
	@echo "  db-shell   - Open PostgreSQL shell"
	@echo ""
	@echo "Database:"
	@echo "  migrate    - Run database migrations"
	@echo "  seed       - Seed database with sample data"
	@echo ""
	@echo "Testing:"
	@echo "  test       - Run all tests"
	@echo "  test-cov   - Run tests with coverage report"
	@echo "  test-unit  - Run unit tests only"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean      - Remove containers and volumes"

# Development commands
build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f web

logs-db:
	docker-compose logs -f db

shell:
	docker-compose exec web /bin/bash

db-shell:
	docker-compose exec db psql -U postgres -d tickethub

migrate:
	docker-compose exec web flask db upgrade

seed:
	docker-compose exec web python seed_db.py

# Testing commands
test:
	pytest

test-cov:
	pytest --cov=app --cov-report=html --cov-report=term

test-unit:
	pytest -m "not integration"

test-integration:
	pytest -m integration

# Cleanup commands
clean:
	docker-compose down -v
	docker system prune -f

