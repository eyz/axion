# Axion Swarm 🤖

**Multi-Agent Discussion System with Natural Expert Collaboration**

Axion Swarm orchestrates conversations between specialized AI agents to provide comprehensive, well-reasoned answers to complex questions. Each agent brings domain expertise while maintaining complete isolation—thinking independently, building on each other's insights, and converging naturally through progressive discussion.

**What makes it different:** Specialists collaborate as an **internal expert team** while you're away, delivering well-reasoned synthesis in under a minute. You get the benefit of multiple expert perspectives debating, refining, and converging—without waiting hours for responses. Works equally well for real-time chat or async consultation across any domain.

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

### Real-Time Information with Search & URL Reading
Specialists can access current information through two complementary tools:
- **@[Search][query]** - Find relevant sources with Tavily Search API (snippets + AI synthesis)
- **@[ReadURL][url]** - Read full page content with Jina AI Reader (complete articles/docs)

**Two-Step Workflow**: Search first to find candidate URLs → ReadURL to fetch full content from promising sources. Results appear as tool messages with requester tracking. Research specialist explicitly acknowledges search/URL findings and integrates them into analysis.

### Intelligent Convergence
- **Progressive retraction**: Specialists increasingly likely to pass as phases progress
- **Probabilistic stagnation detection**: Chair uses multi-signal model (user engagement, phase count, specialist activity) to detect discussion plateau and trigger final phase automatically
- **Aggressive convergence with justification**: Discussions naturally conclude by Phase 8, but can extend when genuinely productive (active user + research + specialists providing answers)
- **Natural consensus**: System detects when all specialists pass (implicit agreement)

### Production-Ready Features
- **Interactive TUI Mode**: Real-time chat interface with automatic question blocking—specialists' @[User] questions pause phase progression until answered. Features collapsible messages (2σ auto-collapse), interactive to-do sidebar (F2), modal message view with reply/dismiss actions, and Final Phase invalidation
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

# Install dependencies
pip install -e .

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

---

## 📚 Architecture Overview

Axion Swarm uses LangGraph for state management and workflow orchestration. Specialists execute in phases, with Chair coordinating and synthesizing.

### Core Components

| File | Purpose |
|------|---------|
| [`main.py`](main.py) | Simple CLI mode entry point |
| [`main_tui.py`](main_tui.py) | Interactive TUI mode with Textual (1494 lines) |
| [`axion_swarm/agents.py`](axion_swarm/agents.py) | Agent functions, message filtering, parallel execution |
| [`axion_swarm/graph.py`](axion_swarm/graph.py) | LangGraph workflow definition |
| [`axion_swarm/state.py`](axion_swarm/state.py) | State schema (TypedDict) |
| [`axion_swarm/prompts.py`](axion_swarm/prompts.py) | System prompts, role descriptions, base instructions |
| [`axion_swarm/config.py`](axion_swarm/config.py) | Provider configuration, model settings |
| [`axion_swarm/checkpoint.py`](axion_swarm/checkpoint.py) | Automatic state persistence and resume |
| [`axion_swarm/search.py`](axion_swarm/search.py) | Tavily search integration |
| [`axion_swarm/colors.py`](axion_swarm/colors.py) | ANSI color utilities for console output |
| [`view_log.py`](view_log.py) / [`view_log.sh`](view_log.sh) | Log viewing utilities with ANSI color support |

### Key Architectural Patterns

**Multi-Agent Culture**: All agents operate under shared Operating Principles (DIGNITY, NON-HARM, CONSENT, TRANSPARENCY, CONTEXT, PURPOSE) while maintaining distinct specialist personas.

**Role Description System**: Dual perspective architecture with first-person (self-identity) and third-person (peer awareness) descriptions from a single maintainable data structure.

**Atomic Phases**: Specialists only see messages from **prior completed phases**, not current phase (prevents premature responses). Chair goes last and sees current phase for synthesis.

**Progressive Retraction**: As phases increase, specialists must be increasingly selective—passing when they have nothing new to add. Higher phase number = higher bar for contribution.

**Chair Conditional Participation**: Chair skips Phase 1 (no responses to synthesize yet), participates Phase 2+ (synthesizes cross-pollination), always participates in Final Phase (primary output).

---

## 🎯 Key Features in Detail

### 1. **Specialist Isolation & Fresh LLM Instances**
Each agent invocation creates a completely fresh LLM instance. No context leakage, no hidden state—only what's visible in the conversation transcript. ([Implementation](axion_swarm/agents.py#L1400-L1450))

### 2. **Explicit @Mention Addressing**
Specialists use `@[User]`, `@[Specialist name]`, or `@[All]` to explicitly address recipients, creating natural group chat dynamics with 100% clarity on audience. ([Documentation](ARCHITECTURE.md#L1310-L1415))

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

