# {{cookiecutter.project_name}} - Development Makefile

.PHONY: help install install-dev setup clean test test-cov lint format type-check pre-commit run-dev run-prod build docker-build docker-run docker-up docker-down db-create db-migrate db-upgrade db-downgrade db-reset deploy-dev deploy-prod

# Default target
help:
	@echo "{{cookiecutter.project_name}} Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  install       Install production dependencies"
	@echo "  install-dev   Install development dependencies"
	@echo "  setup         Complete development environment setup"
	@echo ""
	@echo "Development:"
	@echo "  run-dev       Start development server"
	@echo "  run-prod      Start production server"
	@echo "  clean         Clean cache and temporary files"
	@echo ""
	@echo "Testing:"
	@echo "  test          Run all tests"
	@echo "  test-cov      Run tests with coverage"
	@echo "  test-unit     Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint          Run linters"
	@echo "  format        Format code"
	@echo "  type-check    Run type checking"
	@echo "  pre-commit    Run pre-commit hooks"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build  Build Docker image"
	@echo "  docker-run    Run Docker container"
	@echo "  docker-up     Start Docker Compose services"
	@echo "  docker-down   Stop Docker Compose services"
	@echo ""
	@echo "Database:"
	@echo "  db-create     Create database"
	@echo "  db-migrate    Create new migration"
	@echo "  db-upgrade    Apply migrations"
	@echo "  db-downgrade  Rollback migration"
	@echo "  db-reset      Reset database"
	@echo ""
	@echo "Deployment:"
	@echo "  deploy-dev    Deploy to development"
	@echo "  deploy-prod   Deploy to production"

# Installation
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

setup:
	chmod +x scripts/development/setup-dev.sh
	./scripts/development/setup-dev.sh

# Development
run-dev:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

run-prod:
	uvicorn app.main:app --host 0.0.0.0 --port 8000

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -delete

# Testing
test:
	pytest

test-cov:
	pytest --cov=app --cov-report=html --cov-report=term

test-unit:
	pytest tests/unit/

test-integration:
	pytest tests/integration/

test-e2e:
	pytest tests/e2e/

# Code Quality
lint:
	flake8 app/ tests/
	mypy app/

format:
	black app/ tests/
	isort app/ tests/

type-check:
	mypy app/

pre-commit:
	pre-commit run --all-files

# Docker
docker-build:
	docker build -f docker/Dockerfile.prod -t {{cookiecutter.project_slug}}:latest .

docker-run:
	docker run -p 8000:8000 --env-file .env {{cookiecutter.project_slug}}:latest

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

# Database
db-create:
	python scripts/database/create_db.py

db-migrate:
	alembic revision --autogenerate -m "$(msg)"

db-upgrade:
	alembic upgrade head

db-downgrade:
	alembic downgrade -1

db-reset:
	python scripts/database/reset_db.py
	alembic upgrade head

# Deployment
deploy-dev:
	@echo "Deploying to development environment..."
	cd terraform/environments/dev && terraform apply

deploy-prod:
	@echo "Deploying to production environment..."
	cd terraform/environments/prod && terraform apply

# CI/CD helpers
ci-test:
	pytest --cov=app --cov-report=xml

ci-build:
	docker build -f docker/Dockerfile.prod -t {{cookiecutter.project_slug}}:$(VERSION) .

# Development shortcuts
dev: docker-up run-dev

prod: docker-build docker-run
