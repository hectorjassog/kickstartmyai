# {{cookiecutter.project_name}}

{{cookiecutter.project_description}}

## Features

- **FastAPI**: Modern, fast web framework for building APIs
- **PostgreSQL**: Robust relational database
- **AI Integration**: Ready-to-use AI capabilities with multiple provider support
- **AWS ECS Deployment**: Production-ready container orchestration
- **Terraform Infrastructure**: Infrastructure as Code
- **Comprehensive Testing**: Unit, integration, and E2E tests
- **Security**: JWT authentication, CORS, rate limiting
- **Monitoring**: Health checks, metrics, and logging
- **Docker**: Containerized development and production environments

## Quick Start

### Development Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd {{cookiecutter.project_slug}}
```

2. Set up environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Run with Docker Compose:
```bash
docker-compose up -d
```

4. Access the application:
- API: http://localhost:8000
- Documentation: http://localhost:8000/docs
- Database: postgresql://localhost:5432/{{cookiecutter.database_name}}

### Manual Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up database:
```bash
python scripts/database/create_db.py
alembic upgrade head
```

3. Run the application:
```bash
python -m app.main
```

## Project Structure

```
{{cookiecutter.project_slug}}/
├── app/                    # Main application code
│   ├── api/               # API layer
│   ├── core/              # Core functionality
│   ├── models/            # Database models
│   ├── schemas/           # Pydantic schemas
│   ├── crud/              # Database operations
│   ├── ai/                # AI capabilities
│   └── services/          # Business logic
├── terraform/             # Infrastructure as Code
├── scripts/               # Utility scripts
├── tests/                 # Test suite
├── docker/                # Docker configurations
└── docs/                  # Documentation
```

## Environment Variables

See `.env.example` for all available configuration options.

Key variables:
- `SECRET_KEY`: Application secret key
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `OPENAI_API_KEY`: OpenAI API key (optional)
- `ANTHROPIC_API_KEY`: Anthropic API key (optional)

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run specific test types
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Run with coverage
pytest --cov=app tests/
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Code Quality

```bash
# Format code
black app/ tests/
isort app/ tests/

# Lint
flake8 app/ tests/
mypy app/

# Pre-commit hooks
pre-commit run --all-files
```

## Deployment

### AWS ECS with Terraform

1. Configure AWS credentials
2. Update Terraform variables in `terraform/environments/prod/terraform.tfvars`
3. Deploy infrastructure:

```bash
cd terraform/environments/prod
terraform init
terraform plan
terraform apply
```

### Docker

```bash
# Build production image
docker build -f docker/Dockerfile.prod -t {{cookiecutter.project_slug}}:latest .

# Run production container
docker run -p 8000:8000 {{cookiecutter.project_slug}}:latest
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## AI Capabilities

This project includes:
- Multi-provider AI integration (OpenAI, Anthropic, etc.)
- Agent-based conversation system
- Tool calling and function execution
- Memory management
- Streaming responses

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

[Add your license here]

## Support

[Add support information here]
