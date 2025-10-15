#!/usr/bin/env bash
# Launch Axion Swarm with Web Interface using tmux
# Creates a tmux session with split panes for webserver and TUI

set -e

SESSION_NAME="axion-swarm"

echo "=========================================="
echo "🚀 Axion Swarm Web+TUI (tmux mode)"
echo "=========================================="
echo ""

# Check if tmux is installed
if ! command -v tmux &> /dev/null; then
    echo "❌ Error: tmux is not installed"
    echo "   Install with: sudo apt install tmux"
    exit 1
fi

# Detect Python command (prefer venv if active)
if [ -n "$VIRTUAL_ENV" ]; then
    PYTHON_CMD="$VIRTUAL_ENV/bin/python3"
    echo "✅ Using virtual environment: $VIRTUAL_ENV"
elif [ -d ".venv" ]; then
    PYTHON_CMD=".venv/bin/python3"
    echo "✅ Using local .venv"
else
    PYTHON_CMD="python3"
    echo "⚠️  No venv detected, using system python3"
fi
echo ""

# Check if session already exists
if tmux has-session -t $SESSION_NAME 2>/dev/null; then
    echo "⚠️  Session '$SESSION_NAME' already exists"
    echo "   Attaching to existing session..."
    tmux attach-session -t $SESSION_NAME
    exit 0
fi

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

echo "Creating tmux session with split panes..."
echo ""

# Create new tmux session with webserver in first pane
tmux new-session -d -s $SESSION_NAME -n "Axion" "cd $(pwd) && python3 webserver.py"

# Split window horizontally and run TUI in second pane (after 3s delay)
tmux split-window -h -t $SESSION_NAME "sleep 3 && cd $(pwd) && python3 main.py"

# Resize panes (60% webserver logs, 40% TUI)
tmux resize-pane -t $SESSION_NAME:0.0 -x 60%

# Set pane titles
tmux select-pane -t $SESSION_NAME:0.0 -T "Webserver"
tmux select-pane -t $SESSION_NAME:0.1 -T "TUI (Agent Chat)"

echo "✅ tmux session created: $SESSION_NAME"
echo ""
echo "🌐 Access Points:"
echo "  - Vue.js App: http://localhost:5000/"
echo "  - Static Form: http://localhost:5000/form"
echo ""
echo "📋 tmux Commands:"
echo "  - Switch panes: Ctrl+B then arrow keys"
echo "  - Detach: Ctrl+B then d"
echo "  - Reattach: tmux attach -t $SESSION_NAME"
echo "  - Kill session: tmux kill-session -t $SESSION_NAME"
echo ""
echo "Attaching to session..."
sleep 1

# Attach to the session
tmux attach-session -t $SESSION_NAME

