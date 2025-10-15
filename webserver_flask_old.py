#!/usr/bin/env python3
"""
Real-time web interface for Axion Swarm graph visualization.

Provides a Flask web server with WebSocket support for real-time updates
as agents make decisions and update the graph.
"""

import os
import json
import threading
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, send_from_directory, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Import graph analysis functions
import sys
sys.path.insert(0, str(Path(__file__).parent))
from analyze_graph import analyze_graph_log


app = Flask(__name__, 
            static_folder='web/dist',
            template_folder='web')
CORS(app)
socketio = SocketIO(app, 
                    cors_allowed_origins="*",
                    ping_timeout=60,        # Wait 60s for pong before disconnecting
                    ping_interval=25)       # Send ping every 25s to keep connection alive

# Global state
graph_state = {
    'nodes': {},
    'vote_tally': {},
    'specialist_stats': {}
}
connected_clients = set()


class GraphLogHandler(FileSystemEventHandler):
    """Watch graph.log for changes and broadcast updates."""
    
    def __init__(self, log_path):
        self.log_path = Path(log_path)
        self.last_size = 0
        if self.log_path.exists():
            self.last_size = self.log_path.stat().st_size
    
    def on_modified(self, event):
        if event.src_path == str(self.log_path):
            # Check if file actually grew (not just metadata change)
            current_size = self.log_path.stat().st_size
            if current_size > self.last_size:
                self.last_size = current_size
                print(f"[WebServer] graph.log updated, broadcasting changes...")
                broadcast_graph_update()


def load_graph_state(log_path='graph.log'):
    """Load and analyze graph state from log file."""
    global graph_state
    
    try:
        if not Path(log_path).exists():
            return None
        
        nodes, vote_tally, specialist_stats = analyze_graph_log(log_path)
        
        graph_state = {
            'nodes': nodes,
            'vote_tally': vote_tally,
            'specialist_stats': specialist_stats
        }
        
        return graph_state
    except Exception as e:
        print(f"[WebServer] Error loading graph state: {e}")
        return None


def serialize_graph_state():
    """Convert graph state to JSON-serializable format."""
    serialized = {
        'nodes': {},
        'vote_tally': {},
        'specialist_stats': {}
    }
    
    # Convert nodes
    for path, node_data in graph_state['nodes'].items():
        serialized['nodes'][path] = {
            'votes': node_data.get('votes', []),
            'first_seen_phase': node_data.get('first_seen_phase', '1'),
            'first_seen_specialist': node_data.get('first_seen_specialist', 'Unknown')
        }
    
    # Convert vote_tally
    for path, tally in graph_state['vote_tally'].items():
        serialized['vote_tally'][path] = {
            'upvotes': tally.get('upvotes', 0),
            'downvotes': tally.get('downvotes', 0),
            'up_by': list(tally.get('up_by', [])),
            'down_by': list(tally.get('down_by', []))
        }
    
    # Convert specialist_stats (already serializable)
    for specialist, stats in graph_state['specialist_stats'].items():
        serialized['specialist_stats'][specialist] = {
            'upvotes': stats.get('upvotes', 0),
            'downvotes': stats.get('downvotes', 0),
            'total': stats.get('total', 0),
            'by_phase': dict(stats.get('by_phase', {}))
        }
    
    return serialized


def broadcast_graph_update():
    """Broadcast updated graph state to all connected clients.
    
    Also regenerates the static HTML form (graph_form.html) so both
    implementations stay in sync with the same backend state.
    """
    import time
    from datetime import datetime
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
    
    # socketio.emit() broadcasts to all clients by default (no room/to specified)
    # Called via socketio.start_background_task() for proper eventlet integration
    socketio.emit('graph_update', serialized)
    
    emit_time = time.time()
    emit_complete_timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    print(f"[WebServer] 🕐 [{emit_complete_timestamp}] Emit complete")
    print(f"[WebServer] ⏱️  socketio.emit: {(emit_time - serialize_time) * 1000:.2f}ms")
    print(f"[WebServer] ⏱️  TOTAL: {(emit_time - start_time) * 1000:.2f}ms")
    print(f"[WebServer] ✅ Broadcasted update to {len(connected_clients)} client(s)")


@app.route('/')
def index():
    """Serve the Vue.js SPA (real-time interface)."""
    return send_from_directory('web/dist', 'index.html')


@app.route('/assets/<path:path>')
def serve_assets(path):
    """Serve Vue.js build assets (JS/CSS)."""
    return send_from_directory('web/dist/assets', path)




@app.route('/api/graph')
def get_graph():
    """REST endpoint to get current graph state."""
    load_graph_state()
    return jsonify(serialize_graph_state())


@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    client_id = id(threading.current_thread())
    connected_clients.add(client_id)
    print(f"[WebServer] Client connected (total: {len(connected_clients)})")
    
    # Send initial graph state immediately
    load_graph_state()
    serialized = serialize_graph_state()
    emit('graph_update', serialized)
    print(f"[WebServer] Sent initial graph state to new client ({len(serialized.get('nodes', {}))} nodes)")


@socketio.on('request_initial_state')
def handle_request_initial_state():
    """Handle explicit request for initial graph state from client."""
    import time
    start_time = time.time()
    
    load_graph_state()
    load_time = time.time()
    print(f"[WebServer] ⏱️  load_graph_state: {(load_time - start_time) * 1000:.2f}ms")
    
    serialized = serialize_graph_state()
    serialize_time = time.time()
    print(f"[WebServer] ⏱️  serialize: {(serialize_time - load_time) * 1000:.2f}ms")
    
    emit('graph_update', serialized)
    emit_time = time.time()
    print(f"[WebServer] ⏱️  emit: {(emit_time - serialize_time) * 1000:.2f}ms")
    print(f"[WebServer] ⏱️  TOTAL initial state: {(emit_time - start_time) * 1000:.2f}ms")
    print(f"[WebServer] Sent initial state on client request ({len(serialized.get('nodes', {}))} nodes)")


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    client_id = id(threading.current_thread())
    connected_clients.discard(client_id)
    print(f"[WebServer] Client disconnected (total: {len(connected_clients)})")


@socketio.on('request_update')
def handle_update_request():
    """Handle client request for graph update."""
    print(f"[WebServer] Client requested graph update")
    load_graph_state()
    emit('graph_update', serialize_graph_state())


@socketio.on('submit_decisions')
def handle_submit_decisions(data):
    """Handle user form submission from web UI.
    
    The user's selections are converted to @[Graph] commands and written
    to user_input.txt for the Axion main process to read.
    
    Args:
        data: Dict with 'commands' list and 'timestamp'
    """
    commands = data.get('commands', [])
    timestamp = data.get('timestamp', datetime.now().isoformat())
    
    if not commands:
        emit('submission_error', {'error': 'No commands provided'})
        return
    
    # Format as @[Graph] commands
    graph_commands = [f"@[Graph][Update]{cmd}" for cmd in commands]
    
    # Write to user_input.txt for main process to pick up
    try:
        with open('user_input.txt', 'a', encoding='utf-8') as f:
            f.write(f"\n# User submission from web UI at {timestamp}\n")
            for cmd in graph_commands:
                f.write(f"{cmd}\n")
            f.write("\n")
        
        print(f"[WebServer] User submitted {len(commands)} decision(s)")
        
        # Acknowledge submission
        emit('submission_success', {
            'message': f'Successfully submitted {len(commands)} decision(s)',
            'commands': graph_commands,
            'timestamp': timestamp
        })
        
    except Exception as e:
        print(f"[WebServer] Error writing user input: {e}")
        emit('submission_error', {'error': str(e)})


def start_file_watcher(log_path='graph.log'):
    """Start watching graph.log for changes using inotify."""
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    
    class GraphLogHandler(FileSystemEventHandler):
        def on_modified(self, event):
            if event.src_path.endswith(log_path):
                print(f"[WebServer] graph.log updated (inotify), broadcasting changes...")
                # Use socketio.start_background_task for proper eventlet integration
                socketio.start_background_task(broadcast_graph_update)
        
        def on_created(self, event):
            if event.src_path.endswith(log_path):
                print(f"[WebServer] graph.log created (inotify), broadcasting changes...")
                # Use socketio.start_background_task for proper eventlet integration
                socketio.start_background_task(broadcast_graph_update)
    
    event_handler = GraphLogHandler()
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=False)
    observer.start()
    print(f"[WebServer] Watching {log_path} for changes (inotify mode)...")
    return observer  # No observer to return


def run_server(host='0.0.0.0', port=5000, debug=False, log_path='graph.log'):
    """Run the web server with real-time graph updates.
    
    Args:
        host: Host to bind to (default: 0.0.0.0 for all interfaces)
        port: Port to bind to (default: 5000)
        debug: Enable debug mode (default: False)
        log_path: Path to graph.log file (default: graph.log)
    """
    # Clear user_input.txt queue on startup (fresh command queue for this session)
    # But DON'T clear graph.log - load existing data if present
    user_input_path = Path('user_input.txt')
    graph_log_path = Path(log_path)
    
    if user_input_path.exists():
        user_input_path.unlink()
        print("[WebServer] Cleared user_input.txt (fresh queue for this session)")
    
    # Ensure graph.log exists (create empty if needed) so inotify watcher is ready
    if not graph_log_path.exists():
        graph_log_path.touch()
        print(f"[WebServer] Created empty {log_path} (ready for agent updates)")
    else:
        print(f"[WebServer] Loading existing graph data from {log_path}")
    
    # Load initial state
    load_graph_state(log_path)
    
    # Print initial TUI report and generate static HTML form
    if graph_state['nodes']:
        print("\n" + "="*80)
        print("[WebServer] Initial graph state - TUI report:")
        print("="*80)
        from analyze_graph import print_report, generate_html_form
        print_report(graph_state['nodes'], graph_state['vote_tally'], graph_state['specialist_stats'])
        print("="*80)
        
        # Generate initial static HTML form
        html_output = generate_html_form(graph_state['nodes'], graph_state['vote_tally'])
        html_path = Path('graph_form.html')
        with open(html_path, 'w') as f:
            f.write(html_output)
        print(f"[WebServer] Generated static HTML form: {html_path}")
        print("="*80 + "\n")
    else:
        print("\n[WebServer] No graph data found yet - waiting for updates...\n")
    
    # Start file watcher
    observer = start_file_watcher(log_path)
    
    try:
        print(f"\n{'='*80}")
        print(f"🌐 Axion Swarm Web Interface")
        print(f"{'='*80}")
        print(f"Server running at: http://{host}:{port}")
        print(f"Watching: {log_path}")
        print(f"")
        print(f"📺 Available Interfaces:")
        print(f"  • Vue.js Real-Time: http://{host}:{port}/")
        print(f"  • Static HTML Form: http://{host}:{port}/form")
        print(f"  • REST API:         http://{host}:{port}/api/graph")
        print(f"  • TUI Reports:      Printed to this console on updates")
        print(f"")
        print(f"💡 Usage:")
        print(f"  • Run 'python main.py' in another terminal for agent chat (TUI)")
        print(f"  • Open web interface in browser for graph visualization")
        print(f"  • Both read from same {log_path} - fully synchronized")
        print(f"{'='*80}\n")
        
        socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        print("\n[WebServer] Shutting down...")
    finally:
        # Polling thread is daemon, will stop automatically
        if observer:
            observer.stop()
            observer.join()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Axion Swarm Web Interface')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--log', default='graph.log', help='Path to graph.log file')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    run_server(host=args.host, port=args.port, debug=args.debug, log_path=args.log)

