# DataOps Dashboard Makefile
# Common commands for development and deployment

.PHONY: help install dev test lint format clean docker-up docker-down docker-logs migrate

# Default target
help:
	@echo "DataOps Dashboard - Available commands:"
	@echo ""
	@echo "  Development:"
	@echo "    make install     - Install all dependencies"
	@echo "    make dev         - Start development server"
	@echo "    make worker      - Start Celery worker"
	@echo "    make beat        - Start Celery beat scheduler"
	@echo ""
	@echo "  Testing:"
	@echo "    make test        - Run all tests"
	@echo "    make test-unit   - Run unit tests only"
	@echo "    make test-int    - Run integration tests only"
	@echo "    make coverage    - Run tests with coverage report"
	@echo ""
	@echo "  Code Quality:"
	@echo "    make lint        - Run linter (ruff)"
	@echo "    make format      - Format code (ruff)"
	@echo "    make type-check  - Run type checker (mypy)"
	@echo "    make security    - Run security scan (bandit)"
	@echo "    make check       - Run all quality checks"
	@echo ""
	@echo "  Docker:"
	@echo "    make docker-up   - Start all services"
	@echo "    make docker-down - Stop all services"
	@echo "    make docker-logs - View service logs"
	@echo "    make docker-build - Rebuild Docker images"
	@echo ""
	@echo "  Database:"
	@echo "    make db-shell    - Open Oracle SQL shell"
	@echo "    make db-reset    - Reset database (WARNING: deletes data)"
	@echo ""
	@echo "  Utilities:"
	@echo "    make clean       - Remove generated files"
	@echo "    make deps-update - Update dependencies"

# ==============================================
# Development
# ==============================================

install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

dev:
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

worker:
	celery -A src.workers.celery_app worker --loglevel=info

beat:
	celery -A src.workers.celery_app beat --loglevel=info

# ==============================================
# Testing
# ==============================================

test:
	pytest tests/ -v

test-unit:
	pytest tests/unit/ -v

test-int:
	pytest tests/integration/ -v

coverage:
	pytest tests/ --cov=src --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/index.html"

# ==============================================
# Code Quality
# ==============================================

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

type-check:
	mypy src/ --ignore-missing-imports

security:
	bandit -r src/ -c pyproject.toml

check: lint type-check security
	@echo "All quality checks passed!"

# ==============================================
# Docker
# ==============================================

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-build:
	docker-compose build --no-cache

docker-restart:
	docker-compose restart

# ==============================================
# Database
# ==============================================

db-shell:
	docker-compose exec oracle sqlplus dataops/DataOpsPass123@//localhost:1521/XEPDB1

db-reset:
	@echo "WARNING: This will delete all data!"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ]
	docker-compose down -v
	docker-compose up -d oracle
	@echo "Waiting for Oracle to initialize..."
	sleep 60
	docker-compose up -d

# ==============================================
# Utilities
# ==============================================

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	rm -rf build/ dist/ .eggs/

deps-update:
	pip install --upgrade pip
	pip install --upgrade -r requirements.txt
	pip install --upgrade -r requirements-dev.txt

# Create uploads directory if it doesn't exist
setup-dirs:
	mkdir -p uploads/temp uploads/reports

# Generate requirements from pyproject.toml (if using pip-tools)
compile-deps:
	pip-compile pyproject.toml -o requirements.txt
	pip-compile pyproject.toml --extra dev -o requirements-dev.txt
