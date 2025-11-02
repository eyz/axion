# Axion Swarm 🤖

**Multi-Agent Discussion System with Natural Expert Collaboration**

Axion Swarm orchestrates conversations between specialized AI agents to provide comprehensive, well-reasoned answers to complex questions. Each agent brings domain expertise while maintaining complete isolation—thinking independently, building on each other's insights, and converging naturally through progressive discussion.

**What makes it different:** Specialists collaborate as an **internal expert team** while you're away, delivering well-reasoned synthesis in under a minute. You get the benefit of multiple expert perspectives debating, refining, and converging—without waiting hours for responses. Works equally well for real-time chat or async consultation across any domain.

---

## 🆕 Recent Updates

### November 2, 2025 - Web UI Phase Management + PENDING Badge + Active Graph Context

**Web UI Phase Management:**
- **Phase Status Indicator**: Header shows current phase number and execution state (⏸️ Waiting / ▶️ Running / 🏁 Final) with color-coded backgrounds (orange for waiting, green for running, purple for final)
- **Continue to Next Phase Button**: Unblocks TUI backend from web UI with pending question count display. Disabled (grayed) when phase running, enabled when system paused. Shows "⚠️ X pending" or "✅ All answered" based on state
- **Decision Count Badge**: Submit button shows number of pending decisions to be submitted (real-time count)
- **Smart Button States**: Continue button only shows "All answered" when questions answered AND submitted (prevents state confusion)
- **Backend/Frontend IPC**: TUI backend writes to `phase_status.json` (phase number, waiting state, is_final flag), webserver watches with inotify and broadcasts to browser via WebSocket

**PENDING Badge System:**
- **Orange PENDING badge**: Shows on questions needing user selection submission (bubbles up through answered paths like NEW badge)
- **Recursive logic**: Follows "root-inward" path - only counts/shows pending along paths where ancestors have submitted selections
- **Thought engagement**: Adding thought to question clears PENDING (counts as engagement without selection)
- **Accurate counting**: Only counts root-level questions and descendants along answered paths (not all questions in graph)

**Bug Fixes:**
- **NEW badge initialization**: Fixed bug where all existing nodes from graph.log incorrectly marked as NEW on page load. Now populates `nodesAtLastSubmit` set on first load instead of clearing it
- **Auto-collapse after submit**: Questions now properly auto-collapse after submission even if manually toggled. Added watcher that clears `userManuallyToggled` flag when submission completes
- **Selection restoration**: Fixed bug where selections weren't restored when first `graph_update` had 0 nodes. Now runs restoration when data arrives even if first update was empty
- **Dismissed question count**: Pending count now updates immediately when dismissing questions (optimistic UI using `isNodeXed()` check)

**Active Graph Context for Specialists:**
- **Prevents hallucination**: Specialists now receive compact list of active graph paths showing exactly what exists to vote on
- **Injected in all phases**: Active paths shown before instruction prompt in Phase 1, 2, 3+, and Final
- **Filtered intelligently**: Excludes dismissed (`❌`) and duplicate (`🧹`) paths - shows only active paths
- **Dual purpose**: Paths available for voting (`@[Graph][Update]`) AND extending (`@[Graph][Create]` for nested Q/A)
- **Hierarchical display**: Root questions with answers and nested questions (limited depth for compactness)

**TUI Simplification:**
- **Removed question-blocking logic**: TUI no longer blocks on unanswered questions in left sidebar
- **Always pause after phases**: Every phase (except final) pauses for user to review via web UI
- **Web UI controls continuation**: All phase progression controlled via "Continue to Next Phase" button in web interface
- **Updated pause messages**: Direct users to web UI for decisions and phase continuation

**Architectural Clarifications:**
- **Backend/Frontend separation**: TUI server (`main_tui.py`) is the backend (runs LangGraph, agents, LLM orchestration); webserver (`webserver.py`) is the frontend (serves web UI, handles browser WebSockets, presentation layer)
- **File-based IPC (current)**: `graph.log` (backend→frontend state), `user_input.txt` (frontend→backend commands), `phase_status.json` (backend→frontend phase state)
- **Future architecture**: Replace file-based IPC with direct WebSocket/REST between backend and frontend servers

**Files Modified:** `web/src/App.vue`, `web/src/components/QuestionNode.vue`, `webserver.py`, `main_tui.py`, `axion_swarm/agents.py`

---

### November 2, 2025 (Late Session) - Critical Fixes + Dedupe Schema Redesign

**New Dedupe Schema - Eliminates Hallucinations:**
- **Problem**: Chair's LLM repeatedly hallucinated "path is duplicate of itself" despite validation rules - old schema was positionally ambiguous
- **Old format** (ambiguous): `@[Graph][Update][duplicate][🧹][canonical]` ← Which position is which?
- **New format** (explicit): 
  ```
  @[Graph][KeepCanonical][path_to_keep]       ← Clear: this stays
  @[Graph][MarkDuplicate][path_to_remove]     ← Clear: this goes
  ```
- **Result**: Chair now correctly identifies semantic duplicates without self-reference hallucinations
- **Impact**: Two-command format removes positional ambiguity, tested successfully in production

**Chair Deduplication Hallucination Fixes:**
- **Bug**: Chair's LLM hallucinated 3 times today marking paths as duplicates of themselves or parent questions
- **Root Cause**: Ambiguous single-command format `[duplicate][🧹][canonical]` was cognitively confusing
- **Backend Validation** (`graph_tool.py` lines 488-538):
  - Added 3-level validation for duplicate markers before processing
  - Rejects: Answer marked as duplicate of parent question
  - Rejects: Question marked as duplicate of its own answer  
  - Rejects: Path marked as duplicate of itself
  - Logs rejections to stderr and `graph.log` with reason
  - Prevents auto-clear mechanism from executing on invalid markers
- **Prompt Enhancement** (`prompts.py` lines 3125-3141):
  - Added "CRITICAL VALIDATION RULES" section with 4 explicit prohibitions
  - Shows wrong examples for each rule (e.g., `@[Graph][Update][Q:single][What?][A][Option 1][🧹][Q:single][What?]`)
  - Emphasizes: only compare paths at SAME STRUCTURAL LEVEL
- **Data Cleanup**: Removed 37 invalid lines from production `graph.log` (25 bad duplicate markers + 12 cascading auto-clears)

**Viewport Pinning Hides New Questions Fix:**
- **Bug**: Questions added in Phase 2+ were counted as "pending" but invisible - viewport pinning froze display at Phase 1's question count
- **Fix** (`App.vue` lines 497-505): Modified `displayedRootQuestions` to append new questions to pinned order instead of hiding them
- **Result**: New questions from later phases now appear at bottom of list, no longer hidden ghosts

**Modal Click-Through Prevention:**
- **Bug**: "New Content" modal could be dismissed by clicking anywhere on backdrop, defeating purpose of forcing awareness
- **Fix** (`App.vue` line 13): Removed `@click="acknowledgeNewContent"` from overlay - now ONLY the button dismisses modal
- **UX improvement**: Users must explicitly click "Acknowledge & Continue" button to proceed

**PENDING Badge Reactivity Fix:**
- **Bug**: When nested question was answered and submitted, parent question's PENDING badge didn't clear (Vue reactivity not tracking nested state changes)
- **Root Cause**: Answer paths in `selectionsAtLastSubmit` stored as SHORT relative paths `[A][text]`, but code checked against FULL paths - `startsWith()` never matched
- **Fix** (`QuestionNode.vue` line 406): Build full answer path by prepending parent question path: `const fullAnswerPath = props.path + answerPath`
- **Result**: PENDING badge now correctly clears from parents when nested questions are answered

**New Dedupe Implementation:**
- `prompts.py`: Chair dedupe prompt with KeepCanonical/MarkDuplicate format, updated validation rules, updated specialist guidance
- `graph_tool.py`: Processes new operations, validates no path marked as both canonical AND duplicate
- `graph_parser.py`: Recognizes KeepCanonical/MarkDuplicate operations, marks duplicates in vote_tally

**Other Fixes:**
- `web/src/App.vue`: Viewport pinning fix, modal click-through prevention, removed inaccurate modal text
- `web/src/components/QuestionNode.vue`: PENDING badge reactivity fix, answer viewport pinning fix, duplicate specialist name deduplication
- `webserver.py`: Atomic phase broadcasting (buffers updates during phase execution)

**Data Cleanup**: Removed 72+ invalid self-duplicate markers from production graph.log

**Testing Status**: New schema tested and verified working - Chair correctly identified 2 semantic duplicates without hallucinations ✅

---

### November 1, 2025 (Evening) - De-Duplication Fixes + Web UI Polish + Graph-Native Architecture

**De-Duplication System Improvements:**
- **Prompt Structure Redesign**: Chair de-dupe prompt restructured with system-instructions-first ordering (Context→Requirements→Graph Rules→Expectations→Data). Prevents objective contamination by establishing role/mode before presenting data.
- **Pure Graph Schema**: Removed all user natural language context - Chair now receives ONLY graph paths with metadata. Eliminates conversational triggers that caused Chair to respond instead of de-duplicate.
- **Syntax Clarity**: Added explicit examples showing duplicate≠canonical (must be different paths), newer→older marking.
- **Auto-Clear Selections**: When Chair marks duplicates, system automatically writes `[➖]` to clear any user selections on duplicate paths (appears as User (Web UI) action).
- **Bug Fixes**: Fixed UnboundLocalError from shadowing `import re` statements; 400 BadRequestError now gracefully continues (returns synthetic pass message instead of crashing).

**Web UI Enhancements:**
- **Hide Duplicates Toggle (Fixed!)**: Actually works now - added missing `voteTally` prop, fixed event bubbling, exposed reactive state. Defaults to ON (duplicates hidden). Filters at all levels: root questions, answers, nested questions.
- **Viewport Freezing**: Prevents jarring changes while viewing - new nodes only appear when section is off-screen. Separate tracking for answer lists and root question order.
- **Improved Duplicate Styling**: Opacity 0.85 (was 0.35 - much more readable), lighter background #e8edf2, brightness(0.75) filter, strike-through only on text (not badges/emoji), tooltips functional.
- **Thought Marks as Seen**: Adding thought to a node marks it as "seen" (decrements NEW count by 1, cascades to ancestors).

**Architectural Evolution - Graph-Native Interaction:**
- **@[User] Deprecated**: Specialists no longer ask prose questions like "@[User], what is X?". All user questions must be `@[Graph][Create]` nodes with answer options.
- **Graph-First Design**: User interaction moving entirely to Web UI graph (chat interface being removed). Reduces tokens, improves UX, creates single unified knowledge structure.
- **Specialist Guidance**: Rebalanced create/vote encouragement - "actively propose" new paths but "do quick check" for duplicates. Strengthened anti-echo warnings with FORBIDDEN designation.

**Files Modified:** `axion_swarm/prompts.py`, `axion_swarm/agents.py`, `axion_swarm/graph_tool.py`, `web/src/App.vue`, `web/src/components/QuestionNode.vue`

---

### November 1, 2025 (Morning) - Graph Tool: Create vs Update Split + Automated De-Duplication
- **@[Graph][Create] vs @[Graph][Update] Separation**: Two distinct operations separate path creation from voting. Create proposes NEW path segments (final segment must be new), Update votes on EXISTING complete paths. System validates Create (rejects if path exists) vs Update (rejects if path doesn't exist). Specialists can use both in same message. Prevents structural duplication at source.
- **Automated Chair De-Dupe Pass**: At end of each phase, Chair automatically reviews all @[Graph][Create] operations from that phase and marks semantic duplicates (same meaning, different wording). Chair receives graph paths with vote counts, user selection signals (✅❌), and user thought counts. Comprehensive logging to `chair-dedupe.log` with full LLM prompt, raw response, and graph operations broadcast to room.
- **Smart Canonical Selection**: Chair uses weighted priority: (1) User engagement signals (✅ selections, 💭 thoughts - highest), (2) Net vote score (👍-👎), (3) Graph structure position (Chair's judgment), (4) First occurrence.
- **Web UI Duplicate Handling**: Duplicates styled for visibility (opacity 0.85, brightness 0.75, lighter background) with strike-through text on labels only. Inputs disabled, no vote/thought buttons. Can expand/collapse. Tooltips show canonical path. Toggle "Hide Duplicates 🧹" (defaults ON) in sidebar to completely hide them. Auto-clears user selections when path marked duplicate.
- **Specialist Guidance**: Duplicates are neutral redirects (not negative judgments) - concept is good, just use canonical path. Never pursue, extend, or cite duplicate paths. Migrate all votes/nodes to canonical.
- **No Test-Case Examples**: All prompt examples use generic placeholders (Option A/B, Approach X, etc.) - system is domain-agnostic. Graph questions must be specific decision points, not restatements of user's overall question.
- **User Thoughts Feature**: Users can add free-text comments/thoughts to any graph node (question or answer) using `@[Graph][Regarding]` syntax, displayed in Web UI with "💭 Add thought" button - specialists MUST consider all user thoughts when formulating responses. Adding a thought marks that node as "seen" (decrements "NEW" count by 1).
- **Smart Collapse on Submit**: Questions collapse individually based on user interaction (selections, votes, thoughts) - sibling questions stay in their current state. No more unintended collapses!
- **Checkbox Stability Fix**: Adding thoughts to selected checkbox answers no longer toggles the checkbox state - "Add thought" UI moved outside `<label>` wrapper
- **Hide Expand Arrow**: Questions without child answer nodes no longer show expand arrow for cleaner mindmap-style UI
- **Auto-Expansion Investigation**: Confirmed both new AND existing questions auto-expand when they receive new descendants at any depth
- **Codebase Cleanup**: Removed legacy `analyze_graph.py` (888 lines) and static HTML form, replaced with focused `graph_parser.py` (167 lines) - 80% code reduction, 100% active code
- **"NEW" Badge System**: Visual indicators for newly added nodes since last submission, with recursive counting of unseen descendants and proper cascading when groups marked as "seen"
- **Deselection Support**: Multiple-choice items can be unchecked to send `[➖]` (neutral/indifferent), enabling full state management
- **Per-Question Expansion**: Only questions that receive new children expand, not entire layers - precise control prevents unnecessary re-expansion
- **FastAPI Migration**: Migrated webserver from Flask to FastAPI for improved WebSocket performance and real-time updates (~50ms latency)
- **Collapsible Layers**: Intelligent auto-collapse/expand based on user interaction and new node arrival
- **Smart Sorting**: Vote-based sorting with user selection priority and newest-first tiebreaker
- **Emoji Vote Schema**: Clear differentiation between user authoritative actions (`[✅]`, `[❌]`, `[➖]`) and specialist advisory votes (`[👍]`, `[👎]`, `[🧹]` Chair-only)

---

## 📋 Web UI - Planned Enhancements

**Design/Discussion Items:**

- [ ] **User Upvote/Downvote Buttons (#7)** - Make vote badges (👍/👎) clickable so users can vote on questions/answers like specialists do, not just dismiss with ❌
   
- [ ] **User Downvote Semantics (#10)** - Define behavior: Should user 👎 act as "partial dismiss" (don't want to pursue but willing to continue discussion, may dismiss later)?
   
- [ ] **Multiple Questions Under Single Answer (#14)** - UX consideration: When an answer has multiple child questions and user interacts with one, should:
  - Only that question collapse on submit? (current behavior)
  - All sibling questions under that answer collapse together?
  - User configurable preference?

---

## ✨ What Makes Axion Swarm Different

### Natural Human-Like Discussion
Specialists collaborate like real expert panels—with clear personas, independent thinking (via `<think>` tags), and natural conversation flow. The system creates genuine multi-party discussions, not robotic back-and-forth.

### Complete Agent Isolation
Each specialist is a fresh LLM instance with **zero shared context** outside the visible transcript. This architectural choice ensures authentic independent perspectives and prevents hidden coordination or groupthink.

### Internal Team Collaboration
The multi-phase discussion happens **internally** while you're away. Specialists speak candidly, debate approaches, and refine thinking through cross-pollination—then Chair synthesizes the team's collective wisdom into a comprehensive answer. Fast system response (< 1 minute) with flexible user participation (real-time or async).

### Atomic Phases with Smart Filtering
Strategic message filtering controls what each agent sees at different stages:
- **Phase 1**: Independent assessments (specialists see only the User's question)
- **Phase 2**: Cross-pollination (specialists review others' Phase 1 responses, own responses hidden)
- **Phase 3+**: Iterative refinement (full history visible, specialists pass when nothing new to add)
- **Final Phase**: Synthesis without anchoring (own contributions hidden again)

### Dynamic Team Composition & Domain-Agnostic Design
Start with a focused core team, bring in specialists as needed, auto-dismiss when done:
- **Core team** (Context, Research, Skeptic, Ethicist) works across **any domain**—legal, medical, business, technical, creative
- **Domain specialists** configured per use case (current technical roster validates architecture, not prescriptive)
- Non-core specialists **auto-dismiss after contributing** to keep discussions focused
- Chair coordinates room composition with `@mention` invitations

### Dual Provider Architecture
- **Azure OpenAI**: Parallel execution (15 specialists concurrently), 10-15x faster
- **Ollama**: Sequential execution (local GPUs), optimal for VRAM management
- Switch providers with a single environment variable

### Real-Time Information & Collaborative Tools
Specialists have access to three complementary tools:
- **@[Search][query]** - Find relevant sources with Tavily Search API (snippets + AI synthesis)
- **@[ReadURL][url]** - Read full page content with Jina AI Reader (complete articles/docs)
- **@[Graph][...]** - Build structured decision trees collaboratively with real-time web visualization

**Search Workflow**: Search first to find candidate URLs → ReadURL to fetch full content from promising sources. Results appear as tool messages with requester tracking.

**Graph Workflow**: Context proposes decision questions (`[Q:single]` for radio buttons, `[Q:multiple]` for checkboxes, `[Q:open]` for free text) → ALL specialists MUST vote on questions and answers (specialists use `[👍]` valuable path/agree, `[👎]` discourage/remove, with mandatory comments reflecting entire path context) → Chair can mark duplicates with `[🧹][canonical path][comment]` when newer paths are semantically identical to existing paths (specialists skip duplicates and migrate votes/nodes to canonical) → Specialists propose answers and extend paths with follow-up questions → Specialists use `[If]` citations to explore potential paths hypothetically or `[Because]` to reference chosen/consensus paths (NEVER `[Because]` on `[❌]`-marked closed paths) → User selects answers via web UI (selection sends `[✅]` approval, dismiss button sends `[❌]` closure, deselecting previously approved checkbox sends `[➖]` neutral) → User can add free-text thoughts using `[Regarding]` on any node to guide discussion → **Specialists MUST consider all `[Regarding]` entries from User** → Creates structured decision tree with full provenance and semantic context accumulation.

### Intelligent Convergence
- **Progressive retraction**: Specialists increasingly likely to pass as phases progress
- **Probabilistic stagnation detection**: Chair uses multi-signal model (user engagement, phase count, specialist activity) to detect discussion plateau and trigger final phase automatically
- **Aggressive convergence with justification**: Discussions naturally conclude by Phase 8, but can extend when genuinely productive (active user + research + specialists providing answers)
- **Natural consensus**: System detects when all specialists pass (implicit agreement)

### 🛡️ Validation Guard System - Data Integrity Protection

The system **actively guards against malformed graph updates** and **scolds specialists** when they violate schema rules:

**What It Guards**:
- **Multiple answers in one entry**: `[A][$200][A][$500][A][$1000]` ❌ → Rejected, specialist taught to use separate entries
- **Nested structure errors**: Consecutive answers at any nesting level → Rejected with targeted guidance
- **LLM hallucinations**: AI-generated invalid syntax → Rejected before data corruption
- **Copy-paste mistakes**: Accidental chaining → Caught and prevented

**How It Works**:
1. **Guards**: Real-time validation of every `@[Graph][Update]` before writing to graph.log
2. **Scolds**: Targeted Notice to @[All] specialists explaining what went wrong with correct examples
3. **Protects**: Multi-layer defense (backend validation → graph.log integrity → frontend validation → Web UI rendering)
4. **Educates**: Pattern detection shows most relevant correction based on what they attempted

**Actions Taken**:
- ⚠️ TUI shows stderr warning with error details
- 📢 Notice message injected into conversation (all specialists see it)
- 🚫 Malformed entry NOT written to graph.log
- 👁️ Web UI never renders invalid options
- ✅ Specialist encouraged to resubmit SAME content in correct format (contribution is valuable, only syntax was wrong)

This is a **safety net for both human specialists and LLM agents**, ensuring the decision tree stays clean and users only see valid, selectable choices. See `test_validation.py` for comprehensive test coverage.

**For Developers - Extending Validation**:

The guard system follows a "loud and helpful" philosophy: never silently accept bad data, always explain what went wrong, always educate with examples. When adding new validation rules:

1. Add detection logic to `validate_graph_update()` in `axion_swarm/graph_tool.py`
2. Add pattern-specific Notice message with targeted guidance
3. Mirror validation in `graph_parser.py` (frontend safety)
4. Add test case to `test_validation.py`
5. Update `prompts.py` with invalid/valid examples
6. Run `python test_validation.py` to verify

**Philosophy**: Bad data is exponentially more expensive than validation. A malformed entry in graph.log corrupts all downstream processing. The guard system prevents data corruption at source, educates specialists in real-time, and maintains Web UI quality. See ARCHITECTURE.md § "For Future Development - Extending the Guard System" for complete guide.

**Implementation Notes - Real-World Lessons**:

Critical bugs fixed during production use (documented for future Vue 3 + reactive state projects):

1. **Vue 3 `reactive(new Set())` doesn't trigger watchers reliably** → Use `reactive({})` with timestamps: `obj[key] = Date.now()`
2. **Prop type mismatch silently fails** → If you change `Set` to `Object` in parent, update child `type:` prop definition
3. **Function definition order matters in setup()** → Define dependencies before functions that use them; use `.value` for computed props
4. **State machines need cleanup** → High-priority directives must delete low-priority entries to prevent stale accumulation
5. **Comprehensive logging is essential** → Log every state transition with before/after metrics for complex multi-priority systems
6. **Function prop drilling can silently fail** → In recursive components, verify callback functions are callable at each level with comprehensive logging

See ARCHITECTURE.md § "Smart Collapse/Expand Behavior" → "Critical Implementation Lessons" for detailed symptoms, solutions, and code examples.

---

### Production-Ready Features
- **Dual Interface Support**: Terminal (TUI) for agent chat + Web interface for graph visualization—run both simultaneously
- **Interactive TUI Mode**: Real-time chat interface with automatic question blocking—specialists' @[User] questions pause phase progression until answered. Features collapsible messages (2σ auto-collapse), interactive to-do sidebar (F2), modal message view with reply/dismiss actions, and Final Phase invalidation
- **Real-Time Web Interface**: FastAPI + Vue.js SPA with instant WebSocket updates (~50ms)—watch specialists vote in real-time, vote on questions/answers, cascading radio button selection, sacred user state preservation, intelligent diff tracking (only submits changes)
- **Checkpoint/Resume**: Automatic state persistence with config validation, checkpoint saved just before phase starts
- **Rate limit handling**: Automatic retry with global coordination across parallel agents
- **Token tracking**: Per-agent visibility into context utilization
- **Think transparency**: All reasoning visible on stderr (dark green), never shared with other agents

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Azure OpenAI account (default) or Ollama (local)
- Tavily API key (optional, for search)

### Installation

```bash
# Clone repository
git clone https://github.com/eyz/axion.git
cd axion

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Configuration

**Azure OpenAI** (default):
```bash
PROVIDER=azure_openai
AZURE_OPENAI_ENDPOINT=https://[your-resource].cognitiveservices.azure.com/
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_MODEL=gpt-5-mini
AZURE_OPENAI_DEPLOYMENT=gpt-5-mini
```

**Ollama** (local):
```bash
PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
DEFAULT_MODEL=hf.co/bartowski/Qwen_Qwen3-30B-A3B-Thinking-2507-GGUF:Q5_K_M
OLLAMA_NUM_CTX=36992
```

**Tavily Search** (optional):
```bash
TAVILY_API_KEY=your-tavily-key
```

### Run

**Simple CLI Mode** (single prompt at start):
```bash
python main.py
```

**Interactive TUI Mode** (real-time chat with automatic question blocking):
```bash
python main_tui.py
```

**TUI Features:**
- Real-time message injection at any phase
- Automatic phase blocking when specialists ask @[User] questions
- Interactive to-do sidebar (F2 to toggle) with click-to-reply
- Statistical auto-collapse for long messages (2σ threshold)
- Scrollable conversation history with speaker emojis
- Keybindings: Ctrl+C/Ctrl+D (quit), Page Up/Down (scroll), Home/End

See [ARCHITECTURE.md](ARCHITECTURE.md) for complete TUI documentation and keyboard shortcuts.

### Web Interface (Graph Visualization)

Run web interface alongside TUI for real-time graph visualization:

```bash
# Terminal 1: Web interface (FastAPI + uvicorn)
./launch_web.sh
# Or directly: venv/bin/python webserver.py

# Terminal 2: Agent chat (TUI)
venv/bin/python main_tui.py

# Browser: http://localhost:5000
```

**Web Features:**
- **Real-time updates**: Watch specialists vote as they happen (WebSocket)
- **Vote on any node**: 👍/👎/❌ buttons on questions and answers (user selections count as +1 upvote)
- **Agent vote comments**: See specialist reasoning on BOTH questions and answers
- **Cascading selection**: Selecting nested radio automatically selects parents
- **Sacred state**: Your selections never cleared by incoming updates
- **Diff tracking**: Only submits changes since last submission (no redundant commands)
- **Recursive "NEW" tracking**: Badges show unseen content at ANY depth with counts (e.g., "NEW 5"), auto-expand ancestors, marking entire groups as "seen" when you select any answer
- **Smart sorting**: User selections first, then by votes, newest first as tiebreaker
- **Faithful graph rendering**: ALL questions from graph.log displayed (even without answers) - dismiss unwanted branches with ❌
- **Unlimited nesting**: Questions can have answers with nested questions at any depth
- **Smart collapse/expand**: Questions you interacted with auto-collapse on submit (keep focus), NEW content force-expands with ancestor chain (draw attention), manual user toggles preserved until NEW content overrides
- **Dual formats**: Vue.js real-time (`/`) + Static HTML snapshot (`/form`)
- **TUI reports**: Printed to webserver console on every update

**Quick Setup:**
```bash
bash setup_web.sh  # Install dependencies
./launch_web.sh    # Start FastAPI server
```

See [WEB_UI_README.md](WEB_UI_README.md) for complete web interface documentation.

---

## 📚 Architecture Overview

Axion Swarm uses LangGraph for state management and workflow orchestration. Specialists execute in phases, with Chair coordinating and synthesizing.

### Core Components

| File | Purpose |
|------|---------|
| [`main.py`](main.py) | Simple CLI mode entry point |
| [`main_tui.py`](main_tui.py) | Interactive TUI mode with Textual (1494 lines) |
| [`webserver.py`](webserver.py) | Web interface server (FastAPI + async WebSocket) |
| [`graph_parser.py`](graph_parser.py) | Core graph.log parser for web interface |
| [`web/src/App.vue`](web/src/App.vue) | Vue.js real-time web interface |
| [`axion_swarm/agents.py`](axion_swarm/agents.py) | Agent functions, message filtering, parallel execution |
| [`axion_swarm/graph.py`](axion_swarm/graph.py) | LangGraph workflow definition |
| [`axion_swarm/state.py`](axion_swarm/state.py) | State schema (TypedDict) |
| [`axion_swarm/prompts.py`](axion_swarm/prompts.py) | System prompts, role descriptions, base instructions |
| [`axion_swarm/config.py`](axion_swarm/config.py) | Provider configuration, model settings |
| [`axion_swarm/checkpoint.py`](axion_swarm/checkpoint.py) | Automatic state persistence and resume |
| [`axion_swarm/search.py`](axion_swarm/search.py) | Tavily search integration |
| [`axion_swarm/graph_tool.py`](axion_swarm/graph_tool.py) | Graph tool for collaborative decision trees |
| [`axion_swarm/colors.py`](axion_swarm/colors.py) | ANSI color utilities for console output |
| [`view_log.py`](view_log.py) / [`view_log.sh`](view_log.sh) | Log viewing utilities with ANSI color support |

### Key Architectural Patterns

**Multi-Agent Culture**: All agents operate under shared Operating Principles (DIGNITY, NON-HARM, CONSENT, TRANSPARENCY, CONTEXT, PURPOSE) while maintaining distinct specialist personas.

**Role Description System**: Dual perspective architecture with first-person (self-identity) and third-person (peer awareness) descriptions from a single maintainable data structure.

**Atomic Phases**: Specialists only see messages from **prior completed phases**, not current phase (prevents premature responses). Chair goes last and sees current phase for synthesis.

**Progressive Retraction**: As phases increase, specialists must be increasingly selective—passing when they have nothing new to add. Higher phase number = higher bar for contribution.

**Chair Phase Participation**: Chair participates in all phases with role-appropriate scope - Phase 1 (duplicate graph path marking only), Phase 2+ (full synthesis and coordination), Final Phase (primary comprehensive output).

---

## 🎯 Key Features in Detail

### 1. **Specialist Isolation & Fresh LLM Instances**
Each agent invocation creates a completely fresh LLM instance. No context leakage, no hidden state—only what's visible in the conversation transcript. ([Implementation](axion_swarm/agents.py#L1400-L1450))

### 2. **Explicit Audience Marking (Mandatory)**
Every piece of text must explicitly mark its intended audience using `@[All]` (everyone), `@[User]` (User), `@[Specialist name]` (specific specialist), or `@[Chair]` (Chair). Specialists can switch between audiences even sentence-by-sentence, creating 100% clarity on who should read each part. ([Documentation](ARCHITECTURE.md#L1310-L1415))

### 3. **XML Message Format**
Conversation history uses compact XML structure (`<message>`, `<from>`, `<timestamp_iso>`, `<phase>`, `<content>`) to help LLMs distinguish metadata from content. ([Implementation](axion_swarm/agents.py#L300-L600))

### 4. **History Compression**
After Phase 2, specialists see only Chair's comprehensive synthesis instead of all individual Phase 1-2 responses (configurable via `COMPRESS_HISTORY_AFTER_PHASE3`). Dramatically reduces context size while preserving key information. ([Documentation](ARCHITECTURE.md#L545-L575))

### 5. **Parallel Execution for Cloud APIs**
Azure OpenAI mode executes up to 15 specialists concurrently per phase (Chair sequential after all complete). Ollama mode enforces sequential execution (concurrency=1) to prevent VRAM thrashing. ([Implementation](axion_swarm/agents.py#L1700-L1900))

### 6. **Checkpoint System with Config Validation**
Automatic state persistence after each phase with SHA256 checksum of entire agent configuration. Checkpoints only load if they match current code (roster + prompts). ([Implementation](axion_swarm/checkpoint.py))

### 7. **Rate Limit Handling with Notice Messages**
Global coordination across parallel agents—when ANY agent hits rate limit, ALL agents pause. Adds Notice messages to conversation history documenting the break. ([Implementation](axion_swarm/agents.py#L45-L120))

### 8. **Tavily Search with Content Cleaning**
Real-time LLM-optimized search with automatic HTML entity decoding, Unicode normalization, and markdown/HTML removal. Results in clean XML with primary content (answer) in white, supporting evidence in light grey. ([Implementation](axion_swarm/search.py))

### 9. **Chair's Probabilistic Stagnation Detection**
In Phase 4+, Chair uses a multi-signal probability model (0.0-1.0) to detect discussion stagnation: user silence, phase progression, specialist activity, and conditional language push toward conclusion, while recent user engagement, research activity, and specialists providing answers justify continuation. Aggressive baseline convergence at Phase 8, but can extend to Phase 10+ when genuinely productive. Comprehensive DEBUG output on stderr shows state tracking, all signal computations with formulas, equation summation, weight configuration, and tuning guidance for data-driven iteration. ([Implementation](axion_swarm/agents.py#L1641-L2100))

### 10. **Think Tags for Transparent Reasoning**
Specialists use `<think>` tags for internal reasoning (visible to humans on stderr, never shared with other agents). Enables deep thinking without influencing others. ([Documentation](ARCHITECTURE.md#L1036-L1096))

---

## 🔧 Configuration

All configuration via environment variables or `.env` file:

```bash
# Provider
PROVIDER=azure_openai  # or "ollama"

# Core team (comma-separated specialist role keys)
CORE_TEAM=context,research,skeptic,ethicist

# Features
COMPRESS_HISTORY_AFTER_PHASE3=true  # History compression (default: true)
ENABLE_CHECKPOINTS=true  # Checkpoint system (default: true)
SHOW_MESSAGE_DEBUG=false  # Raw XML debug output (default: false)

# Tavily Search
TAVILY_API_KEY=your-key
TAVILY_MAX_RESULTS=5  # Results per query (max: 20)
```

See [`axion_swarm/config.py`](axion_swarm/config.py) for complete configuration options.

---

## 📖 Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Complete technical documentation (8,100+ lines)
  - Core architecture and design philosophy
  - Phase system with atomic filtering (including phase reset logic)
  - Message formats and filtering logic
  - Agent roster management
  - Parallel execution architecture
  - Checkpoint system with reordered flow
  - Search tool setup (Tavily API configuration)
  - **Interactive TUI mode** - Complete guide:
    - Automatic question blocking architecture
    - To-do sidebar with click-to-reply modals
    - Statistical auto-collapse (2σ threshold)
    - Keyboard shortcuts and navigation
    - Final Phase invalidation
    - Event handling and state management
    - TUI logging to discussion.log
  - Recent changes & bug fixes (message display, double phase starts, keybindings)

---

## 🎨 Output Streams

**STDOUT** (light green): Clean conversation log with timestamps
```
[2025-10-11 14:32:15.234 CDT] Notice: We are starting discussion phase 1...
[2025-10-11 14:32:20.123 CDT] Context specialist said: @[User], the concern here is...
```

**STDERR** (mixed colors): Debug information
- Yellow: Status messages, phase headers
- Dark green: Internal reasoning (`<think>` blocks)
- Red/Yellow: Message visibility debug (when `SHOW_MESSAGE_DEBUG=true`)

---

## 🤝 Contributing

This is a sophisticated multi-agent system with careful architectural considerations. Before contributing:

1. Read [ARCHITECTURE.md](ARCHITECTURE.md) thoroughly (especially "Recent Changes & Potential Bug Areas")
2. Understand the atomic phase architecture and message filtering logic
3. Respect the agent isolation principle (no shared context outside transcript)
4. Test with both Azure OpenAI (parallel) and Ollama (sequential) modes

---

## 📝 License

[View LICENSE](LICENSE)

---

## 🙏 Acknowledgments

Built with:
- [LangGraph](https://github.com/langchain-ai/langgraph) - State management and workflow orchestration
- [LangChain](https://github.com/langchain-ai/langchain) - LLM abstractions
- [Textual](https://github.com/Textualize/textual) - Terminal user interface framework
- [Tavily](https://tavily.com) - LLM-optimized search API
- [Ollama](https://ollama.ai) - Local LLM runtime
- [Azure OpenAI](https://azure.microsoft.com/en-us/products/ai-services/openai-service) - Hosted LLM service

---

**Axion Swarm** - Where specialized AI agents collaborate naturally to solve complex problems.

