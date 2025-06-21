# {{cookiecutter.project_name}} - Development Makefile

.PHONY: help install install-dev setup clean test test-cov lint format type-check pre-commit run-dev run-prod build docker-build docker-run docker-up docker-down db-init db-create db-migrate db-upgrade db-downgrade db-reset db-fresh db-status db-info db-validate-models db-fix-models db-help deploy-dev deploy-prod

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
	@echo "Security:"
	@echo "  security-install    Install security scanning tools"
	@echo "  security-scan       Run all security scans"
	@echo "  security-report     Generate security reports"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build  Build Docker image"
	@echo "  docker-run    Run Docker container"
	@echo "  docker-up     Start Docker Compose services"
	@echo "  docker-down   Stop Docker Compose services"
	@echo ""
	@echo "Database:"
	@echo "  db-init       Initialize database migrations (first time setup)"
	@echo "  db-create     Create initial migration for all tables"
	@echo "  db-migrate    Generate new migration"
	@echo "  db-upgrade    Apply migrations"
	@echo "  db-downgrade  Rollback migration"
	@echo "  db-reset      Reset database (destructive)"
	@echo "  db-fresh      Fresh start (destructive)"
	@echo "  db-status     Check migration status"
	@echo "  db-info       Show database info"
	@echo "  db-help       Show detailed database commands"
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

# Security Commands
security-install:
	@echo "Installing security tools..."
	pip install safety bandit semgrep

security-scan:
	@echo "Running security scans..."
	@echo "1. Safety vulnerability scan..."
	safety scan || true
	@echo "2. Bandit code security scan..."
	bandit -r app/ || true
	@echo "3. Semgrep security patterns..."
	semgrep --config=auto app/ || true

security-report:
	@echo "Generating security reports..."
	mkdir -p reports/security
	safety scan --json > reports/security/safety-report.json || true
	bandit -r app/ -f json -o reports/security/bandit-report.json || true
	semgrep --config=auto --json --output=reports/security/semgrep-report.json app/ || true
	@echo "Security reports saved to reports/security/"

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

# Database Management
db-init:
	@echo "🚀 Initializing database migrations..."
	./scripts/database/migrate.sh init

db-create:
	@echo "📄 Creating initial migration..."
	./scripts/database/migrate.sh create-initial

db-migrate:
	@echo "🔨 Generating new migration..."
	@read -p "Migration message: " msg; \
	./scripts/database/migrate.sh generate "$$msg"

db-upgrade:
	@echo "⬆️  Upgrading database..."
	./scripts/database/migrate.sh upgrade

db-downgrade:
	@echo "⬇️  Downgrading database..."
	@read -p "Target revision (e.g., -1): " rev; \
	./scripts/database/migrate.sh downgrade "$$rev"

db-reset:
	@echo "🔄 Resetting database..."
	./scripts/database/migrate.sh reset

db-fresh:
	@echo "🆕 Fresh database start..."
	./scripts/database/migrate.sh fresh

db-status:
	@echo "📊 Checking migration status..."
	python scripts/database/migration_utils.py status

db-info:
	@echo "📋 Database information..."
	python scripts/database/migration_utils.py info

db-validate-models:
	@echo "🔍 Validating model imports..."
	./scripts/database/migrate.sh validate-models

db-fix-models:
	@echo "🔧 Fixing model imports..."
	./scripts/database/migrate.sh fix-models

db-help:
	@echo "Database Management Commands"
	@echo "============================"
	@echo "make db-init            - Initialize Alembic migrations"
	@echo "make db-create          - Create initial migration for all tables"
	@echo "make db-migrate         - Generate new migration (validates models first)"
	@echo "make db-upgrade         - Apply migrations"
	@echo "make db-downgrade       - Rollback migrations"
	@echo "make db-reset           - Reset database (destructive)"
	@echo "make db-fresh           - Fresh start (destructive)"
	@echo "make db-status          - Check migration status"
	@echo "make db-info            - Show database info"
	@echo "make db-validate-models - Validate model imports in __init__.py"
	@echo "make db-fix-models      - Auto-fix model imports in __init__.py"

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
