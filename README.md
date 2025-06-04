# 🚀 KickStartMyAI

**Production-Ready FastAPI Template for AI-Powered Applications**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

KickStartMyAI is a comprehensive Cookiecutter template that generates production-ready FastAPI applications with advanced AI agent capabilities, async database operations, comprehensive testing, and modern DevOps tooling. Get your AI-powered application up and running in minutes, not days.

## ✨ Features

### 🤖 AI & Machine Learning
- **Multi-Provider AI Support**: OpenAI, Anthropic Claude, Google Gemini
- **Advanced Agent System**: Conversational AI with memory and context
- **Function Calling**: Extensible tool framework for AI agents
- **Streaming Responses**: Real-time AI interactions with Server-Sent Events
- **Vector Embeddings**: Text similarity and semantic search capabilities
- **Cost Tracking**: Automatic token usage and cost monitoring per provider

### 🏗️ Core Infrastructure
- **FastAPI Framework**: High-performance async Python web framework
- **PostgreSQL Database**: Full async SQLAlchemy with Alembic migrations
- **Redis Caching**: Session management and performance optimization
- **JWT Authentication**: Secure user authentication with refresh tokens
- **Comprehensive CRUD**: Advanced querying, filtering, and pagination
- **API Documentation**: Auto-generated OpenAPI/Swagger documentation

### 🛠️ Tool Framework
- **Extensible Architecture**: Plugin-based tool system for AI agents
- **Built-in Tools**: Web search, code execution, file management, database queries
- **Security Layer**: Parameter validation and execution sandboxing
- **Concurrent Execution**: Parallel tool processing with timeout handling
- **Tool Registry**: Dynamic tool registration and management

### 🔒 Security & Monitoring
- **Production Security**: Rate limiting, CORS, security headers
- **Health Monitoring**: Comprehensive health checks and metrics
- **Structured Logging**: JSON-formatted logs with request tracing
- **Error Handling**: Graceful error recovery and user-friendly messages
- **Input Validation**: Pydantic schemas with comprehensive validation

### 🚀 DevOps & Deployment
- **Docker Support**: Multi-stage builds with production optimization
- **Terraform Infrastructure**: AWS deployment with best practices
- **GitHub Actions**: CI/CD pipeline with automated testing
- **Environment Management**: Configuration for dev, staging, production
- **Database Migrations**: Automated schema management with Alembic

### 🧪 Testing & Quality
- **Comprehensive Testing**: Unit, integration, E2E, and security tests
- **Template Validation**: Automated testing of template generation
- **Code Quality**: Pre-commit hooks, linting, and formatting
- **Performance Testing**: Load testing and benchmarking
- **Security Testing**: Vulnerability scanning and penetration testing

## 🚀 Quick Start

### Prerequisites

- Python 3.8+ 
- PostgreSQL 13+
- Docker (optional)
- Git

### 1. Install Cookiecutter

```bash
pip install cookiecutter
```

### 2. Generate Your Project

```bash
cookiecutter https://github.com/hectorjassog/kickstartmyai
```

### 3. Configure Your Project

Answer the prompts to customize your project:

```
project_name [My AI Project]: 
project_slug [my_ai_project]: 
description [An AI-powered FastAPI application]: 
author [Your Name]: 
email [your.email@example.com]: 
version [0.1.0]: 
include_docker [y]: 
include_redis [y]: 
include_terraform [y]: 
ai_providers [all]: 
```

### 4. Set Up Your Environment

```bash
cd my_ai_project

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Copy environment template
cp .env.example .env
```

### 5. Configure Environment Variables

Edit `.env` file with your settings:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/mydb

# AI Providers (add your API keys)
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# Security
SECRET_KEY=your-super-secret-key-here

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# Environment
ENVIRONMENT=development
DEBUG=true
```

### 6. Initialize Database

```bash
# Create database
createdb mydb

# Run migrations
alembic upgrade head

# Or use the provided script
make db-init
```

### 7. Start Your Application

```bash
# Development server
make dev

# Or directly with uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 8. Explore Your API

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Admin Panel**: http://localhost:8000/admin (if enabled)

## 📖 Documentation

### Project Structure

```
my_ai_project/
├── app/
│   ├── api/                    # API routes and endpoints
│   │   ├── middleware/         # Custom middleware
│   │   └── v1/endpoints/       # API version 1 endpoints
│   ├── ai/                     # AI and ML components
│   │   ├── providers/          # AI provider integrations
│   │   ├── services/           # AI orchestration services
│   │   └── tools/              # AI tool framework
│   ├── core/                   # Core application logic
│   │   ├── config.py           # Configuration management
│   │   ├── security/           # Authentication & security
│   │   └── events.py           # Application lifecycle events
│   ├── crud/                   # Database operations
│   ├── db/                     # Database configuration
│   ├── models/                 # SQLAlchemy models
│   ├── schemas/                # Pydantic schemas
│   ├── services/               # Business logic services
│   └── monitoring/             # Health checks and metrics
├── tests/                      # Comprehensive test suite
├── scripts/                    # Utility scripts
├── terraform/                  # Infrastructure as code
├── docker/                     # Docker configurations
└── docs/                       # Additional documentation
```

### AI Providers Integration

#### OpenAI Integration

```python
from app.ai.providers import openai_provider

# Chat completion
response = await openai_provider.chat_completion(
    messages=[{"role": "user", "content": "Hello!"}],
    model="gpt-4",
    stream=True
)

# Function calling
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather information",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"}
                }
            }
        }
    }
]

response = await openai_provider.chat_completion_with_tools(
    messages=[{"role": "user", "content": "What's the weather in NYC?"}],
    tools=tools
)
```

#### Anthropic Claude Integration

```python
from app.ai.providers import anthropic_provider

# Claude conversation
response = await anthropic_provider.create_message(
    messages=[{"role": "user", "content": "Explain quantum computing"}],
    model="claude-3-sonnet-20240229",
    max_tokens=1000
)

# Streaming response
async for chunk in anthropic_provider.stream_message(messages):
    print(chunk.content)
```

#### Google Gemini Integration

```python
from app.ai.providers import gemini_provider

# Text generation
response = await gemini_provider.generate_content(
    prompt="Write a Python function to calculate fibonacci",
    model="gemini-pro"
)

# Multimodal with images
import base64
image_data = base64.b64encode(image_bytes).decode()

response = await gemini_provider.generate_content_multimodal(
    text_prompt="Describe this image",
    image_data=image_data,
    mime_type="image/jpeg"
)
```

### Tool Framework

#### Creating Custom Tools

```python
from app.ai.tools.base import BaseTool, ToolParameter, ToolParameterType, ToolResult

class WeatherTool(BaseTool):
    @property
    def name(self) -> str:
        return "get_weather"
    
    @property
    def description(self) -> str:
        return "Get current weather for a location"
    
    @property
    def category(self) -> str:
        return "information"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="location",
                type=ToolParameterType.STRING,
                description="City name or coordinates",
                required=True
            ),
            ToolParameter(
                name="units",
                type=ToolParameterType.STRING,
                description="Temperature units (celsius/fahrenheit)",
                required=False,
                default="celsius"
            )
        ]
    
    async def execute(self, location: str, units: str = "celsius") -> ToolResult:
        try:
            # Your weather API integration here
            weather_data = await fetch_weather(location, units)
            
            return ToolResult(
                success=True,
                result=weather_data,
                execution_time=0.5
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e)
            )
```

#### Registering Tools

```python
from app.services.tool_service import tool_service

# Register your custom tool
weather_tool = WeatherTool()
tool_service.register_tool(weather_tool, "information")

# Use in AI conversations
from app.ai.services.execution_engine import execution_engine

result = await execution_engine.execute_with_tools(
    agent_id="your-agent-id",
    message="What's the weather in San Francisco?",
    available_tools=["get_weather"]
)
```

### API Usage Examples

#### User Management

```python
import httpx

# Register new user
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "password": "SecurePass123!",
            "full_name": "John Doe"
        }
    )
    user_data = response.json()

# Login
response = await client.post(
    "http://localhost:8000/api/v1/auth/login",
    json={
        "email": "user@example.com",
        "password": "SecurePass123!"
    }
)
tokens = response.json()
access_token = tokens["access_token"]
```

#### Agent Creation and Chat

```python
# Create an AI agent
headers = {"Authorization": f"Bearer {access_token}"}

agent_response = await client.post(
    "http://localhost:8000/api/v1/agents/",
    json={
        "name": "My Assistant",
        "description": "A helpful AI assistant",
        "system_prompt": "You are a helpful assistant that can use tools.",
        "model": "gpt-4",
        "provider": "openai",
        "tools_enabled": ["web_search", "calculator"]
    },
    headers=headers
)
agent = agent_response.json()

# Start a conversation
conversation_response = await client.post(
    "http://localhost:8000/api/v1/conversations/",
    json={
        "title": "My First Chat",
        "agent_id": agent["id"]
    },
    headers=headers
)
conversation = conversation_response.json()

# Send a message
message_response = await client.post(
    f"http://localhost:8000/api/v1/conversations/{conversation['id']}/messages",
    json={
        "content": "Calculate the square root of 144 and then search for information about mathematics"
    },
    headers=headers
)
message = message_response.json()
```

#### Streaming AI Responses

```python
import asyncio
from sse_starlette import EventSourceResponse

async def stream_ai_response():
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            f"http://localhost:8000/api/v1/agent-execution/{agent['id']}/stream",
            json={
                "message": "Tell me a story about AI",
                "conversation_id": conversation["id"]
            },
            headers=headers
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if data.get("type") == "content":
                        print(data.get("content"), end="")
```

## 🧪 Testing

The template includes a comprehensive testing suite with multiple levels:

### Quick Validation

```bash
# Basic template validation
python test_template.py

# Full integration testing
python test_template.py --level integration

# Complete end-to-end testing
python test_template.py --level full
```

### Unit Tests

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ --cov=app --cov-report=html

# Run specific test files
pytest tests/unit/test_ai_providers.py
pytest tests/unit/test_tools.py
```

### Integration Tests

```bash
# API integration tests
pytest tests/integration/test_api/ -v

# AI workflow tests
pytest tests/integration/test_ai_workflow/ -v

# Database integration tests
pytest tests/integration/test_database/ -v
```

### End-to-End Tests

```bash
# Full user journey tests
pytest tests/e2e/ -v --docker

# Performance tests
pytest tests/load/ -v
```

### Security Tests

```bash
# Security vulnerability tests
pytest tests/security/ -v

# Authentication security tests
pytest tests/security/test_auth_security.py -v
```

## 🐳 Docker Deployment

### Development

```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f app

# Run tests in container
docker-compose exec app pytest
```

### Production

```bash
# Build production image
docker build -f docker/Dockerfile.prod -t myapp:latest .

# Run production container
docker run -d \
  --name myapp \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  -e SECRET_KEY=... \
  myapp:latest
```

### Multi-stage Build

The included Dockerfile uses multi-stage builds for optimal production images:

```dockerfile
# Development stage with all dev dependencies
FROM python:3.11-slim as development

# Production stage with minimal dependencies
FROM python:3.11-slim as production
```

## ☁️ Cloud Deployment

### AWS with Terraform

```bash
cd terraform/environments/prod

# Initialize Terraform
terraform init

# Plan deployment
terraform plan -var="environment=production"

# Deploy infrastructure
terraform apply

# Get outputs
terraform output app_url
```

### Environment Variables for Production

```env
# Production environment
ENVIRONMENT=production
DEBUG=false

# Database (use managed service)
DATABASE_URL=postgresql+asyncpg://user:pass@rds-instance:5432/db

# Redis (use managed service)
REDIS_URL=redis://elasticache-instance:6379/0

# AI Providers
OPENAI_API_KEY=your_production_openai_key
ANTHROPIC_API_KEY=your_production_anthropic_key
GEMINI_API_KEY=your_production_gemini_key

# Security
SECRET_KEY=super-secure-production-key-here

# Monitoring
SENTRY_DSN=your_sentry_dsn_here
```

## 🔧 Configuration

### Core Settings

The application uses Pydantic settings for configuration management:

```python
# app/core/config.py
class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "KickStartMyAI"
    
    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 30
    
    # AI Providers
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    
    # Security
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Feature Flags
    ENABLE_AI_FEATURES: bool = True
    ENABLE_TOOL_EXECUTION: bool = True
    ENABLE_BACKGROUND_TASKS: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True
```

### AI Provider Configuration

```python
# Configure AI providers
OPENAI_MODEL_DEFAULT = "gpt-4"
ANTHROPIC_MODEL_DEFAULT = "claude-3-sonnet-20240229"
GEMINI_MODEL_DEFAULT = "gemini-pro"

# Model-specific settings
OPENAI_MAX_TOKENS = 4000
ANTHROPIC_MAX_TOKENS = 4000
GEMINI_MAX_TOKENS = 2048

# Rate limiting
AI_REQUESTS_PER_MINUTE = 60
AI_REQUESTS_PER_HOUR = 1000
```

## 📊 Monitoring & Observability

### Health Checks

```bash
# Basic health check
curl http://localhost:8000/health

# Detailed health check
curl http://localhost:8000/health/detailed
```

### Metrics and Logging

The application includes structured logging and metrics:

```python
# Request logging with correlation IDs
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "logger": "app.api.middleware.logging",
  "message": "Request completed",
  "request_id": "abc-123-def",
  "http_method": "POST",
  "http_path": "/api/v1/agents",
  "http_status": 201,
  "duration_ms": 150.5
}

# AI provider metrics
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "logger": "app.ai.providers.openai",
  "message": "Chat completion successful",
  "model": "gpt-4",
  "tokens_used": 150,
  "cost_usd": 0.003,
  "duration_ms": 1200
}
```

### Performance Monitoring

```python
# Built-in performance tracking
from app.monitoring.performance import track_performance

@track_performance("ai_generation")
async def generate_response(prompt: str):
    response = await ai_provider.generate(prompt)
    return response
```

## 🤝 Contributing

### Development Setup

```bash
# Clone the repository
git clone https://github.com/hectorjassog/kickstartmyai.git
cd kickstartmyai

# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Run template validation
python test_template.py
```

### Code Quality

The project uses several tools for code quality:

```bash
# Format code
black .
isort .

# Lint code
flake8 .
mypy .

# Security checks
bandit -r app/

# Dependency checks
safety check
```

### Testing Requirements

All contributions must include:

- Unit tests for new functionality
- Integration tests for API changes
- Documentation updates
- Type hints for all functions
- Docstring documentation

### Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run the full test suite
5. Update documentation
6. Submit a pull request

## 📚 Advanced Features

### Custom Middleware

```python
# app/api/middleware/custom.py
from starlette.middleware.base import BaseHTTPMiddleware

class CustomMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Pre-processing
        start_time = time.time()
        
        response = await call_next(request)
        
        # Post-processing
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
```

### Background Tasks

```python
# app/services/background_tasks.py
from celery import Celery

celery_app = Celery("myapp")

@celery_app.task
async def process_ai_batch(batch_id: str):
    """Process AI requests in batch for cost optimization."""
    batch = await get_batch(batch_id)
    
    for request in batch.requests:
        result = await ai_provider.process(request)
        await save_result(request.id, result)
```

### Custom AI Providers

```python
# app/ai/providers/custom_provider.py
from app.ai.providers.base import BaseAIProvider

class CustomAIProvider(BaseAIProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = CustomAIClient(api_key)
    
    async def chat_completion(self, messages: List[dict], **kwargs):
        response = await self.client.complete(messages)
        return self._format_response(response)
    
    async def stream_completion(self, messages: List[dict], **kwargs):
        async for chunk in self.client.stream(messages):
            yield self._format_chunk(chunk)
```

## 🔐 Security Best Practices

### Authentication & Authorization

- JWT tokens with secure rotation
- Password strength requirements
- Rate limiting on authentication endpoints
- Session management with Redis
- Role-based access control (RBAC)

### API Security

- Input validation with Pydantic
- SQL injection prevention
- XSS protection
- CORS configuration
- Request size limits
- API versioning

### AI Security

- Prompt injection protection
- Tool execution sandboxing
- Parameter validation
- Cost monitoring and limits
- Audit logging for AI operations

## 📈 Performance Optimization

### Database Optimization

```python
# Async database operations
async def get_users_optimized(db: AsyncSession, limit: int = 100):
    query = select(User).options(
        selectinload(User.conversations),  # Eager loading
        selectinload(User.agents)
    ).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()

# Database connection pooling
engine = create_async_engine(
    database_url,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

### Caching Strategy

```python
# Redis caching
from app.core.cache import cache

@cache.cached(timeout=300)  # 5 minutes
async def get_expensive_data(key: str):
    # Expensive operation
    return await compute_data(key)

# AI response caching
@cache.cached(timeout=3600, key_prefix="ai_response")
async def cached_ai_completion(prompt_hash: str):
    return await ai_provider.complete(prompt)
```

### Async Optimization

```python
# Concurrent AI requests
import asyncio

async def process_multiple_requests(requests: List[str]):
    tasks = [
        ai_provider.complete(request) 
        for request in requests
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

## 🌐 API Reference

### Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | User login |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| POST | `/api/v1/auth/logout` | User logout |
| GET | `/api/v1/auth/me` | Get current user |

### Agent Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/agents/` | List agents |
| POST | `/api/v1/agents/` | Create agent |
| GET | `/api/v1/agents/{id}` | Get agent details |
| PUT | `/api/v1/agents/{id}` | Update agent |
| DELETE | `/api/v1/agents/{id}` | Delete agent |

### Conversation Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/conversations/` | List conversations |
| POST | `/api/v1/conversations/` | Create conversation |
| GET | `/api/v1/conversations/{id}` | Get conversation |
| POST | `/api/v1/conversations/{id}/messages` | Send message |
| GET | `/api/v1/conversations/{id}/messages` | Get messages |

### AI Execution

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/agent-execution/{agent_id}/execute` | Execute agent |
| POST | `/api/v1/agent-execution/{agent_id}/stream` | Stream execution |
| GET | `/api/v1/executions/` | List executions |
| GET | `/api/v1/executions/{id}` | Get execution details |

## 🆘 Troubleshooting

### Common Issues

#### Database Connection Issues

```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Test connection
psql postgresql://user:pass@localhost:5432/dbname

# Check migrations
alembic current
alembic history
```

#### AI Provider Issues

```bash
# Test API keys
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     "https://api.openai.com/v1/models"

# Check provider configuration
python -c "from app.core.config import settings; print(settings.OPENAI_API_KEY[:10])"
```

#### Docker Issues

```bash
# Check container logs
docker-compose logs app

# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Debug Mode

Enable debug mode for detailed error information:

```env
DEBUG=true
LOG_LEVEL=DEBUG
```

### Getting Help

- **Documentation**: Check the `/docs` directory
- **API Docs**: Visit `/docs` endpoint when running
- **Issues**: Open an issue on GitHub
- **Community**: Join our Discord/Slack community

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - The amazing web framework
- [SQLAlchemy](https://sqlalchemy.org/) - The database toolkit
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation library
- [OpenAI](https://openai.com/) - AI provider
- [Anthropic](https://anthropic.com/) - Claude AI provider
- [Google](https://ai.google.dev/) - Gemini AI provider

## 🚀 What's Next?

After generating your project:

1. **Configure your AI providers** with API keys
2. **Set up your database** and run migrations
3. **Create your first agent** and start chatting
4. **Customize the tool framework** for your use case
5. **Deploy to production** using the included Terraform configs
6. **Monitor and scale** your application

Ready to build the future with AI? Let's get started! 🚀