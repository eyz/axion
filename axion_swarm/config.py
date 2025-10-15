"""Configuration for Ollama and Azure OpenAI providers.

USAGE:
======

To switch between providers, set the PROVIDER environment variable:

    # Use Azure OpenAI (default, parallel execution)
    export PROVIDER=azure_openai
    
    # Use local Ollama (sequential execution with concurrency=1)
    export PROVIDER=ollama

Azure OpenAI Configuration (environment variables):
---------------------------------------------------
    PROVIDER=azure_openai (default)
    AZURE_OPENAI_ENDPOINT=https://[your-resource-name].cognitiveservices.azure.com/
        (REQUIRED - from Azure Portal > Your OpenAI Resource > Keys and Endpoint)
    AZURE_OPENAI_API_KEY=[key-from-azure-portal]
        (REQUIRED - from Azure Portal > Your OpenAI Resource > Keys and Endpoint > KEY 1)
    AZURE_OPENAI_MODEL_AND_DEPLOYMENT=gpt-5-mini (default: "gpt-5-mini")
        (Sets both model_name and deployment - they must match)
        (Supports: "gpt-5-mini", "gpt-5-nano")
    AZURE_OPENAI_API_VERSION=2024-12-01-preview (default)
    AZURE_OPENAI_MAX_TOKENS=128000 (default: 128K, max output tokens)
    AZURE_OPENAI_REASONING_EFFORT=high (default: "high", values: "high"|"medium"|"low"|"minimal")
    
    IMPORTANT: AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY are REQUIRED when using
    Azure OpenAI provider. The application will raise an error if not provided.
    
    PHASE-SPECIFIC SETTINGS (automatic, overrides defaults for Phase 1-2):
        Phase 1: reasoning_effort="medium" (solid initial perspectives)
        Phase 2: reasoning_effort="medium" (thoughtful integration)
        Phase 3+: reasoning_effort="high" (full depth for sustained discussion)

Ollama Configuration (environment variables):
----------------------------------------------
    PROVIDER=ollama
    OLLAMA_BASE_URL=http://localhost:11434
    DEFAULT_MODEL=<model-name>
    OLLAMA_NUM_CTX=<context-window-size>

Shared Configuration (both providers):
--------------------------------------
    TEMPERATURE=0.6
    TOP_P=0.95
    TOP_K=20
    MIN_P=0.0
    COMPRESS_HISTORY_AFTER_PHASE3=true

Execution Behavior:
-------------------
- Azure OpenAI: Specialists execute in parallel per phase (Chair sequential)
- Ollama: All specialists execute sequentially (concurrency=1 to prevent VRAM thrashing)

See ARCHITECTURE.md section "Cloud Provider Parallelization" for details.
"""

import os
from dataclasses import dataclass
from typing import Tuple, Optional


# =============================================================================
# PROVIDER SELECTION
# =============================================================================
class ProviderType:
    """Available LLM provider types."""
    OLLAMA = "ollama"
    AZURE_OPENAI = "azure_openai"


# =============================================================================
# SPECIALIST ROOM PRESENCE - Core Team Configuration
# =============================================================================
# Specialists who start "in" the room (actively participating from the beginning)
# Chair is always present and not tracked in specialist_presence dict
# Other specialists are "available" and can be brought in by Chair when needed
DEFAULT_CORE_TEAM = [
    "context",
    "research",
    "skeptic",
    "ethicist",
]


def get_core_team() -> list[str]:
    """
    Get core team from config or environment variable.
    
    Environment variable format: CORE_TEAM=context,research,skeptic,ethicist
    
    Returns list of role_keys for specialists who start "in" the room.
    Chair is always present and not included in this list.
    """
    env_core = os.getenv("CORE_TEAM", "")
    if env_core:
        return [s.strip() for s in env_core.split(",")]
    return DEFAULT_CORE_TEAM


def initialize_specialist_presence() -> dict[str, str]:
    """
    Initialize specialist presence mapping for all non-Chair specialists.
    
    Returns dict like: {"context": "in", "research": "in", "cloud": "available", ...}
    
    Status values:
    - "in": Specialist is actively participating in phase rotations
    - "available": Specialist can be brought in by Chair when needed
    
    Chair is always present and not tracked in this dict.
    """
    from axion_swarm.agents import AGENT_ROSTER  # Import here to avoid circular dependency
    
    core_team = get_core_team()
    presence = {}
    
    for role in AGENT_ROSTER:
        if role == "chair":
            continue  # Chair always present, not tracked
        presence[role] = "in" if role in core_team else "available"
    
    return presence


def get_max_input_tokens(config: 'SwarmConfig') -> int:
    """Get maximum input tokens for the current provider.
    
    Args:
        config: SwarmConfig instance
        
    Returns:
        Maximum input tokens for the current provider
    """
    if config.provider == ProviderType.AZURE_OPENAI:
        # gpt-5-mini: 272,000 max input tokens
        return 272000
    else:
        # Ollama: use num_ctx from config (default to a conservative 128K if not set)
        if config.ollama_num_ctx:
            return config.ollama_num_ctx
        return 128000  # Conservative default


# =============================================================================
# OLLAMA MODEL + CONTEXT WINDOW COMBINATIONS
# =============================================================================
# Define model+context tuples here. Context window is optimized per quantization.
# Format: (model_name, context_window_tokens)

# Qwen3 30B A3B Thinking - Q4_K_M quantization
MODEL_QWEN3_30B_Q4_K_M = (
    "hf.co/bartowski/Qwen_Qwen3-30B-A3B-Thinking-2507-GGUF:Q4_K_M",
    50560  # fits in ~ 2 x 16GB VRAM on latest ollama
)

MODEL_QWEN3_30B_Q5_K_M = (
    "hf.co/bartowski/Qwen_Qwen3-30B-A3B-Thinking-2507-GGUF:Q5_K_M",
    36992
)

MODEL_QWEN3_30B_Q6_K = (
    "hf.co/bartowski/Qwen_Qwen3-30B-A3B-Thinking-2507-GGUF:Q6_K",
    22336
)

# -----------------------------------------------------------------------------
# SELECT DEFAULT OLLAMA MODEL HERE (only used when provider=ollama)
# -----------------------------------------------------------------------------
#DEFAULT_MODEL_TUPLE = MODEL_QWEN3_30B_Q4_K_M
DEFAULT_MODEL_TUPLE = MODEL_QWEN3_30B_Q5_K_M
#DEFAULT_MODEL_TUPLE = MODEL_QWEN3_30B_Q6_K
# -----------------------------------------------------------------------------

# =============================================================================


@dataclass
class AzureOpenAIConfig:
    """Configuration for Azure OpenAI provider.
    
    Supported models (set via AZURE_OPENAI_MODEL_AND_DEPLOYMENT):
    - gpt-5-mini: Standard GPT-5 model
    - gpt-5-nano: Faster, lighter GPT-5 model
    
    gpt-5-mini/nano specifications:
    - Total context window: 400,000 tokens
    - Max input tokens: 272,000 tokens
    - Max output tokens: 128,000 tokens
    - max_tokens parameter controls OUTPUT tokens only (completion/response length)
    
    IMPORTANT: gpt-5-mini/nano only support default sampling parameters:
    - temperature: 1.0 (default, not configurable)
    - top_p: default (not configurable)
    - Custom temperature/top_p values will cause 400 errors
    
    reasoning_effort parameter:
    - Controls depth of reasoning for GPT-5 models
    - Values: "minimal", "low", "medium", "high"
    - Default: "high"
    - "high" = deeper reasoning, more thinking time (recommended for complex tasks)
    - Phase-specific: Phase 1-2 use "medium", Phase 3+ uses "high"
    
    NOTE: model_name and deployment must be identical (set via single env var)
"""
    endpoint: str
    model_name: str
    deployment: str
    api_key: str
    api_version: str = "2024-12-01-preview"
    max_tokens: int = 128000  # Maximum OUTPUT tokens (set to model's max: 128K)
    reasoning_effort: str = "high"  # Request high reasoning effort for deeper analysis


@dataclass
class AgentConfig:
    """Configuration for a single agent (provider-agnostic)."""
    provider: str  # "ollama" or "azure_openai"
    
    # Sampling parameters (used by both providers)
    temperature: float = 0.6
    top_p: float = 0.95
    top_k: int = 20
    min_p: float = 0.0
    
    # Ollama-specific fields
    model: Optional[str] = None
    num_ctx: Optional[int] = None
    base_url: Optional[str] = None
    
    # Azure OpenAI-specific fields (shared config reference)
    azure_config: Optional[AzureOpenAIConfig] = None


class SwarmConfig:
    """Configuration for all agents in the swarm."""
    
    def __init__(self):
        """Initialize configuration from environment variables or defaults."""
        # =============================================================================
        # PROVIDER SELECTION - Choose between Ollama (local) or Azure OpenAI (hosted)
        # =============================================================================
        self.provider = os.getenv("PROVIDER", ProviderType.AZURE_OPENAI)  # Default: Azure OpenAI
        
        # =============================================================================
        # AZURE OPENAI CONFIGURATION (when provider=azure_openai)
        # =============================================================================
        # REQUIRED: Endpoint and API key MUST be provided via environment variables
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        
        # Validate required credentials when using Azure OpenAI
        if self.provider == ProviderType.AZURE_OPENAI:
            if not azure_endpoint:
                raise ValueError(
                    "AZURE_OPENAI_ENDPOINT environment variable is required when using Azure OpenAI provider.\n"
                    "Get your endpoint from: Azure Portal > Your OpenAI Resource > Keys and Endpoint\n"
                    "Format: https://[your-resource-name].cognitiveservices.azure.com/\n"
                    "Set it: export AZURE_OPENAI_ENDPOINT=https://[your-resource-name].cognitiveservices.azure.com/"
                )
            if not azure_api_key:
                raise ValueError(
                    "AZURE_OPENAI_API_KEY environment variable is required when using Azure OpenAI provider.\n"
                    "Get your key from: Azure Portal > Your OpenAI Resource > Keys and Endpoint > KEY 1\n"
                    "Set it: export AZURE_OPENAI_API_KEY=[your-key-from-azure-portal]"
                )
        
        # Use single env var for both model_name and deployment (they must match)
        model_and_deployment = os.getenv("AZURE_OPENAI_MODEL_AND_DEPLOYMENT", "gpt-5-mini")
        
        self.azure_config = AzureOpenAIConfig(
            endpoint=azure_endpoint or "",
            model_name=model_and_deployment,
            deployment=model_and_deployment,
            api_key=azure_api_key or "",
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
            max_tokens=int(os.getenv("AZURE_OPENAI_MAX_TOKENS", "128000")),
            reasoning_effort=os.getenv("AZURE_OPENAI_REASONING_EFFORT", "high")  # high|medium|low|minimal
        )
        
        # Parallelization settings
        # Azure OpenAI: Use parallel execution for specialists (Chair still sequential)
        # Ollama: Use concurrency=1 (sequential) to prevent VRAM thrashing
        self.parallel_execution = (self.provider == ProviderType.AZURE_OPENAI)
        self.max_concurrency = 1 if self.provider == ProviderType.OLLAMA else 15  # Max parallel specialists
        
        # =============================================================================
        # OLLAMA CONFIGURATION (when provider=ollama)
        # =============================================================================
        default_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        
        # Use the selected model tuple (defined at top of file)
        # Can be overridden with DEFAULT_MODEL and OLLAMA_NUM_CTX environment variables
        default_model_ctx: Tuple[str, int] = (
            os.getenv("DEFAULT_MODEL", DEFAULT_MODEL_TUPLE[0]),
            int(os.getenv("OLLAMA_NUM_CTX", str(DEFAULT_MODEL_TUPLE[1])))
        )
        
        # =============================================================================
        # SHARED CONFIGURATION (both providers)
        # =============================================================================
        # Sampling parameters (used by both Ollama and Azure OpenAI)
        default_temperature = float(os.getenv("TEMPERATURE", "0.6"))
        default_top_p = float(os.getenv("TOP_P", "0.95"))
        default_top_k = int(os.getenv("TOP_K", "20"))
        default_min_p = float(os.getenv("MIN_P", "0.0"))
        
        # History compression: After Phase 2, hide Phase 1 & 2 individual responses,
        # keeping only Chair's Phase 2 synthesis + Phase 3+ messages
        # This reduces context size while preserving key points via Chair's summary
        self.compress_history_after_phase3 = os.getenv("COMPRESS_HISTORY_AFTER_PHASE3", "true").lower() in ("true", "1", "yes")
        
        # Checkpoint: Save conversation state after each phase (enabled by default)
        # Allows resuming from where you left off if interrupted
        # Checkpoint file location: CHECKPOINT_FILE env var (default: .axion_checkpoint.json)
        self.enable_checkpoints = os.getenv("ENABLE_CHECKPOINTS", "true").lower() in ("true", "1", "yes")
        
        # Rate-limit-triggered compression: When hitting rate limits, have Chair compress
        # history to reduce context size and prevent cascading rate limit issues
        # Disabled by default (experimental feature)
        self.rate_limit_compression_enabled = os.getenv("RATE_LIMIT_COMPRESSION", "false").lower() in ("true", "1", "yes")
        self.rate_limit_compression_min_messages = int(os.getenv("RATE_LIMIT_COMPRESSION_MIN_MESSAGES", "10"))
        self.rate_limit_compression_min_tokens = int(os.getenv("RATE_LIMIT_COMPRESSION_MIN_TOKENS", "100000"))
        
        # Message visibility debug output: Show raw XML messages with VISIBLE/FILTERED indicators
        # Disabled by default (only shows per-agent thinking and normal stdout chat transcript)
        self.show_message_debug = os.getenv("SHOW_MESSAGE_DEBUG", "false").lower() in ("true", "1", "yes")
        
        # =============================================================================
        # TAVILY SEARCH API CONFIGURATION
        # =============================================================================
        # Specialists can use @[Search][query] to perform real-time LLM-optimized searches
        # Requires: Tavily API key
        # Setup: https://tavily.com (sign up for API key)
        # Tavily is a search API specifically designed for LLM applications
        self.tavily_api_key = os.getenv("TAVILY_API_KEY", "")
        self.tavily_search_enabled = bool(self.tavily_api_key)
        #self.tavily_max_results = int(os.getenv("TAVILY_MAX_RESULTS", "5"))
        self.tavily_max_results = int(os.getenv("TAVILY_MAX_RESULTS", "20"))
        # Note: Tavily provides LLM-optimized search results with citations
        
        # =============================================================================
        # JINA AI READER API CONFIGURATION
        # =============================================================================
        # Specialists can use @[ReadURL][url] to fetch full page content from URLs
        # Optional: Jina API key (provides higher rate limits, but works without it)
        # Setup: https://jina.ai/reader/ (sign up for API key)
        # Jina Reader extracts clean, LLM-friendly markdown from web pages
        self.jina_api_key = os.getenv("JINA_API_KEY", "")
        # Note: Works without API key (lower rate limits), but key recommended for production
        
        # =============================================================================
        # AGENT CONFIGURATION - All agents share the same provider configuration
        # =============================================================================
        # Helper function to create AgentConfig based on provider
        def create_agent_config(agent_name: str) -> AgentConfig:
            """Create AgentConfig for the specified agent based on provider."""
            if self.provider == ProviderType.AZURE_OPENAI:
                return AgentConfig(
                    provider=ProviderType.AZURE_OPENAI,
                    temperature=default_temperature,
                    top_p=default_top_p,
                    top_k=default_top_k,
                    min_p=default_min_p,
                    azure_config=self.azure_config
                )
            else:  # OLLAMA
                # Support per-agent model overrides via environment variables
                agent_env_name = agent_name.upper()
                return AgentConfig(
                    provider=ProviderType.OLLAMA,
                    model=os.getenv(f"{agent_env_name}_MODEL", default_model_ctx[0]),
                    num_ctx=int(os.getenv(f"{agent_env_name}_NUM_CTX", str(default_model_ctx[1]))),
                    temperature=default_temperature,
                    top_p=default_top_p,
                    top_k=default_top_k,
                    min_p=default_min_p,
                    base_url=default_base_url
                )
        
        # Create agent configurations
        self.chair = create_agent_config("chair")
        self.research = create_agent_config("research")
        self.engineer = create_agent_config("engineer")
        self.skeptic = create_agent_config("skeptic")
        self.context = create_agent_config("context")
        self.ethicist = create_agent_config("ethicist")
        self.azuredevopsengineer = create_agent_config("azuredevopsengineer")
        self.cloudarchitect = create_agent_config("cloudarchitect")
        self.dbarchitect = create_agent_config("dbarchitect")
        self.backendengineer = create_agent_config("backendengineer")
        self.frontendengineer = create_agent_config("frontendengineer")
        self.devopsengineer = create_agent_config("devopsengineer")
        self.productmanager = create_agent_config("productmanager")
        self.qaengineer = create_agent_config("qaengineer")
        self.technicalwriter = create_agent_config("technicalwriter")
        self.hr = create_agent_config("hr")
