#!/usr/bin/env bash
# Launch script for Axion Swarm with Web Interface
# This script starts both the web server and TUI in the correct order

set -e  # Exit on error

echo "=========================================="
echo "🚀 Axion Swarm Web+TUI Launch Script"
echo "=========================================="
echo ""

# Check if webserver.py exists
if [ ! -f "webserver.py" ]; then
    echo "❌ Error: webserver.py not found in current directory"
    exit 1
fi

# Check if main.py exists
if [ ! -f "main.py" ]; then
    echo "❌ Error: main.py not found in current directory"
    exit 1
fi

# Detect Python command (prefer venv if active)
if [ -n "$VIRTUAL_ENV" ]; then
    PYTHON_CMD="$VIRTUAL_ENV/bin/python3"
    echo "✅ Using virtual environment: $VIRTUAL_ENV"
elif [ -d "venv" ]; then
    PYTHON_CMD="venv/bin/python3"
    echo "✅ Using local venv"
elif [ -d "venv" ]; then
    PYTHON_CMD="venv/bin/python3"
    echo "✅ Using local venv"
else
    PYTHON_CMD="python3"
    echo "⚠️  No venv detected, using system python3"
fi
echo ""

# Check if web UI is built
if [ ! -d "web/dist" ]; then
    echo "⚠️  Web UI not built. Building now..."
    cd web
    npm install
    npm run build
    cd ..
    echo "✅ Web UI built successfully"
    echo ""
fi

echo "Starting Web Server..."
echo "----------------------------------------"
echo ""
echo "📋 The webserver will:"
echo "   - Clear user_input.txt (fresh command queue)"
echo "   - Load existing graph.log (or wait for new data)"
echo "   - Watch graph.log for agent updates"
echo "   - Serve Vue.js UI on http://localhost:5000/"
echo "   - Write web submissions to user_input.txt"
echo ""
echo "💡 To start agents:"
echo "   - Open another terminal"
echo "   - Run: python main.py"
echo "   - Agents will watch user_input.txt for web submissions"
echo ""
echo "=========================================="
echo ""
$PYTHON_CMD webserver.py
echo ""
echo "=========================================="
echo "Webserver stopped"
echo "=========================================="

