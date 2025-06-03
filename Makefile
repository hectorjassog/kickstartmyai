# KickStartMyAI Development and Validation Makefile

.PHONY: help install dev-install test test-quick validate validate-quick \
        lint format security clean build publish validate-full \
        test-template test-generated check-deps

# Default target
help: ## Show this help message
	@echo "KickStartMyAI Development Commands"
	@echo "=================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation
install: ## Install the package
	pip install -e .

dev-install: ## Install development dependencies
	pip install -e .
	pip install -r requirements-dev.txt
	pre-commit install

# Testing
test: ## Run all tests
	pytest tests/ -v --cov=kickstartmyai --cov-report=html

test-quick: ## Run quick tests only
	pytest tests/unit/ -v

test-template: ## Test template generation
	python -m kickstartmyai.test_template

test-generated: ## Test generated project functionality
	python -c "from validate_production import KickStartMyAIValidator; v = KickStartMyAIValidator(verbose=True); exit(0 if v.validate_project_functionality() else 1)"

# Validation
validate: ## Run full production validation
	python validate_production.py --verbose

validate-quick: ## Run quick validation (no functionality tests)
	python validate_production.py --verbose --quick

validate-full: ## Run comprehensive validation with all checks
	@echo "🚀 Running comprehensive validation..."
	@echo "This may take 10-15 minutes..."
	python validate_production.py --verbose
	make security
	make lint
	@echo "✅ Full validation complete!"

# Code Quality
lint: ## Run linting checks
	black --check kickstartmyai/
	isort --check-only kickstartmyai/
	flake8 kickstartmyai/
	mypy kickstartmyai/

format: ## Format code
	black kickstartmyai/
	isort kickstartmyai/

security: ## Run security checks
	bandit -r kickstartmyai/ -f json -o bandit-report.json
	safety check --json --output safety-report.json
	@echo "Security reports generated: bandit-report.json, safety-report.json"

# Dependencies
check-deps: ## Check for dependency updates
	pip-audit
	pip list --outdated

# Build and Release
clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

build: clean ## Build distribution packages
	python -m build

publish-test: build ## Publish to Test PyPI
	python -m twine upload --repository testpypi dist/*

publish: build ## Publish to PyPI
	python -m twine upload dist/*

# Development Workflow
dev-setup: ## Set up development environment
	python -m venv .venv
	source .venv/bin/activate && make dev-install
	@echo "Development environment ready!"
	@echo "Activate with: source .venv/bin/activate"

pre-commit: ## Run pre-commit checks
	pre-commit run --all-files

# CI/CD Simulation
ci-test: ## Simulate CI testing locally
	@echo "🔍 Simulating CI pipeline locally..."
	make lint
	make security
	make test
	make validate-quick
	@echo "✅ CI simulation complete!"

# Template Testing Shortcuts
test-minimal: ## Test minimal template configuration
	python -c "
	import tempfile, json
	from pathlib import Path
	from validate_production import KickStartMyAIValidator
	
	config = {
		'project_name': 'Test Minimal',
		'project_slug': 'test_minimal',
		'project_description': 'Minimal test',
		'author_name': 'Test',
		'author_email': 'test@test.com',
		'version': '0.1.0',
		'include_docker': 'n',
		'include_redis': 'n',
		'database_type': 'sqlite'
	}
	
	v = KickStartMyAIValidator(verbose=True)
	with v.temp_directory() as temp_dir:
		project_dir = v._generate_project(temp_dir, config)
		v._validate_project_structure(project_dir)
		v._validate_python_syntax(project_dir)
	print('✅ Minimal template test passed')
	"

test-full-config: ## Test full-featured template configuration
	python -c "
	import tempfile, json
	from pathlib import Path
	from validate_production import KickStartMyAIValidator
	
	config = {
		'project_name': 'Test Full',
		'project_slug': 'test_full',
		'project_description': 'Full test',
		'author_name': 'Test',
		'author_email': 'test@test.com',
		'version': '0.1.0',
		'include_docker': 'y',
		'include_redis': 'y',
		'database_type': 'postgresql'
	}
	
	v = KickStartMyAIValidator(verbose=True)
	with v.temp_directory() as temp_dir:
		project_dir = v._generate_project(temp_dir, config)
		v._validate_project_structure(project_dir)
		v._validate_python_syntax(project_dir)
	print('✅ Full template test passed')
	"

# Documentation
docs-build: ## Build documentation
	@echo "Building documentation..."
	# Add documentation build commands here

docs-serve: ## Serve documentation locally
	@echo "Serving documentation..."
	# Add documentation serve commands here

# Release Workflow
release-check: ## Check if ready for release
	@echo "🔍 Checking release readiness..."
	make validate-full
	make test
	make security
	@echo "✅ Release checks passed!"

release-prep: ## Prepare for release
	@echo "📦 Preparing release..."
	make clean
	make release-check
	make build
	@echo "✅ Release preparation complete!"

# Development Utilities
generate-sample: ## Generate a sample project for testing
	@echo "Generating sample project..."
	mkdir -p samples/
	cd samples/ && cookiecutter ../kickstartmyai/templates --no-input

clean-samples: ## Clean sample projects
	rm -rf samples/

# Performance Testing
perf-test: ## Run performance tests
	@echo "⚡ Running performance tests..."
	time python validate_production.py --quick
	@echo "Template generation performance test complete"

# Database Testing
test-db: ## Test database configurations
	@echo "🗄️  Testing database configurations..."
	python -c "
	from validate_production import KickStartMyAIValidator
	
	configs = [
		{'database_type': 'sqlite'},
		{'database_type': 'postgresql'}
	]
	
	v = KickStartMyAIValidator(verbose=True)
	for config in configs:
		base_config = {
			'project_name': f'DB Test {config[\"database_type\"]}',
			'project_slug': f'db_test_{config[\"database_type\"]}',
			'project_description': 'Database test',
			'author_name': 'Test',
			'author_email': 'test@test.com',
			'version': '0.1.0',
			**config
		}
		
		with v.temp_directory() as temp_dir:
			project_dir = v._generate_project(temp_dir, base_config)
			v._validate_project_structure(project_dir)
		
		print(f'✅ {config[\"database_type\"]} configuration test passed')
	"

# Container Testing
test-docker: ## Test Docker functionality
	@echo "🐳 Testing Docker functionality..."
	python -c "
	from validate_production import KickStartMyAIValidator
	
	config = {
		'project_name': 'Docker Test',
		'project_slug': 'docker_test',
		'project_description': 'Docker test',
		'author_name': 'Test',
		'author_email': 'test@test.com',
		'version': '0.1.0',
		'include_docker': 'y'
	}
	
	v = KickStartMyAIValidator(verbose=True)
	with v.temp_directory() as temp_dir:
		project_dir = v._generate_project(temp_dir, config)
		v._test_docker_build(project_dir)
	
	print('✅ Docker test passed')
	"

# Monitoring
monitor-usage: ## Monitor template usage (requires analytics setup)
	@echo "📊 Template usage monitoring not yet implemented"
	@echo "This would show download stats, generation frequency, etc."

# Debugging
debug-template: ## Debug template generation
	@echo "🐛 Debug mode - generating template with verbose output"
	COOKIECUTTER_DEBUG=1 python validate_production.py --verbose

# All-in-one commands
ready: ## Check if everything is ready for production
	@echo "🚀 Checking production readiness..."
	make validate-full
	@echo "🎉 KickStartMyAI is ready for production!"

quick-check: ## Quick health check
	@echo "⚡ Quick health check..."
	make validate-quick
	make lint
	@echo "✅ Quick check complete!"
