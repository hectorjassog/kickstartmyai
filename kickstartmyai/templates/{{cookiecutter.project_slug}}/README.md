# {{cookiecutter.project_name}}

{{cookiecutter.project_description}}

🚀 **Built with KickStartMyAI** - A production-ready FastAPI template with AI integration, modern database setup, and comprehensive DevOps tooling.

## ✨ Features

- **🔥 FastAPI**: Modern, fast web framework for building APIs with automatic OpenAPI docs
- **🐘 PostgreSQL**: Robust relational database with async SQLAlchemy
- **🤖 AI Integration**: Ready-to-use AI capabilities with OpenAI, Anthropic, and more
- **☁️ AWS ECS Deployment**: Production-ready container orchestration
- **🏗️ Terraform Infrastructure**: Infrastructure as Code for reliable deployments
- **🧪 Comprehensive Testing**: Unit, integration, and E2E tests with pytest
- **🔐 Security**: JWT authentication, CORS, rate limiting, and security headers
- **📊 Monitoring**: Health checks, metrics, structured logging, and observability
- **🐳 Docker**: Containerized development and production environments
- **⚡ Redis**: Caching and session storage
- **🔄 Database Migrations**: Alembic for database versioning

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

The fastest way to get up and running:

```bash
# 1. Clone and navigate
git clone <repository-url>
cd {{cookiecutter.project_slug}}

# 2. Set up environment
cp .env.example .env
# Edit .env with your configuration (see Environment Variables section below)

# 3. Start all services
docker-compose up -d

# 4. Initialize database (first time only)
make db-init

# 5. Access your application
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### Option 2: Local Development

For local development without Docker:

```bash
# 1. Clone and navigate
git clone <repository-url>
cd {{cookiecutter.project_slug}}

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment
cp .env.example .env
# Edit .env with your database credentials

# 4. Start PostgreSQL and Redis
# (Install and start these services on your system)

# 5. Initialize database
make db-init

# 6. Start the application
make run-dev
```

## 🔧 Environment Setup

### Required Environment Variables

Copy `.env.example` to `.env` and configure these essential variables:

```bash
# Security (REQUIRED)
SECRET_KEY=your-super-secret-key-change-this-in-production

# Database (REQUIRED)
POSTGRES_PASSWORD=your-database-password

# AI Providers (Optional - add as needed)
OPENAI_API_KEY=your-openai-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here
GEMINI_API_KEY=your-gemini-api-key-here
```

### Full Configuration

See `.env.example` for all available configuration options including:
- Database connection settings
- Redis configuration
- AI provider settings
- Security and authentication
- Monitoring and logging
- Feature flags

## 🗄️ Database Setup

### First Time Setup

Use the included initialization script:

```bash
# This will:
# - Check your environment configuration
# - Test database connection
# - Create initial migration
# - Apply migrations to create tables
make db-init
```

### Working with Migrations

```bash
# Create a new migration
make db-migrate msg="Add user profile table"

# Apply pending migrations
make db-upgrade

# Rollback last migration
make db-downgrade

# Reset database (WARNING: Destructive!)
make db-reset
```

## 🛠️ Development Commands

Use the included Makefile for common development tasks:

```bash
# Setup
make install-dev          # Install development dependencies
make setup                # Complete development environment setup

# Development
make run-dev              # Start development server with hot reload
make run-prod             # Start production server
make clean                # Clean cache and temporary files

# Testing
make test                 # Run all tests
make test-cov             # Run tests with coverage report
make test-unit            # Run unit tests only
make test-integration     # Run integration tests only

# Code Quality
make lint                 # Run linters (flake8, mypy)
make format               # Format code (black, isort)
make type-check           # Run type checking

# Database
make db-init              # Initialize database (first time)
make db-migrate msg="..."  # Create new migration
make db-upgrade           # Apply migrations
make db-downgrade         # Rollback migration

# Docker
make docker-build         # Build production Docker image
make docker-up            # Start Docker Compose services
make docker-down          # Stop Docker Compose services
```

## 📁 Project Structure

```
{{cookiecutter.project_slug}}/
├── app/                    # Main application code
│   ├── api/               # API layer (FastAPI routes)
│   │   ├── v1/           # API version 1
│   │   └── middleware/   # Custom middleware
│   ├── core/             # Core functionality (config, security)
│   ├── models/           # SQLAlchemy database models
│   ├── schemas/          # Pydantic schemas for validation
│   ├── crud/             # Database operations
│   ├── ai/               # AI capabilities and providers
│   ├── services/         # Business logic layer
│   ├── db/               # Database configuration
│   └── main.py           # Application entry point
├── alembic/              # Database migrations
├── terraform/            # Infrastructure as Code
│   ├── modules/          # Reusable Terraform modules
│   └── environments/     # Environment-specific configs
├── scripts/              # Utility scripts
│   ├── database/         # Database management scripts
│   └── development/      # Development helpers
├── tests/                # Test suite
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   └── e2e/             # End-to-end tests
├── docker/               # Docker configurations
├── docs/                 # Documentation
└── requirements.txt      # Python dependencies
```

## 🤖 AI Capabilities

This project includes a powerful AI integration system:

- **Multi-Provider Support**: OpenAI, Anthropic Claude, Google Gemini, and extensible for more
- **Agent-Based Conversations**: Create and manage AI agents with different personalities
- **Tool Calling**: AI can execute functions and tools
- **Memory Management**: Conversation history and context preservation
- **Streaming Responses**: Real-time AI response streaming
- **Function Calling**: AI can call custom functions and APIs

### Quick AI Example

```python
from app.ai.providers import get_ai_provider

# Get an AI provider
provider = get_ai_provider("openai")

# Generate a response
response = await provider.generate_response(
    messages=[{"role": "user", "content": "Hello!"}],
    model="gpt-4"
)
```

## 🧪 Testing

Comprehensive testing setup included:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test types
pytest tests/unit/          # Fast unit tests
pytest tests/integration/   # Integration tests
pytest tests/e2e/          # End-to-end tests

# Run tests in parallel
pytest -n auto
```

## 🚀 Deployment

### AWS ECS with Terraform

Production deployment to AWS:

```bash
# 1. Configure AWS credentials
aws configure

# 2. Update variables
# Edit terraform/environments/prod/terraform.tfvars

# 3. Deploy infrastructure
cd terraform/environments/prod
terraform init
terraform plan
terraform apply
```

### Docker Production

```bash
# Build production image
make docker-build

# Run production container
docker run -p 8000:8000 --env-file .env {{cookiecutter.project_slug}}:latest
```

## 📚 API Documentation

Once running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 🔍 Monitoring & Health

Built-in monitoring endpoints:

- **Health Check**: `GET /health`
- **Metrics**: `GET /metrics` (if enabled)
- **Database Health**: Included in health checks
- **Redis Health**: Included in health checks

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Add tests for your changes
5. Run tests: `make test`
6. Format code: `make format`
7. Commit changes: `git commit -m 'Add amazing feature'`
8. Push to branch: `git push origin feature/amazing-feature`
9. Submit a pull request

## 🆘 Troubleshooting

### Common Issues

**Database Connection Issues:**
```bash
# Check if PostgreSQL is running
docker-compose ps

# View database logs
docker-compose logs postgres

# Test connection manually
python -c "from app.core.config import settings; print(settings.get_database_url())"
```

**Migration Issues:**
```bash
# Reset migrations (WARNING: Destructive)
make db-reset

# Check migration status
alembic current
alembic history
```

**Import Errors:**
```bash
# Ensure you're in the project root and virtual environment is activated
pip install -r requirements.txt
```

## 📄 License

[Add your license here]

## 🙋‍♂️ Support

- 📧 Email: [Add your email]
- 💬 Issues: Use GitHub Issues for bug reports and feature requests
- 📖 Documentation: Check the `/docs` folder for detailed documentation

---

**Generated with ❤️ by [KickStartMyAI](https://github.com/kickstartmyai/kickstartmyai)**
