#!/bin/bash
# Axion Swarm Web UI Setup Script

set -e

echo "╔═══════════════════════════════════════════════════════╗"
echo "║    Axion Swarm Web UI - Setup                        ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

echo "✅ Node.js found: $(node --version)"

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install npm first."
    exit 1
fi

echo "✅ npm found: $(npm --version)"
echo ""

# Detect Python/pip command (prefer venv if active)
if [ -n "$VIRTUAL_ENV" ]; then
    PIP_CMD="$VIRTUAL_ENV/bin/pip"
    echo "✅ Using virtual environment: $VIRTUAL_ENV"
elif [ -d ".venv" ]; then
    PIP_CMD=".venv/bin/pip"
    echo "✅ Using local .venv virtual environment"
else
    PIP_CMD="pip3"
    echo "⚠️  No virtual environment detected, using system pip3"
fi
echo ""

# Install Python dependencies
echo "📦 Installing Python dependencies..."
$PIP_CMD install -r requirements.txt
echo "✅ Python dependencies installed"
echo ""

# Install Node.js dependencies
echo "📦 Installing Node.js dependencies..."
cd web
npm install
echo "✅ Node.js dependencies installed"
echo ""

# Build frontend
echo "🔨 Building Vue.js frontend..."
npm run build
echo "✅ Frontend built successfully"
cd ..
echo ""

echo "╔═══════════════════════════════════════════════════════╗"
echo "║    Setup Complete! 🎉                                ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""
echo "To start the web interface:"
echo ""
echo "  # Option 1: Production mode (recommended for first try)"
echo "  python webserver.py"
echo "  # Then visit: http://localhost:5000"
echo ""
echo "  # Option 2: Development mode (with hot reload)"
echo "  # Terminal 1:"
echo "  python webserver.py"
echo "  # Terminal 2:"
echo "  cd web && npm run dev"
echo "  # Then visit: http://localhost:3000"
echo ""
echo "For full usage instructions, see: WEB_UI_README.md"
echo ""

