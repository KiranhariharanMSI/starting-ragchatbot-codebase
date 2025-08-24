#!/bin/bash
set -e

echo "🚀 Starting Course Materials RAG System..."

# Ensure ChromaDB directory exists and has proper permissions
if [ ! -d "/app/chroma_db" ]; then
    echo "📁 Creating ChromaDB directory..."
    mkdir -p /app/chroma_db
fi

# Check if .env file exists and has API key
if [ ! -f "/app/.env" ]; then
    echo "❌ Error: .env file not found. Please make sure to mount your .env file with ANTHROPIC_API_KEY"
    exit 1
fi

# Check if API key is set
if ! grep -q "ANTHROPIC_API_KEY" /app/.env || grep -q -E "(your_anthropic_api_key_here|your-anthropic-api-key-here|your_actual_api_key_here)" /app/.env; then
    echo "❌ Error: Please set your actual ANTHROPIC_API_KEY in the .env file"
    exit 1
fi

echo "✅ Environment configuration validated"

echo "🔍 Debug: Checking environment..."
echo "Current directory: $(pwd)"
echo "Python path: $(which python)"
echo "uv version: $(uv --version)"
echo "Contents of /app:"
ls -la /app/
echo "Contents of /app/.venv/bin (first 10):"
ls -la /app/.venv/bin/ | head -10
echo "Checking if uvicorn is importable:"
/app/.venv/bin/python -c "import uvicorn; print('✅ uvicorn module found')" || echo "❌ uvicorn module not found"
echo "pyproject.toml exists: $(test -f /app/pyproject.toml && echo '✅' || echo '❌')"

echo "🔧 Starting FastAPI server..."
echo "📊 Access the web interface at: http://localhost:8000"
echo "📖 API documentation available at: http://localhost:8000/docs"

# Start the FastAPI server - try uv run first, fallback to system python
# Using 0.0.0.0 to accept connections from outside the container
cd /app

# Since uvicorn module is available, use Python directly
echo "Starting with Python module (uvicorn is importable)..."
cd /app/backend
export PYTHONPATH="/app:/app/backend:/app/.venv/lib/python3.13/site-packages"
python3 -m uvicorn app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --log-level info