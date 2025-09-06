#!/bin/bash
# Quick start script for BOL-CD

echo "Starting BOL-CD services..."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Start API server
echo "🚀 Starting API server on port 8080..."
PYTHONPATH="${PYTHONPATH}:src" uvicorn src.bolcd.api.app:app --host 0.0.0.0 --port 8080 --reload &
API_PID=$!

# Start Web UI
if [ -d "web" ]; then
    echo "🌐 Starting Web UI on port 3000..."
    cd web && npm run dev &
    WEB_PID=$!
    cd ..
fi

echo ""
echo "========================================="
echo "  BOL-CD is running!"
echo "========================================="
echo "  API:    http://localhost:8080"
echo "  Web UI: http://localhost:3000"
echo "  Docs:   http://localhost:8080/docs"
echo ""
echo "  Demo accounts:"
echo "  - admin@demo.com / admin123"
echo "  - user@demo.com / user123"
echo "  - analyst@demo.com / analyst123"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap "kill $API_PID $WEB_PID 2>/dev/null; exit" INT
wait
