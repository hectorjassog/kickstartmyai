#!/bin/bash
# Development environment setup script for {{cookiecutter.project_name}}

set -e

echo "🚀 Setting up {{cookiecutter.project_name}} development environment..."

# Check if Python 3.11+ is installed
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.11.0"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
    echo "❌ Python 3.11+ is required. Current version: $python_version"
    exit 1
fi

echo "✅ Python version: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Set up environment file
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please update .env with your actual configuration values"
fi

# Set up pre-commit hooks
echo "Setting up pre-commit hooks..."
pre-commit install

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and run this script again."
    exit 1
fi

echo "✅ Docker is running"

# Start database and redis with Docker Compose
echo "Starting database and Redis..."
docker-compose up -d postgres redis

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 10

# Create database
echo "Setting up database..."
python scripts/database/create_db.py

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Run tests to make sure everything is working
echo "Running tests..."
pytest tests/ -v

echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "To start development:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Start the application: python -m app.main"
echo "3. Visit: http://localhost:8000"
echo "4. API docs: http://localhost:8000/docs"
echo ""
echo "Useful commands:"
echo "- Start all services: docker-compose up -d"
echo "- Stop all services: docker-compose down"
echo "- Run tests: pytest"
echo "- Format code: black app/ tests/ && isort app/ tests/"
echo "- Check types: mypy app/"
