#!/usr/bin/env python3
"""
Real-time web interface for Axion Swarm graph visualization.

FastAPI + Socket.IO + uvicorn for high-performance WebSocket support.
"""

import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import socketio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Import graph analysis functions
sys.path.insert(0, str(Path(__file__).parent))
from graph_parser import analyze_graph_log


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    # Startup
    global observer
    
    # Ensure graph.log exists
    graph_log_path = Path('graph.log')
    if not graph_log_path.exists():
        graph_log_path.touch()
        print(f"[WebServer] Created empty graph.log (ready for agent updates)")
    else:
        print(f"[WebServer] Loading existing graph data from graph.log")
    
    # Clear user input file
    user_input_path = Path('user_input.txt')
    if user_input_path.exists():
        user_input_path.unlink()
    user_input_path.touch()
    print(f"[WebServer] Cleared user_input.txt (fresh session)")
    
    # Initialize phase status file
    phase_status_path = Path('phase_status.json')
    if not phase_status_path.exists():
        import json
        with phase_status_path.open('w') as f:
            json.dump({'waiting': False, 'phase': 0, 'is_final': False}, f)
        print(f"[WebServer] Created phase_status.json")
    
    # Load initial state
    load_graph_state()
    
    # Start file watcher with the event loop
    loop = asyncio.get_event_loop()
    start_file_watcher(loop)
    
    print(f"\n{'='*80}")
    print(f"🌐 Axion Swarm Web Interface")
    print(f"{'='*80}")
    print(f"Server running at: http://0.0.0.0:5000")
    print(f"Watching: graph.log")
    print(f"")
    print(f"📺 Available Interfaces:")
    print(f"  • Vue.js Real-Time: http://0.0.0.0:5000/")
    print(f"  • REST API:         http://0.0.0.0:5000/api/graph")
    print(f"")
    print(f"💡 Usage:")
    print(f"  • Run 'python main_tui.py' in another terminal for agent chat (TUI)")
    print(f"  • Open web interface in browser for graph visualization")
    print(f"  • Both read from same graph.log - fully synchronized")
    print(f"{'='*80}\n")
    
    yield
    
    # Shutdown
    if observer:
        observer.stop()
        observer.join()
    print("\n[WebServer] Shutting down...")


# Create FastAPI app with lifespan
app = FastAPI(title="Axion Swarm Web Interface", lifespan=lifespan)

# Create Socket.IO server with ASGI support
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    ping_timeout=60,
    ping_interval=25
)

# Wrap with Socket.IO ASGI app
socket_app = socketio.ASGIApp(sio, app)

# Global state
graph_state: Dict[str, Any] = {
    'nodes': {},
    'vote_tally': {},
    'specialist_stats': {}
}
connected_clients = set()
observer = None


def load_graph_state(log_path='graph.log'):
    """Load and parse graph.log into memory."""
    if not Path(log_path).exists():
        return
    
    nodes, vote_tally, specialist_stats = analyze_graph_log(log_path)
    graph_state['nodes'] = nodes
    graph_state['vote_tally'] = vote_tally
    graph_state['specialist_stats'] = specialist_stats


def serialize_graph_state() -> Dict[str, Any]:
    """Serialize graph state for transmission to clients."""
    return {
        'nodes': graph_state['nodes'],
        'vote_tally': graph_state['vote_tally'],
        'specialist_stats': graph_state['specialist_stats']
    }


async def broadcast_graph_update():
    """Broadcast updated graph state to all connected clients."""
    import time
    start_time = time.time()
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    
    print(f"[WebServer] 🕐 [{timestamp}] Starting broadcast...")
    
    # Reload graph data
    nodes, vote_tally, specialist_stats = analyze_graph_log('graph.log')
    parse_time = time.time()
    print(f"[WebServer] ⏱️  analyze_graph_log: {(parse_time - start_time) * 1000:.2f}ms")
    
    # Store updated state
    graph_state['nodes'] = nodes
    graph_state['vote_tally'] = vote_tally
    graph_state['specialist_stats'] = specialist_stats
    
    # Broadcast to browser immediately
    serialized = serialize_graph_state()
    serialize_time = time.time()
    print(f"[WebServer] ⏱️  serialize_graph_state: {(serialize_time - parse_time) * 1000:.2f}ms")
    
    emit_timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    print(f"[WebServer] 🕐 [{emit_timestamp}] Emitting to clients...")
    
    # Emit to all connected clients
    await sio.emit('graph_update', serialized)
    
    emit_time = time.time()
    emit_complete_timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    print(f"[WebServer] 🕐 [{emit_complete_timestamp}] Emit complete")
    print(f"[WebServer] ⏱️  socketio.emit: {(emit_time - serialize_time) * 1000:.2f}ms")
    print(f"[WebServer] ⏱️  TOTAL: {(emit_time - start_time) * 1000:.2f}ms")
    print(f"[WebServer] ✅ Broadcasted update to {len(connected_clients)} client(s)")


async def broadcast_phase_status():
    """Broadcast phase status to all connected clients."""
    import json
    
    try:
        phase_status_path = Path('phase_status.json')
        if not phase_status_path.exists():
            return
        
        with phase_status_path.open('r') as f:
            status = json.load(f)
        
        print(f"[WebServer] Broadcasting phase status: Phase {status.get('phase', 0)}, waiting={status.get('waiting', False)}")
        await sio.emit('phase_status', status)
        
    except Exception as e:
        print(f"[WebServer] Error broadcasting phase status: {e}")


# Socket.IO event handlers
@sio.event
async def connect(sid, environ):
    """Handle client connection."""
    connected_clients.add(sid)
    print(f"[WebServer] Client connected (total: {len(connected_clients)})")
    
    # Send initial state
    import time
    import json
    start_time = time.time()
    
    load_graph_state()
    load_time = time.time()
    print(f"[WebServer] ⏱️  load_graph_state: {(load_time - start_time) * 1000:.2f}ms")
    
    serialized = serialize_graph_state()
    serialize_time = time.time()
    print(f"[WebServer] ⏱️  serialize: {(serialize_time - load_time) * 1000:.2f}ms")
    
    await sio.emit('graph_update', serialized, to=sid)
    emit_time = time.time()
    print(f"[WebServer] ⏱️  emit: {(emit_time - serialize_time) * 1000:.2f}ms")
    print(f"[WebServer] ⏱️  TOTAL initial state: {(emit_time - start_time) * 1000:.2f}ms")
    print(f"[WebServer] Sent initial graph state to new client ({len(serialized.get('nodes', {}))} nodes)")
    
    # Also send initial phase status
    try:
        phase_status_path = Path('phase_status.json')
        if phase_status_path.exists():
            with phase_status_path.open('r') as f:
                status = json.load(f)
            await sio.emit('phase_status', status, to=sid)
            print(f"[WebServer] Sent initial phase status to new client (Phase {status.get('phase', 0)})")
    except Exception as e:
        print(f"[WebServer] Could not send initial phase status: {e}")


@sio.event
async def disconnect(sid):
    """Handle client disconnection."""
    connected_clients.discard(sid)
    print(f"[WebServer] Client disconnected (total: {len(connected_clients)})")


@sio.event
async def request_initial_state(sid):
    """Handle explicit request for initial graph state from client."""
    import time
    start_time = time.time()
    
    load_graph_state()
    load_time = time.time()
    print(f"[WebServer] ⏱️  load_graph_state: {(load_time - start_time) * 1000:.2f}ms")
    
    serialized = serialize_graph_state()
    serialize_time = time.time()
    print(f"[WebServer] ⏱️  serialize: {(serialize_time - load_time) * 1000:.2f}ms")
    
    await sio.emit('graph_update', serialized, to=sid)
    emit_time = time.time()
    print(f"[WebServer] ⏱️  emit: {(emit_time - serialize_time) * 1000:.2f}ms")
    print(f"[WebServer] ⏱️  TOTAL initial state: {(emit_time - start_time) * 1000:.2f}ms")
    print(f"[WebServer] Sent initial state on client request ({len(serialized.get('nodes', {}))} nodes)")


@sio.event
async def submit_decisions(sid, data):
    """Handle user form submission from web UI."""
    commands = data.get('commands', [])
    timestamp = data.get('timestamp', datetime.now().isoformat())
    
    if not commands:
        await sio.emit('submission_error', {'error': 'No commands provided'}, to=sid)
        return
    
    print(f"[WebServer] Received {len(commands)} decision(s) from web UI")
    
    # Convert to graph commands
    graph_commands = [f"@[Graph][Update]{cmd}" for cmd in commands]
    
    try:
        # Write to user_input.txt for TUI to read
        user_input_path = Path('user_input.txt')
        with user_input_path.open('a') as f:
            f.write(f"\n# User submission from web UI at {timestamp}\n")
            for cmd in graph_commands:
                f.write(f"{cmd}\n")
        
        print(f"[WebServer] Wrote {len(graph_commands)} command(s) to user_input.txt")
        
        await sio.emit('submission_success', {
            'message': f'Successfully submitted {len(commands)} decision(s)',
            'commands': graph_commands,
            'timestamp': timestamp
        }, to=sid)
        
    except Exception as e:
        print(f"[WebServer] Error writing user input: {e}")
        await sio.emit('submission_error', {'error': str(e)}, to=sid)


@sio.event
async def submit_thought(sid, data):
    """Handle user thought/comment submission on a graph node."""
    path = data.get('path', '')
    comment = data.get('comment', '')
    timestamp = data.get('timestamp', datetime.now().isoformat())
    
    if not path or not comment:
        await sio.emit('thought_error', {'error': 'Path and comment are required'}, to=sid)
        return
    
    print(f"[WebServer] Received thought for {path}: \"{comment}\"")
    
    try:
        # Write to user_input.txt so TUI picks it up (like other web commands)
        # Agents will see it and it will be written to graph.log by the agent system
        user_input_path = Path('user_input.txt')
        thought_command = f"@[Graph][Regarding]{path}[{comment}]"
        
        with user_input_path.open('a') as f:
            f.write(f"\n# User thought from web UI at {timestamp}\n")
            f.write(f"{thought_command}\n")
        
        print(f"[WebServer] Wrote thought to user_input.txt")
        
        await sio.emit('thought_success', {
            'message': 'Thought submitted successfully',
            'path': path,
            'timestamp': timestamp
        }, to=sid)
        
    except Exception as e:
        print(f"[WebServer] Error writing thought: {e}")
        await sio.emit('thought_error', {'error': str(e)}, to=sid)


@sio.event
async def continue_phase(sid, data):
    """Handle user request to continue to next phase from web UI."""
    unanswered_count = data.get('unanswered_count', 0)
    timestamp = datetime.now().isoformat()
    
    print(f"[WebServer] User clicked Continue to Next Phase ({unanswered_count} unanswered questions)")
    
    try:
        # Write a special command to user_input.txt that TUI will recognize
        user_input_path = Path('user_input.txt')
        continue_command = "@[System][ContinuePhase]"
        
        with user_input_path.open('a') as f:
            f.write(f"\n# User clicked Continue Phase from web UI at {timestamp}\n")
            f.write(f"{continue_command}\n")
        
        print(f"[WebServer] Wrote continue command to user_input.txt")
        
        await sio.emit('continue_success', {
            'message': 'Continue signal sent to swarm',
            'unanswered_count': unanswered_count,
            'timestamp': timestamp
        }, to=sid)
        
    except Exception as e:
        print(f"[WebServer] Error writing continue command: {e}")
        await sio.emit('continue_error', {'error': str(e)}, to=sid)


# File watcher for graph.log and phase_status.json
class GraphLogHandler(FileSystemEventHandler):
    """Watch graph.log and phase_status.json for changes and broadcast updates."""
    
    def __init__(self, loop):
        self.loop = loop
    
    def on_modified(self, event):
        if event.src_path.endswith('graph.log'):
            print(f"[WebServer] graph.log updated (inotify), broadcasting changes...")
            # Schedule broadcast in the event loop
            asyncio.run_coroutine_threadsafe(broadcast_graph_update(), self.loop)
        elif event.src_path.endswith('phase_status.json'):
            print(f"[WebServer] phase_status.json updated (inotify), broadcasting phase status...")
            asyncio.run_coroutine_threadsafe(broadcast_phase_status(), self.loop)
    
    def on_created(self, event):
        if event.src_path.endswith('graph.log'):
            print(f"[WebServer] graph.log created (inotify), broadcasting changes...")
            # Schedule broadcast in the event loop
            asyncio.run_coroutine_threadsafe(broadcast_graph_update(), self.loop)
        elif event.src_path.endswith('phase_status.json'):
            print(f"[WebServer] phase_status.json created (inotify), broadcasting phase status...")
            asyncio.run_coroutine_threadsafe(broadcast_phase_status(), self.loop)


def start_file_watcher(loop, log_path='graph.log'):
    """Start watching graph.log for changes using inotify."""
    global observer
    
    event_handler = GraphLogHandler(loop)
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=False)
    observer.start()
    print(f"[WebServer] Started file watcher for {log_path}")


# FastAPI routes
@app.get("/")
async def index():
    """Serve the Vue.js SPA (real-time interface)."""
    return FileResponse('web/dist/index.html')


@app.get("/assets/{path:path}")
async def serve_assets(path: str):
    """Serve Vue.js build assets (JS/CSS)."""
    return FileResponse(f'web/dist/assets/{path}')


@app.get("/api/graph")
async def get_graph():
    """REST API endpoint for graph state."""
    load_graph_state()
    return serialize_graph_state()


if __name__ == '__main__':
    import uvicorn
    
    # Run with uvicorn
    uvicorn.run(
        socket_app,  # Use the Socket.IO wrapped app
        host="0.0.0.0",
        port=5000,
        log_level="info"
    )

