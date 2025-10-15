# Axion Swarm Web UI

Real-time web interface for the Axion multi-agent decision system. Watch as specialists propose questions, vote on answers, and track the decision graph in real-time.

## Transitioning from TUI to Web

Axion Swarm is **gradually transitioning** from terminal-based (TUI) to web-based interfaces while maintaining full backward compatibility.

### Current State: Dual Interface Support

**Terminal (TUI) - Agent Chat**
- **File**: `main.py` (primary Axion agent discussion system)
- **Purpose**: Core multi-agent conversation interface
- **Status**: Primary interface, fully functional
- **Usage**: `python main.py`

**Web Interface - Graph Visualization** 
- **Files**: `webserver.py` + `web/` directory
- **Purpose**: Visual graph decision tree alongside agent chat
- **Status**: In development, coexists with TUI
- **Usage**: `python webserver.py` (run alongside `main.py`)

**Vue.js Web Interface - Production**
- **File**: `web/src/App.vue` (Vue.js SPA)
- **Purpose**: Real-time interactive graph visualization
- **Status**: Active production interface

### Launch Scripts (Recommended)

**Quick Start (Web Server Only)**
```bash
./launch_web.sh
```
Starts the webserver with Vue.js interface on `http://localhost:5000/`

**With Agent Discussion (Optional)**
```bash
# Terminal 1: Start webserver
./launch_web.sh

# Terminal 2: Start agent chat (when you're ready)
python main.py
```

**Advanced: tmux Split Panes**
```bash
./launch_web_tmux.sh
```
Creates a tmux session with split panes - webserver logs on left, TUI chat on right.

### Manual Setup

**Just Web Interface:**
```bash
python webserver.py
# Open: http://localhost:5000/
```

**With Agent Discussion:**
```bash
# Terminal 1: Webserver (clears user_input.txt queue on startup)
python webserver.py

# Terminal 2: Agent chat (watches user_input.txt for web submissions)
python main.py

# Browser: http://localhost:5000/
```

**How It Works:**
1. **Webserver starts** → Clears `user_input.txt` (fresh queue), creates empty `graph.log` if needed, serves Vue.js app
2. **Browser opens** → Real-time graph visualization (empty initially if no prior data)
3. **Optional: Start TUI** → Background thread watches `user_input.txt`
4. **Agents discuss** → Updates written to `graph.log`
5. **Webserver watches** → `graph.log` changes broadcast to browser via WebSocket (instant updates)
6. **User submits via web** → Commands written to `user_input.txt`
7. **TUI file watcher** → Picks up commands, displays as `[Web UI]` in chat
8. **Agents process** → Graph updates → back to step 5
9. **All synchronized** via `graph.log` (agents→web) + `user_input.txt` (web→agents)

### Three Web Implementations

**1. Static HTML Form** - `http://localhost:5000/form`
- Generated snapshot from `graph.log`
- Cascading radio selection
- Shows graph commands
- No real-time updates

**2. Vue.js Real-Time App** - `http://localhost:5000/`
- Live WebSocket updates
- Sacred user state preservation
- Bi-directional communication
- Primary web interface

**3. TUI Reports** - Printed to webserver console
- Terminal-based analysis reports
- Printed on every graph update
- For users who prefer terminal output

**Transition Goal**: Achieve parity, validate web interface, gradually migrate users from TUI to web, then potentially deprecate TUI when web is stable.

## Features (Vue.js Real-Time App)

- **Real-time Updates**: See specialist votes and decisions as they happen via WebSocket
- **Interactive Voting**: Vote up/down on questions and answers, mark nodes with X
- **Decision Submission**: Select radio buttons/checkboxes and submit to the swarm
- **Deselection Support**: Uncheck previously selected multiple-choice items to send `[➖]` (neutral/indifferent)
- **User Thoughts/Comments**: Add free-text thoughts to any graph node (question or answer) using "💭 Add thought" button
  - Thoughts are stored in graph.log using `@[Graph][Regarding]` syntax
  - Display as collapsible "👤 Your thoughts" section with timestamps
  - Adding a thought marks that specific node as "seen" (decrements "NEW" count by 1)
  - Specialists treat `[Regarding]` entries as preferred conversation direction
  - Helps guide discussion and document reasoning
- **Nested Navigation**: Explore follow-up questions in a hierarchical tree
- **Vote Tracking**: Color-coded badges show consensus strength
- **Sacred User State**: Your selections are never cleared by incoming updates
- **Recursive "NEW" Tracking**: 
  - Nodes with unseen content (at ANY depth) show "NEW" badge with count
  - Badge shows total unseen Q+A nodes within (e.g., "NEW 5")
  - Selecting ANY answer in a group marks entire group as "seen"
  - Adding a thought to a node marks THAT node as "seen" (count -1), but keeps counting new descendants
  - "Seen" status cascades upward to update ancestor counts
  - All new content auto-expands to be visible
- **Smart Sorting**: New nodes appear at the end (sorted by votes) until submit, then your selections move to top
- **Collapsible Layers**: Auto-collapse answered layers on submit, auto-expand when new options appear
- **Faithful Graph Rendering**: All questions from graph.log are displayed, even without answers (mindmap style) - user can dismiss unwanted branches with ❌
- **Diff Tracking**: Only changed selections are submitted, reducing redundant commands

## Change Tracking System

The Vue.js interface implements a sophisticated **local backing object** that tracks the entire graph state and intelligently detects new content at any depth.

### How "NEW" Detection Works

**Initial State:**
- On page load, the system takes a snapshot of all existing nodes
- No "NEW" badges appear (everything is "existing")

**When Specialists Add Content:**
- New Q or A nodes are detected and marked as "unseen"
- The system computes **recursive new counts** for every node:
  - Counts how many unseen Q+A nodes exist within (at ANY depth)
  - Example: If `Q1→A1→Q2→A2→Q3` has 3 new items, then Q1 shows "NEW 3", Q2 shows "NEW 3", Q3 shows "NEW 1"

**Automatic Expansion:**
- Any question with new descendants (at ANY depth) automatically expands
- ALL ancestor questions also expand to make new content visible
- Example: If `Q1→A1→Q2→A2` has a new answer A2, then Q2 expands AND Q1 expands

**"Seen" Marking on Selection:**
- When you select ANY answer in a group (radio/checkbox), the ENTIRE group is marked as "seen"
- This includes the question and all its direct answers
- The system recomputes recursive counts, cascading changes upward
- Example: If you select any answer under Q2, then Q2 and all its answers become "seen", and Q1's count updates

**On Submission:**
- All current nodes are snapshotted as "existing"
- All recursive counts reset to 0
- Future updates will only show truly new content

**Benefits:**
- **Deep Nesting Support**: Tracks changes at ANY depth (great-grandchildren, etc.)
- **Immediate Feedback**: Badge counts update instantly when you engage with content
- **No Manual Tracking**: System automatically computes what's new vs seen
- **Efficient**: Only recomputes when changes occur, not on every render

### Data Structure

```javascript
graphChangeLog: {
  // Nodes that existed at last submission
  nodesAtLastSubmit: Set<string>,
  
  // Map: node path → count of unseen descendants
  // Example: { "[Q:single][Q1]": 5, "[Q:single][Q1][A][A1]": 3 }
  recursiveNewCounts: Map<string, number>,
  
  // Nodes user has engaged with (selected an answer in group)
  seenNodes: Set<string>
}
```

## Architecture

### File-Based IPC (Inter-Process Communication)

The system uses **two log files** for bidirectional communication:

```
┌────────────────────────────────────────────────────────────────┐
│  Axion Agents (main.py)                                        │
│  ├─> @[Graph][Update] commands → graph.log                   │
│  └─> File watcher thread ← user_input.txt (tail -f mode)     │
└──────────────────────┬────────────────────┬────────────────────┘
                       │                    │
                  graph.log            user_input.txt
               (agents → web)         (web → agents)
                       │                    │
                       ↓                    ↑
┌────────────────────────────────────────────────────────────────┐
│  FastAPI Backend (webserver.py)                                │
│  ├─> Watches graph.log for changes (inotify)                 │
│  ├─> Parses with graph_parser.py                              │
│  ├─> Broadcasts via WebSocket (async)                         │
│  ├─> Writes user submissions to user_input.txt                │
│  └─> Clears user_input.txt on startup (fresh queue)          │
└──────────────────────┬─────────────────────────────────────────┘
                       │
                       │ (WebSocket)
                       ↓
┌────────────────────────────────────────────────────────────────┐
│  Vue.js Frontend (web/src/)                                    │
│  ├─> Receives real-time graph updates                         │
│  ├─> Preserves user selections (sacred!)                      │
│  ├─> Renders nested question/answer tree                      │
│  └─> Submits votes/selections as @[Graph] commands            │
└────────────────────────────────────────────────────────────────┘
```

### Data Flow Examples

**Agents → Web:**
1. Agent creates graph update: `@[Graph][Update][Q:single][Should we?][A][Yes][👍]`
2. Written to `graph.log`
3. `webserver.py` detects change (inotify)
4. Analyzes graph, broadcasts to browser via WebSocket
5. Vue.js updates UI in real-time

**Web → Agents:**
1. User submits selections in browser
2. Vue.js sends commands to `webserver.py` via WebSocket
3. `webserver.py` writes to `user_input.txt`: `@[Graph][Update][A][Yes][✅]`
4. `main.py` file watcher detects new line (inotify)
5. Displays in TUI as `[Web UI] @[Graph][Update][A][Yes][✅]`
6. Agents see the graph update and continue discussion

**User Thoughts (Web → Graph Log):**
1. User clicks "💭 Add thought" on a question or answer node
2. Enters free-text comment and clicks "Submit"
3. Vue.js sends `submit_thought` event to `webserver.py` via WebSocket
4. `webserver.py` writes to `user_input.txt`: `@[Graph][Regarding][Q:...][A:...][User's comment]`
5. TUI watches `user_input.txt`, picks up the command, and writes it to `graph.log` with `User (Web UI)` prefix
6. TUI displays the thought in the room as a user message
7. `graph.log` file change triggers graph reload
8. Updated graph (with user thoughts) broadcasts to all connected clients
9. User thoughts display under node as "👤 Your thoughts" with timestamp
10. That specific node is marked as "seen" (NEW count -1), cascading to ancestors

## Setup

### Quick Start (Automated)

```bash
# Install dependencies (first time only)
./setup_web.sh

# Launch both webserver and TUI
./launch_web.sh

# OR use tmux for split-pane view
./launch_web_tmux.sh
```

Then open `http://localhost:5000/` in your browser!

### 1. Install Python Dependencies (Manual)

```bash
pip install -r requirements.txt
```

### 2. Install Node.js Dependencies

```bash
cd web
npm install
```

### 3. Build the Frontend

```bash
# Development (with hot reload)
npm run dev

# Production build
npm run build
```

## Running

### Option 1: Development Mode (Recommended)

Run the backend and frontend separately for hot-reload during development:

**Terminal 1 - Backend:**
```bash
python webserver.py
```

**Terminal 2 - Frontend:**
```bash
cd web
npm run dev
```

Then visit: `http://localhost:3000`

### Option 2: Production Mode

Build the frontend once, then run only the backend:

```bash
# Build frontend
cd web
npm run build
cd ..

# Run backend (serves built frontend)
python webserver.py
```

Then visit: `http://localhost:5000`

### Option 3: With Axion Running

Run Axion Swarm alongside the web server:

**Terminal 1 - Axion Swarm:**
```bash
python main.py
```

**Terminal 2 - Web Server:**
```bash
python webserver.py
```

**Terminal 3 - Frontend Dev (optional):**
```bash
cd web
npm run dev
```

## Usage

### Viewing Real-Time Updates

1. Start Axion Swarm (`python main.py`)
2. Start the web server (`python webserver.py`)
3. Open browser to `http://localhost:5000`
4. Watch as specialists propose questions and vote in real-time

### Voting on Nodes

**Vote Schema (Emoji-based for clarity):**

**Specialist Votes (Advisory):**
- **👍** = Upvote/recommend - "I recommend this direction"
- **👎** = Downvote/concern - "I have concerns about this"

**User Votes (Authoritative - from Web UI):**
- **✅** = Approve/decide - "I've decided on this" (authoritative approval via radio/checkbox selection)
- **❌** = Dismiss/close - "Close this path permanently" (authoritative closure)
- **➖** = Neutral/changed mind - "No longer prioritizing this" (user clears previous approval)

The visual distinction reflects authority: **checkmark/red X = user decisions** that directly control the graph, **thumbs = specialist opinions** that guide discussion.

**User Actions in Web UI:**
- **Select radio button** → sends `[✅]` for chosen answer
- **Select checkbox** → sends `[✅]` for selected options
- **Deselect previously approved checkbox** → sends `[➖]` to mark as neutral
- **Click ❌ button** → sends `[❌]` to dismiss/close that node permanently

### Submitting Decisions

1. Select radio buttons for single-choice questions (implicit ✅ approval)
2. Select checkboxes for multiple-choice questions (implicit ✅ approval)
3. Optionally click ❌ to dismiss/close any node permanently
4. Click "Submit Decisions to Swarm"
5. Your choices convert to `@[Graph][Update]` commands with emoji markers

**Intelligent Diff Tracking:**

The web UI tracks your last submission and **only sends what has changed** on subsequent submissions. This means:

- **First submission**: Sends all your selections/votes
- **Subsequent submissions**: Only sends new/changed selections and votes
- **No changes**: If you click submit without making changes, nothing is sent (displays "No changes to submit")

**Benefits:**
- Avoids redundant commands in `graph.log`
- Cleaner agent discussion (specialists only see actual changes)
- You can safely click submit multiple times
- Precise change tracking for better collaboration

**Example:**
```
Submit 1: Select Options A, B → Sends [A][✅], [B][✅]
Submit 2: Add Option C → Sends [C][✅] (only the new one)
Submit 3: Remove Option B → Sends [B][➖] (only the deselection)
Submit 4: No changes → Sends nothing
```

### Cascading Selection (Single-Choice Questions)

When you select a nested radio button (e.g., a deeply-nested answer), the system **automatically selects all parent radio buttons** in the path. This ensures logical consistency in the decision tree.

**Example:**
```
[Q] What emergency authority should the sitter have?
  [A] Transport to emergency vet ← automatically selected
    [Q] What spending limit?
      [A] $300 (recommended) ← you click this
```

When you click "$300 (recommended)", the parent answer "Transport to emergency vet" is automatically selected.

**Implementation:**
- **Vue.js App**: Uses path-based reactive state tracking
- **Static HTML Form**: Uses SHA-1 hash-based ID lookups to avoid radio button group conflicts

### Command Mapping

Your UI actions become graph commands:

| Action | Result |
|--------|--------|
| Select radio button | `[Q:single][Question?][A][Answer][✅]` |
| Select checkbox | `[Q:multiple][Question?][A][Option][✅]` |
| Deselect previously approved checkbox | `[Q:multiple][Question?][A][Option][➖]` |
| Click ❌ dismiss button | `[Node path][❌]` |

**Note**: Users no longer send explicit 👍/👎 votes - selection (✅) and dismissal (❌) are the primary actions. Specialists send 👍/👎 advisory votes.

## Configuration

### Backend (webserver.py)

```bash
python webserver.py --host 0.0.0.0 --port 5000 --log graph.log
```

Options:
- `--host`: Host to bind to (default: 0.0.0.0)
- `--port`: Port to bind to (default: 5000)
- `--log`: Path to graph.log (default: graph.log)
- `--debug`: Enable debug mode

### Frontend (web/vite.config.js)

The frontend proxies API calls to the backend. Edit `vite.config.js` if your backend runs on a different port:

```javascript
server: {
  port: 3000,
  proxy: {
    '/api': 'http://localhost:5000',
    '/socket.io': {
      target: 'http://localhost:5000',
      ws: true
    }
  }
}
```

## Components

### App.vue
Main application container with:
- WebSocket connection management
- Graph state management with change tracking (`graphChangeLog`)
- User selection preservation
- Recursive new count computation
- "Seen" node tracking and cascade logic
- Automatic expansion of questions with new descendants
- Form submission logic with diff tracking

### QuestionNode.vue
Recursive component for questions/answers with:
- Vote buttons for questions and answers (user selections count as +1 upvote)
- Agent vote comments displayed on BOTH questions and answers
- Radio/checkbox selection for answers (triggers "seen" marking for entire answer group)
- "NEW" badge display with recursive descendant count (all Q/A nodes at any depth)
- Smart sorting (user selections first, then by votes, then newest)
- Faithful graph rendering (questions shown even without answers - user can dismiss with ❌)
- Collapsible/expandable UI based on layer interaction state
- Nested follow-up question rendering at unlimited depth
- Character-by-character path parsing (no regex) for correct nesting detection
- Atomic graph update handling (intermediate nodes filtered, only complete paths shown)
- Color-coded consensus badges
- Props: receives `graphChangeLog` for new count display

## WebSocket Events

### Client → Server

- `connect`: Initial connection
- `disconnect`: Client disconnects
- `request_update`: Request full graph state
- `submit_decisions`: Submit user's votes/selections

### Server → Client

- `graph_update`: Broadcast new graph state
- `submission_success`: Acknowledge successful submission
- `submission_error`: Report submission error

## State Preservation

**CRITICAL**: The Vue app NEVER clears user selections when receiving updates. This ensures:

1. User can take their time making decisions
2. Specialists' votes don't interrupt user workflow
3. Radio buttons/checkboxes remain sacred
4. Only NEW questions/answers are added

## Graph Parser Architecture

### `graph_parser.py` - Character-by-Character Parsing

The parser uses **character-by-character iteration** instead of regex for robustness:

**Key principles:**
- **No regex for path traversal** - iterate through bracket contents token by token
- **Atomic updates** - each graph.log line creates multiple intermediate nodes in one atomic operation
- **Faithful parsing** - all nodes in a path are created (e.g., `[Q][text][A][text][Q][text]` creates 3 nodes)
- **Vote attribution** - votes are stored on the full path (last segment), never inherited by children or parents
- **User selections = upvotes** - ✅ votes count as +1 upvote, same as specialist 👍 votes

**Example parsing:**
```
[Q:single][Who...][A][Mid-market / enterprise][Q:single][What level...][👍][comment]
```
Creates 3 nodes:
1. `[Q:single][Who...]` - root question
2. `[Q:single][Who...][A][Mid-market / enterprise]` - answer node
3. `[Q:single][Who...][A][Mid-market / enterprise][Q:single][What level...]` - nested question (gets the vote)

## Development

### Adding New Features

1. Update `QuestionNode.vue` for new node types
2. Update `App.vue` for new submission logic
3. Update `webserver.py` for new server endpoints
4. Update `graph_parser.py` for new graph analysis (avoid regex, use character iteration)

### Debugging

- **Backend logs**: Watch `stderr` from `webserver.py`
- **Frontend logs**: Browser console (F12)
- **WebSocket**: Browser Network tab → WS filter
- **Graph state**: `http://localhost:5000/api/graph` (REST endpoint)

## Troubleshooting

### WebSocket not connecting

```
Error: WebSocket connection failed
```

**Solution**: Ensure backend is running on expected port:
```bash
python webserver.py --port 5000
```

### Updates not appearing

**Solution**: Check that `graph.log` exists and is being written to:
```bash
# Watch graph.log
tail -f graph.log
```

### User selections cleared

**Solution**: This should never happen! If it does, check `updateGraphData()` in `App.vue` - it should only add new data, never replace.

## License

Same as Axion Swarm main project.

