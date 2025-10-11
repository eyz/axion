#!/bin/bash

# Axion Swarm Setup Script

echo "🚀 Setting up Axion Swarm..."
echo ""

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "⚠️  Ollama is not installed."
    echo "📦 Install it from: https://ollama.ai"
    echo ""
    read -p "Do you want to continue without Ollama? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✅ Ollama is installed"
    
    # Check if models are available
    echo "📦 Checking for required models..."
    
    if ! ollama list | grep -q "llama3.2:3b"; then
        echo "⬇️  Pulling llama3.2:3b..."
        ollama pull llama3.2:3b
    else
        echo "✅ llama3.2:3b is available"
    fi
    
    if ! ollama list | grep -q "qwen2.5-coder:7b"; then
        echo "⬇️  Pulling qwen2.5-coder:7b (this may take a while)..."
        ollama pull qwen2.5-coder:7b
    else
        echo "✅ qwen2.5-coder:7b is available"
    fi
fi

echo ""
echo "🐍 Setting up Python environment..."

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install -e . -q

echo ""

# Setup .env file
if [ ! -f ".env" ]; then
    if [ -f ".env.ollama.example" ]; then
        cp .env.ollama.example .env
        echo "✅ Created .env file from .env.ollama.example"
    fi
else
    echo "✅ .env file already exists"
fi

echo ""
echo "✨ Setup complete!"
echo ""
echo "To get started:"
echo "  1. Activate the virtual environment: source .venv/bin/activate"
echo "  2. Run the swarm: python main.py"
echo "  3. Edit .env to customize agent models"
echo ""
