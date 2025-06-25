#!/bin/bash

# AskMyDrive Local Development Server Script
# This script runs the FastAPI application locally using uvicorn

set -e  # Exit on any error

# Default port
DEFAULT_PORT=8000
PORT=${1:-$DEFAULT_PORT}

# Validate port number
if ! [[ "$PORT" =~ ^[0-9]+$ ]] || [ "$PORT" -lt 1 ] || [ "$PORT" -gt 65535 ]; then
    echo "❌ Error: Invalid port number '$PORT'. Please provide a valid port (1-65535)."
    echo "💡 Usage: ./run_local.sh [PORT]"
    echo "💡 Example: ./run_local.sh 8080"
    exit 1
fi

echo "🚀 Starting AskMyDrive local development server..."
echo "📍 Working directory: $(pwd)"

# Check if we're in the backend directory
if [ ! -f "app/main.py" ]; then
    echo "❌ Error: app/main.py not found. Please run this script from the backend directory."
    echo "💡 Tip: cd backend && ./run_local.sh"
    exit 1
fi

# Check if virtual environment is activated (optional but recommended)
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: No virtual environment detected. Consider activating one:"
    echo "   python -m venv venv && source venv/bin/activate"
    echo ""
fi

# Check if requirements are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "❌ Error: FastAPI not found. Please install requirements:"
    echo "   pip install -r requirements.txt"
    exit 1
fi

echo "🔧 Configuration:"
echo "   - Host: 0.0.0.0"
echo "   - Port: $PORT"
echo "   - Reload: enabled"
echo "   - Log level: info"
echo ""

echo "🌐 Server will be available at:"
echo "   - Local: http://localhost:$PORT"
echo "   - Network: http://0.0.0.0:$PORT"
echo "   - API Docs: http://localhost:$PORT/docs"
echo "   - ReDoc: http://localhost:$PORT/redoc"
echo ""

echo "⏳ Starting server on port $PORT... (Press Ctrl+C to stop)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Run uvicorn with development settings
uvicorn app.main:app \
    --host 0.0.0.0 \
    --port $PORT \
    --reload \
    --log-level info \
    --reload-dir app \
    --access-log 