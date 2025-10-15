"""Phase-based agent system with natural language chat."""

import re
import sys
import time
import json
import asyncio
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Union, List, Dict, Callable
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_ollama import ChatOllama
from langchain_openai import AzureChatOpenAI
from openai import RateLimitError, BadRequestError
import tiktoken

from .state import OverallState
from .config import SwarmConfig, AgentConfig, ProviderType
from .colors import dark_green, yellow, red, light_green, light_blue, cyan, white
from .search import (
    detect_search_requests, detect_readurl_requests,
    perform_tavily_search, read_url_with_jina,
    format_search_results, format_readurl_results
)
from .graph_tool import (
    detect_graph_requests, process_graph_operations,
    QuestionGraph
)
from .prompts import (
    CHAIR_SYSTEM,
    CHAIR_RATE_LIMIT_COMPRESSION_SYSTEM,
    CHAIR_DEDUPE_PASS_SYSTEM,
    RESEARCH_SYSTEM,
    ENGINEER_SYSTEM,
    SKEPTIC_SYSTEM,
    CONTEXT_SYSTEM,
    ETHICIST_SYSTEM,
    AZURE_DEVOPS_ENGINEER_SYSTEM,
    CLOUD_INFRASTRUCTURE_ARCHITECT_SYSTEM,
    DATABASE_ARCHITECT_SYSTEM,
    BACKEND_ENGINEER_SYSTEM,
    FRONTEND_ENGINEER_SYSTEM,
    DEVOPS_ENGINEER_SYSTEM,
    PRODUCT_MANAGER_SYSTEM,
    QA_ENGINEER_SYSTEM,
    TECHNICAL_WRITER_SYSTEM,
    HR_SYSTEM,
)


# =============================================================================
# GLOBAL RATE LIMIT TRACKING (for Azure OpenAI 429 errors)
# =============================================================================
# When ANY agent hits a rate limit, ALL agents must wait before retrying.
# This prevents parallel agents from all hitting rate limits simultaneously.
_rate_limit_lock = threading.Lock()
_rate_limit_until = 0.0  # Timestamp when rate limit expires
_rate_limit_hit_this_phase = False  # Track if rate limit was hit (for compression decision)
_rate_limit_break_notice_issued = False  # Track if "taking a break" notice already issued
_rate_limit_back_notice_issued = False  # Track if "we're back" notice already issued


def wait_if_rate_limited():
    """Check if we're currently rate limited and wait if necessary.
    
    This is called before every Azure OpenAI API call to ensure we respect
    the global rate limit across all parallel agents.
    
    Thread-safe: Reads global state inside lock, waits outside lock.
    """
    global _rate_limit_until
    
    # THREAD-SAFE: Read shared state inside lock
    with _rate_limit_lock:
        wait_until = _rate_limit_until  # Snapshot the value
        if wait_until > time.time():
            wait_seconds = wait_until - time.time()
            print(f"⏸️  Rate limit active. Waiting {wait_seconds:.1f} seconds before retry...", 
                  file=sys.stderr, flush=True)
    
    # Wait outside the lock so other threads can check too
    while time.time() < wait_until:
        time.sleep(0.5)


def set_rate_limit(duration_seconds: int):
    """Set global rate limit for the specified duration.
    
    Args:
        duration_seconds: How long to block all Azure OpenAI calls
    
    Thread-safe: All shared state modifications protected by lock.
    Multiple parallel agents may call this simultaneously - only the first
    one to acquire the lock will reset the notice flags.
    """
    global _rate_limit_until, _rate_limit_hit_this_phase, _rate_limit_break_notice_issued, _rate_limit_back_notice_issued
    
    # THREAD-SAFE: All reads/writes to shared state inside lock
    with _rate_limit_lock:
        # Check if we're already in a waiting state
        already_waiting = _rate_limit_until > time.time()
        
        _rate_limit_until = time.time() + duration_seconds
        _rate_limit_hit_this_phase = True  # Mark that rate limit occurred
        
        # Only reset notice flags if this is a NEW wait period (not already waiting)
        if not already_waiting:
            _rate_limit_break_notice_issued = False
            _rate_limit_back_notice_issued = False
        
        print(f"⚠️  Rate limit encountered. Blocking all Azure OpenAI calls for {duration_seconds} seconds.", 
              file=sys.stderr, flush=True)


def reset_rate_limit_flag():
    """Reset the rate limit hit flag (called at start of each phase).
    
    Thread-safe: All shared state modifications protected by lock.
    """
    global _rate_limit_hit_this_phase, _rate_limit_break_notice_issued, _rate_limit_back_notice_issued
    
    # THREAD-SAFE: All writes to shared state inside lock
    with _rate_limit_lock:
        _rate_limit_hit_this_phase = False
        _rate_limit_break_notice_issued = False
        _rate_limit_back_notice_issued = False


def was_rate_limit_hit():
    """Check if rate limit was hit during this phase."""
    with _rate_limit_lock:
        return _rate_limit_hit_this_phase


def should_compress_after_rate_limit(state: Dict) -> bool:
    """Decide if we should compress history after recovering from rate limit.
    
    Args:
        state: Current conversation state
    
    Returns:
        True if compression should be applied
    """
    config = get_config()
    
    # Feature disabled
    if not config.rate_limit_compression_enabled:
        return False
    
    # No rate limit hit this phase
    if not was_rate_limit_hit():
        return False
    
    # Only compress in Phase 3+
    # Phase 1-2: Chair's normal end-of-Phase-2 compression handles this already
    # Phase 3+: We're working with compressed history and may need additional compression
    phase_number = state.get("phase_number", 0)
    if phase_number < 3:
        print(f"[COMPRESSION] Skipping: Phase {phase_number} < 3 (Chair's Phase 2 compression handles Phase 1-2)",
              file=sys.stderr, flush=True)
        return False
    
    messages = state.get("messages", [])
    last_compression_idx = state.get("last_compression_message_index", -1)
    
    # Count messages since last compression
    messages_since_compression = len(messages) - last_compression_idx - 1
    
    # Not enough messages to warrant compression
    if messages_since_compression < config.rate_limit_compression_min_messages:
        print(f"[COMPRESSION] Skipping: only {messages_since_compression} messages since last compression (min: {config.rate_limit_compression_min_messages})", 
              file=sys.stderr, flush=True)
        return False
    
    # Estimate current context tokens (rough estimate: 4 chars per token)
    total_chars = sum(len(msg.content) for msg in messages if hasattr(msg, 'content'))
    estimated_tokens = total_chars // 4
    
    # Context not large enough
    if estimated_tokens < config.rate_limit_compression_min_tokens:
        print(f"[COMPRESSION] Skipping: only ~{estimated_tokens} tokens (min: {config.rate_limit_compression_min_tokens})",
              file=sys.stderr, flush=True)
        return False
    
    # Check if Chair just spoke (last 5 messages)
    recent_messages = messages[-5:] if len(messages) >= 5 else messages
    chair_just_spoke = any(
        hasattr(msg, 'name') and msg.name == "Chair"
        for msg in recent_messages
    )
    
    if chair_just_spoke:
        print(f"[COMPRESSION] Skipping: Chair spoke recently",
              file=sys.stderr, flush=True)
        return False
    
    print(f"[COMPRESSION] Applying: {messages_since_compression} messages, ~{estimated_tokens} tokens",
          file=sys.stderr, flush=True)
    return True


def log_denied_request(agent_name: str, messages: List[BaseMessage], error: BadRequestError):
    """Log denied LLM requests to 400s.log for analysis.
    
    When OpenAI returns a 400 error (BadRequestError), it's often due to content policy
    violations or prompt refusal. This function appends the full context to 400s.log.
    
    Args:
        agent_name: Name of the agent/specialist that made the request
        messages: Complete message history that was sent to the LLM
        error: The BadRequestError exception from OpenAI
    """
    try:
        log_path = Path("400s.log")
        timestamp = datetime.now().isoformat()
        
        # Format the messages for logging
        formatted_messages = []
        for msg in messages:
            msg_dict = {
                "role": getattr(msg, "name", msg.__class__.__name__),
                "content": msg.content if hasattr(msg, "content") else str(msg)
            }
            if hasattr(msg, "additional_kwargs") and msg.additional_kwargs:
                msg_dict["metadata"] = msg.additional_kwargs
            formatted_messages.append(msg_dict)
        
        # Create log entry with full request and response details
        log_entry = {
            "timestamp": timestamp,
            "agent": agent_name,
            "error": str(error),
            "error_type": error.__class__.__name__,
            "status_code": getattr(error, "status_code", 400),
            "response": {
                "body": getattr(error, "body", None),
                "response": getattr(error, "response", None)
            },
            "messages": formatted_messages,
            "message_count": len(messages),
            "total_chars": sum(len(msg.content) for msg in messages if hasattr(msg, "content"))
        }
        
        # Append to 400s.log
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(json.dumps(log_entry, indent=2, ensure_ascii=False))
            f.write("\n" + "=" * 80 + "\n\n")
        
        print(f"⚠️  Logged 400 response to 400s.log (agent: {agent_name})", 
              file=sys.stderr, flush=True)
    
    except Exception as log_error:
        # Don't let logging errors crash the system
        print(f"⚠️  Failed to log 400 response: {log_error}", 
              file=sys.stderr, flush=True)


# Agent roster - canonical execution order
# Chair always goes LAST to synthesize all other contributions
#
# ROSTER COMPOSITION:
# - Core team (context, research, engineer, skeptic, ethicist): Domain-agnostic, work for any field
# - Non-core specialists (azuredevopsengineer, cloudarchitect, etc.): Domain-specific, configured per use case
# - Current non-core technical specialists are FOR TEST CASE ONLY (platform engineering domain)
# - In real use, replace non-core specialists with domain-appropriate roles:
#   Legal: legalresearch, compliance, contractanalysis
#   Medical: clinical, researchspecialist, bioethics
#   Business: marketanalysis, finance, operations
# - Chair always goes LAST to synthesize all contributions
AGENT_ROSTER = [
    "context",
    "research", 
    "engineer",
    "skeptic",
    "ethicist",
    "azuredevopsengineer",
    "cloudarchitect",
    "dbarchitect",
    "backendengineer",
    "frontendengineer",
    "devopsengineer",
    "productmanager",
    "qaengineer",
    "technicalwriter",
    "hr",
    "chair"
]

# Synthesis specialists - These specialists see current phase messages (not just prior phases)
# because their role is to consolidate/synthesize what was said in the current phase
# - Chair: Synthesizes all specialist contributions
# (Future: additional synthesis specialists can be added for specific consolidation roles)
SYNTHESIS_SPECIALISTS = [
    "Chair",
]


# =============================================================================
# SEARCH RESULT CLEANUP HELPERS
# =============================================================================

def cleanup_old_search_results(content: str) -> str:
    """Remove verbose tags from old search and ReadURL results to save tokens.
    
    For SEARCH results:
    - Keeps the <results> wrapper with query, requester, and <answer>
    - Removes individual <result> tags which contain detailed URL/title/content
    - Also removes any 'count' attribute for consistency with new search format
    
    For READURL results:
    - Keeps the <content> element with url, title, requester attributes
    - Removes the inner markdown content (can be 1000s of words)
    - Replaces with ellipsis (…) to indicate content was elided
    
    This function is applied to tool results that are 2+ phases old.
    Specialists get ONE full phase to work with detailed results
    before they are compressed. For example:
    - Phase 3: Tool created with full content
    - Phase 4: Specialists see full results (can respond/use them)
    - Phase 5+: Results are trimmed to save tokens
    
    This allows specialists to see that a tool was already used
    (preventing duplicate requests) while dramatically reducing token usage
    from historical results.
    
    Example transformations:
    
    SEARCH:
        <results query="..." requester="@[Research specialist]">
            <answer>synthesis</answer>
            <result url="..." title="...">content1</result>
            <result url="..." title="...">content2</result>
        </results>
        
        Becomes:
        
        <results query="..." requester="@[Research specialist]">
            <answer>synthesis</answer>
            …
        </results>
    
    READURL:
        <content url="..." title="..." requester="...">
        Full markdown content (1000s of words)...
        </content>
        
        Becomes:
        
        <content url="..." title="..." requester="...">…</content>
    
    Args:
        content: Message content that may contain search or ReadURL results
        
    Returns:
        Content with <result> and <content> tags removed from old tool results (3+ phases old)
    """
    # Pattern to match <results>...</results> blocks
    # Use non-greedy matching and handle multiline
    def cleanup_results_block(match):
        full_block = match.group(0)
        
        # If it already has count attribute and no <result> tags, it's already clean
        if 'count="' in full_block and '<result' not in full_block:
            return full_block
        
        # Extract the opening <results ...> tag
        opening_match = re.match(r'<results[^>]*>', full_block)
        if not opening_match:
            return full_block
        
        opening_tag = opening_match.group(0)
        
        # Extract <answer> tag if present
        answer_match = re.search(r'<answer>.*?</answer>', full_block, re.DOTALL)
        answer_tag = answer_match.group(0) if answer_match else ""
        
        # Count <result> tags to determine if we need the ellipsis
        result_count = len(re.findall(r'<result[^>]*>.*?</result>', full_block, re.DOTALL))
        
        # Remove count attribute if it exists (for consistency with new search format)
        opening_tag = re.sub(r'\s+count="[^"]*"', '', opening_tag)
        
        # Add visual indicator that detailed results were elided (removed to save tokens)
        # Use unicode horizontal ellipsis (…) as a simple, clean hint
        elided_hint = ""
        if result_count > 0:
            elided_hint = "…"
        
        # Rebuild: <results ...><answer>...</answer>…</results>
        return f"{opening_tag}{answer_tag}{elided_hint}</results>"
    
    # Match <results>...</results> blocks (non-greedy, multiline)
    content = re.sub(
        r'<results[^>]*>.*?</results>',
        cleanup_results_block,
        content,
        flags=re.DOTALL
    )
    
    # Pattern to match <content>...</content> blocks (for ReadURL results)
    def cleanup_content_block(full_block):
        """Trim ReadURL content blocks, replacing body with ellipsis (…).
        
        CRITICAL: Only trim if content is NOT already just the ellipsis marker.
        This prevents re-trimming already trimmed content, which would cause:
        - False positives in trimming detection (thinking '…' in actual web content means already trimmed)
        - Repeated debug logs for the same messages
        
        Note: We check if inner_content == '…' (exactly the ellipsis), NOT if '…' is
        anywhere in the content. This allows web content that happens to contain '…'
        to be trimmed correctly, while still preventing re-trimming of already-trimmed content.
        
        Args:
            full_block: String containing the <content>...</content> block
            
        Returns:
            Trimmed content block string with body replaced by ellipsis
        """
        # Extract the opening <content ...> tag
        opening_match = re.match(r'<content[^>]*>', full_block)
        if not opening_match:
            return full_block
        
        opening_tag = opening_match.group(0)
        
        # Extract content between tags
        content_match = re.search(r'<content[^>]*>(.*?)</content>', full_block, re.DOTALL)
        if not content_match:
            return full_block
        
        inner_content = content_match.group(1).strip()
        
        # If content is ONLY the ellipsis, it's already trimmed - don't trim again
        if inner_content == '…':
            return full_block
        
        # If there's actual content (not just ellipsis), trim it
        # Replace with ellipsis to indicate content was elided
        return f"{opening_tag}…</content>"
    
    # Match <content>...</content> blocks (non-greedy, multiline)
    # Only match within "URL content: " context to avoid matching unrelated content tags
    content = re.sub(
        r'URL content: <content[^>]*>.*?</content>',
        lambda m: 'URL content: ' + cleanup_content_block(m.group(0).replace('URL content: ', '')),
        content,
        flags=re.DOTALL
    )
    
    return content


# =============================================================================
# SPECIALIST ROOM PRESENCE HELPERS
# =============================================================================

def get_active_specialists(state: OverallState) -> list[str]:
    """
    Return list of specialists currently 'in' the room (participating in phases).
    Maintains AGENT_ROSTER order.
    
    Args:
        state: Current conversation state
        
    Returns:
        List of role_keys for specialists with status="in", in AGENT_ROSTER order.
        Chair is excluded (handled separately with conditional participation logic).
    """
    presence = state.get("specialist_presence", {})
    active = []
    
    for role in AGENT_ROSTER:
        if role == "chair":
            continue  # Chair handled separately (conditional participation)
        if presence.get(role) == "in":
            active.append(role)
    
    return active


def get_available_specialists(state: OverallState) -> list[str]:
    """
    Return list of specialists currently 'available' (can be brought in).
    
    Args:
        state: Current conversation state
        
    Returns:
        List of role_keys for specialists with status="available".
    """
    presence = state.get("specialist_presence", {})
    available = []
    
    for role in AGENT_ROSTER:
        if role == "chair":
            continue  # Chair always present, not tracked
        if presence.get(role) == "available":
            available.append(role)
    
    return available


def auto_dismiss_non_core_specialists(
    specialist_messages: list[BaseMessage],
    state: OverallState,
    chair_messages: list[BaseMessage] = None
) -> tuple[dict[str, str] | None, list[AIMessage]]:
    """
    Auto-dismiss non-core team specialists after they respond.
    
    Non-core specialists who responded in this phase are automatically changed
    to "available" status UNLESS they were mentioned (via @[Name]) in the current
    phase, keeping the discussion focused on the core team. They can be brought
    back in if needed.
    
    Args:
        specialist_messages: Messages from specialists in current phase (before Chair)
        state: Current conversation state
        chair_messages: Optional Chair messages from current phase (to check for mentions)
        
    Returns:
        Tuple of:
        - Updated specialist_presence dict (or None if no changes)
        - List of Notice messages for dismissed specialists
    """
    from axion_swarm.config import get_core_team
    
    core_team = get_core_team()
    current_presence = state.get("specialist_presence", {})
    
    # Collect all messages from current phase to check for mentions
    all_phase_messages = list(specialist_messages)
    if chair_messages:
        all_phase_messages.extend(chair_messages)
    
    # Find specialists who were mentioned in this phase
    mentioned_specialists = set()
    for msg in all_phase_messages:
        content = getattr(msg, 'content', '')
        # Find all @[...] mentions
        mentions = re.findall(r'@\[([^\]]+)\]', content)
        for mention in mentions:
            # Map display name to role key
            role_key = find_role_key_by_display_name(mention)
            if role_key:
                mentioned_specialists.add(role_key)
    
    # Find specialists who responded in this phase (exclude Chair)
    responded_specialists = set()
    for msg in specialist_messages:
        # Get the specialist name from the message
        specialist_name = getattr(msg, 'name', None)
        if specialist_name and specialist_name != "Chair":
            # Map display name back to role key
            for role_key in AGENT_ROSTER:
                if role_key == "chair":
                    continue
                if get_display_name(role_key) == specialist_name:
                    responded_specialists.add(role_key)
                    break
    
    # Identify non-core specialists who responded and are currently "in"
    # BUT exclude those who were mentioned (they should stay to respond)
    to_dismiss = []
    for role_key in responded_specialists:
        if role_key not in core_team and current_presence.get(role_key) == "in":
            # Don't dismiss if they were mentioned in this phase
            if role_key not in mentioned_specialists:
                to_dismiss.append(role_key)
    
    if not to_dismiss:
        return None, []
    
    # Update presence
    updated_presence = current_presence.copy()
    for role_key in to_dismiss:
        updated_presence[role_key] = "available"
    
    # Create Notice messages
    notice_messages = []
    dismissed_names = [get_display_name(role) for role in to_dismiss]
    
    phase_num = state.get("phase_number", 1)
    
    if len(dismissed_names) == 1:
        notice_content = f"Notice: {dismissed_names[0]} has self-dismissed from the discussion and is now available to be brought back in if needed."
    else:
        notice_content = f"Notice: {', '.join(dismissed_names)} have self-dismissed from the discussion and are now available to be brought back in if needed."
    
    notice_msg = AIMessage(
        content=notice_content,
        name="Notice",
        additional_kwargs={"phase": phase_num}
    )
    notice_messages.append(notice_msg)
    
    return updated_presence, notice_messages


def get_display_name(role_key: str) -> str:
    """
    Get display name for a specialist role key.
    
    Args:
        role_key: Role key like "context", "cloudarchitect", etc.
        
    Returns:
        Display name like "Context specialist", "Cloud Infrastructure specialist", etc.
    """
    # Map role keys to display names
    display_names = {
        "context": "Context specialist",
        "research": "Research specialist",
        "engineer": "Engineer specialist",
        "skeptic": "Skeptic specialist",
        "ethicist": "Ethicist specialist",
        "azuredevopsengineer": "Azure DevOps Engineer specialist",
        "cloudarchitect": "Cloud Infrastructure specialist",
        "dbarchitect": "Database Architect specialist",
        "backendengineer": "Backend Engineer specialist",
        "frontendengineer": "Frontend Engineer specialist",
        "devopsengineer": "DevOps Engineer specialist",
        "productmanager": "Product Manager specialist",
        "qaengineer": "QA Engineer specialist",
        "technicalwriter": "Technical Writer specialist",
        "hr": "HR specialist",
        "chair": "Chair",
    }
    return display_names.get(role_key, f"{role_key} specialist")


def format_name_list(names: list[str]) -> str:
    """Format a list of names with proper English grammar (Oxford comma).
    
    Examples:
        ["Alice"] -> "Alice"
        ["Alice", "Bob"] -> "Alice and Bob"
        ["Alice", "Bob", "Charlie"] -> "Alice, Bob, and Charlie"
    """
    if len(names) == 0:
        return ""
    elif len(names) == 1:
        return names[0]
    elif len(names) == 2:
        return f"{names[0]} and {names[1]}"
    else:
        return ", ".join(names[:-1]) + f", and {names[-1]}"


def find_role_key_by_display_name(display_name: str) -> str | None:
    """
    Map display name like 'Cloud Infrastructure specialist' to role_key like 'cloudarchitect'.
    
    Args:
        display_name: Display name (e.g., "Cloud Infrastructure specialist")
        
    Returns:
        Role key (e.g., "cloudarchitect") or None if not found.
    """
    # Normalize: remove "specialist" suffix, lowercase, strip
    normalized = display_name.lower().replace("specialist", "").strip()
    
    # Check AGENT_ROSTER for matches
    for role_key in AGENT_ROSTER:
        role_display = get_display_name(role_key).lower().replace("specialist", "").strip()
        if normalized == role_display:
            return role_key
    
    return None


def detect_specialist_additions(chair_response: str, state: OverallState) -> tuple[list[str], list[AIMessage]]:
    """
    Detect when Chair brings specialists into the room.
    
    Chair brings specialists in simply by @mentioning them.
    Any @mention of an available specialist automatically brings them into the room for the next phase.
    
    Args:
        chair_response: Chair's text response
        state: Current conversation state
        
    Returns:
        Tuple of:
        - List of role_keys brought in (e.g., ["cloudarchitect", "dbarchitect"])
        - List of Notice messages to add to conversation history
    """
    added_specialists = []
    
    # Find all @mentions in Chair's response
    all_mentions = re.findall(r"@\[([^\]]+)\]", chair_response)
    
    for mention in all_mentions:
        role_key = find_role_key_by_display_name(mention)
        
        if not role_key or role_key == "chair":
            continue  # Skip invalid names and Chair
        
        current_status = state["specialist_presence"].get(role_key)
        
        # If Chair mentions an available specialist, bring them in
        if current_status == "available" and role_key not in added_specialists:
            added_specialists.append(role_key)
    
    notice_messages = []
    
    # Create Notice message if any specialists were added
    if added_specialists:
        # Get current room composition (before adding new specialists)
        active_specialists = get_active_specialists(state)
        # Add newly brought-in specialists
        updated_active = active_specialists + added_specialists
        
        # Create Notice
        specialist_names = [get_display_name(role) for role in added_specialists]
        room_composition = [get_display_name(role) for role in updated_active]
        
        if len(specialist_names) == 1:
            notice_content = f"Notice: {specialist_names[0]} has been brought in and will participate starting next phase. Current team: {', '.join(room_composition)}"
        else:
            notice_content = f"Notice: {', '.join(specialist_names)} have been brought in and will participate starting next phase. Current team: {', '.join(room_composition)}"
        
        notice_msg = AIMessage(
            content=notice_content,
            name="Notice",
            additional_kwargs={
                "phase": state["phase_number"],
                "timestamp": datetime.now().astimezone().isoformat(timespec='milliseconds')
            }
        )
        notice_messages.append(notice_msg)
    
    return added_specialists, notice_messages


# Global config
_config = None

# Global tokenizer for accurate token counting
# Using cl100k_base (GPT-3.5/4 encoding) as a general-purpose tokenizer
try:
    _tokenizer = tiktoken.get_encoding("cl100k_base")
except Exception:
    # Fallback to None if tiktoken fails to load
    _tokenizer = None

# Global lock for console output to prevent interleaving when running parallel agents
# Critical for parallel Azure OpenAI execution - ensures each agent's complete output
# (stderr debug info + stdout message) prints atomically without interruption
_console_output_lock = threading.Lock()


def get_config() -> SwarmConfig:
    """Get or create config."""
    global _config
    if _config is None:
        _config = SwarmConfig()
    return _config


def get_phase_specific_settings(phase_number: int, azure_config) -> dict:
    """Get phase-specific reasoning effort settings.
    
    Phase 1: Medium effort (solid initial perspectives)
    Phase 2: Medium effort (thoughtful integration of multiple perspectives)
    Phase 3+: High effort (full depth for sustained discussion)
    
    Args:
        phase_number: Current phase number
        azure_config: Base Azure config with default settings
        
    Returns:
        Dict with reasoning_effort for the phase
    """
    if phase_number == 1:
        return {
            "reasoning_effort": "medium"
        }
    elif phase_number == 2:
        return {
            "reasoning_effort": "medium"
        }
    else:  # Phase 3+
        return {
            "reasoning_effort": azure_config.reasoning_effort  # Default: "high"
        }


def get_llm(agent_name: str, agent_config: AgentConfig, phase_number: int = None) -> Union[ChatOllama, AzureChatOpenAI]:
    """Create a fresh LLM instance for each agent invocation to ensure complete isolation.
    
    Returns either ChatOllama (for local models) or AzureChatOpenAI (for hosted Azure OpenAI),
    depending on the provider configuration.
    
    Args:
        agent_name: Name of the agent
        agent_config: Configuration for the agent
        phase_number: Current phase number for phase-specific settings (Azure OpenAI only)
    """
    # ALWAYS create a fresh instance to ensure no context leakage between calls
    # Each invocation gets a completely independent LLM instance
    
    if agent_config.provider == ProviderType.AZURE_OPENAI:
        # Azure OpenAI configuration
        if agent_config.azure_config is None:
            raise ValueError(f"Agent {agent_name}: azure_config is required when provider is azure_openai")
        
        azure_config = agent_config.azure_config
        
        # Get phase-specific settings if phase_number provided
        if phase_number is not None:
            phase_settings = get_phase_specific_settings(phase_number, azure_config)
            reasoning_effort = phase_settings["reasoning_effort"]
        else:
            # Use defaults from config
            reasoning_effort = azure_config.reasoning_effort
        
        # Note: GPT-5 models (gpt-5-mini, gpt-5-nano) only support default temperature (1.0)
        # Do NOT pass temperature, top_p, or other sampling parameters
        # However, reasoning_effort IS supported to control reasoning depth
        llm = AzureChatOpenAI(
            azure_endpoint=azure_config.endpoint,
            azure_deployment=azure_config.deployment,
            api_key=azure_config.api_key,
            api_version=azure_config.api_version,
            max_tokens=azure_config.max_tokens,
            reasoning_effort=reasoning_effort,
            # Do NOT set temperature, top_p, top_k, min_p for GPT-5 models
            # These models only support default values
        )
        
        return llm
    
    else:  # OLLAMA
        # Build kwargs for ChatOllama
        kwargs = {
            "model": agent_config.model,
            "temperature": agent_config.temperature,
            "top_p": agent_config.top_p,
            "top_k": agent_config.top_k,
            "base_url": agent_config.base_url,
            "num_ctx": agent_config.num_ctx,
        }
        
        # Add min_p if supported (newer Ollama versions support this directly)
        # If not supported, Ollama will ignore unknown parameters
        if agent_config.min_p is not None:
            kwargs["min_p"] = agent_config.min_p
        
        llm = ChatOllama(**kwargs)
        
        return llm


def elide_xml_content(xml_msg: str) -> str:
    """Elide the content within <content>…</content> tags for cleaner debug output."""
    return re.sub(r'<content>.*?</content>', '<content>…</content>', xml_msg, flags=re.DOTALL)


def count_tokens_in_messages(messages: list) -> int:
    """Count tokens in a list of messages using tiktoken.
    
    Args:
        messages: List of LangChain messages (SystemMessage, HumanMessage, AIMessage)
        
    Returns:
        Token count, or character-based approximation if tiktoken unavailable
    """
    if _tokenizer is None:
        # Fallback to character-based approximation
        total_chars = sum(len(str(msg.content)) for msg in messages)
        return total_chars // 4
    
    # Count tokens accurately using tiktoken
    total_tokens = 0
    for msg in messages:
        content = str(msg.content)
        total_tokens += len(_tokenizer.encode(content))
    
    return total_tokens


def build_active_graph_context() -> str:
    """Build compact list of active graph paths for specialist context.
    
    Shows non-dismissed, non-duplicate paths so specialists can:
    - Vote with @[Graph][Update][exact path][👍/👎][comment]
    - Extend with @[Graph][Create][existing path][Q:type][new nested question]
    - Build upon with @[Graph][Create][existing path][A][new answer]
    
    Returns empty string if no active paths exist.
    """
    from pathlib import Path
    
    if not Path('graph.log').exists():
        return ""
    
    try:
        # Parse graph.log to get all paths
        from graph_parser import analyze_graph_log
        nodes, vote_tally, specialist_stats = analyze_graph_log('graph.log')
        
        # Filter to active paths only (not dismissed, not duplicates)
        active_paths = []
        for path, node in nodes.items():
            # Skip if dismissed (any ❌ or X vote)
            has_dismiss = any(v.get('vote') in ['❌', 'X'] for v in node.get('votes', []))
            if has_dismiss:
                continue
            
            # Skip if marked duplicate by Chair
            has_duplicate = any(
                v.get('vote') == '🧹' and v.get('specialist') == 'Chair' 
                for v in node.get('votes', [])
            )
            if has_duplicate:
                continue
            
            active_paths.append(path)
        
        if not active_paths:
            return ""
        
        # Build compact hierarchical list
        lines = ["\n" + "="*80]
        lines.append("ACTIVE GRAPH PATHS:")
        lines.append("="*80)
        lines.append("")
        lines.append("These are the current active paths in the collaborative graph.")
        lines.append("Use these to:")
        lines.append("  • Vote with @[Graph][Update][exact path][👍/👎][comment]")
        lines.append("  • Extend with @[Graph][Create][existing path][Q:type][new nested question]")
        lines.append("  • Build upon with @[Graph][Create][existing path][A][new answer]")
        lines.append("")
        lines.append("Copy exact paths - do not paraphrase or invent new question titles.")
        lines.append("")
        
        # Group by root question
        root_questions = [p for p in active_paths if p.count('[Q:') == 1 and p.endswith(']')]
        
        for root_q in sorted(root_questions):
            lines.append(f"• {root_q}")
            
            # Find direct answers under this question
            q_prefix = root_q + '[A'
            answers = [p for p in active_paths if p.startswith(q_prefix) and p.count('[Q:') == 1]
            for answer in sorted(answers):
                answer_text = answer.replace(root_q, '')
                # Truncate long answers
                if len(answer_text) > 100:
                    answer_text = answer_text[:97] + '...'
                lines.append(f"  - {answer_text}")
                
                # Find nested questions under this answer (limit to keep compact)
                nested_qs = [p for p in active_paths if p.startswith(answer + '[Q:') and p.count('[Q:') == 2]
                for nested_q in sorted(nested_qs)[:2]:  # Limit to 2 nested per answer
                    nested_text = nested_q.replace(answer, '')
                    if len(nested_text) > 80:
                        nested_text = nested_text[:77] + '...'
                    lines.append(f"    └─ {nested_text}")
        
        lines.append("")
        lines.append("Dismissed (❌) and duplicate (🧹) paths are hidden - these are active paths only.")
        lines.append("="*80 + "\n")
        
        return '\n'.join(lines)
        
    except Exception as e:
        # If graph parsing fails, return empty string (don't break agent execution)
        print(f"Warning: Could not build graph context: {e}", file=sys.stderr)
        return ""


def create_agent_func(name: str, system_prompt: str, agent_config: AgentConfig, specialist_count: int = None):
    """Create an agent that participates in phases.
    
    Args:
        name: Agent name
        system_prompt: System prompt for the agent
        agent_config: Agent configuration
        specialist_count: Optional - for Chair only, number of specialist responses to synthesize
    """
    def agent(state: OverallState) -> dict:
        # Declare global variables for rate limit tracking (must be at function level)
        global _rate_limit_break_notice_issued, _rate_limit_back_notice_issued, _rate_limit_until
        
        # Get global config for system-wide settings
        config = get_config()
        
        # Get current phase number for phase-specific settings
        current_phase = state.get("phase_number", 1)
        
        # Create a fresh LLM instance for this invocation (complete isolation, no context sharing)
        # Pass phase_number for phase-specific reasoning effort and text verbosity
        llm = get_llm(name, agent_config, phase_number=current_phase)
        
        # Check if this is the final phase - use different system prompt
        # BUG FIX: Check BOTH final_phase_needed (for upcoming final) AND final_phase_done (for current final)
        # This ensures specialists recognize they're IN the final phase even before Chair runs
        is_final = state.get("final_phase_needed", False) or state.get("final_phase_done", False)
        
        if is_final:
            # Extract just the role description (without BASE_INSTRUCTION rules)
            # The system_prompt is "role_specific_prompt + BASE_INSTRUCTION"
            # For final phase, we want ONLY the role description, no iteration rules
            role_lines = system_prompt.split('\n')
            # Find where the role-specific content starts - look for "You are [Name]"
            role_description = ""
            for i, line in enumerate(role_lines):
                if 'You are' in line and (name in line or name.lower() in line.lower()):
                    # Find where BASE_INSTRUCTION starts (usually after the role description)
                    # BASE_INSTRUCTION starts with "CRITICAL RULES:"
                    role_end = len(role_lines)
                    for j in range(i, len(role_lines)):
                        if 'CRITICAL RULES:' in role_lines[j] or 'BASE_INSTRUCTION' in role_lines[j]:
                            role_end = j
                            break
                    role_description = '\n'.join(role_lines[i:role_end])
                    break
            
            # If extraction failed, use a simple default
            if not role_description:
                role_description = f"You are a {name} specialist."
            
            # Special prompt for Chair in final phase
            if name == "Chair":
                final_system_prompt = f"""{role_description}

YOUR IDENTITY:
You are Chair - coordinator who speaks LAST after all other specialists.

CRITICAL - FINAL PHASE SUMMARY:
This is the FINAL PHASE. Your response is the PRIMARY OUTPUT of this discussion for the User.
You must provide a COMPLETE but CONCISE synthesis of the entire discussion covering all key points.

Your response must include:
- Synthesis of ALL key points made by specialists throughout the discussion (briefly stated)
- Summary of ALL important questions raised (including any questions to the User)
- Areas of agreement among specialists
- Areas of disagreement or different perspectives
- Practical recommendations or next steps
- Any critical concerns or risks identified

CHAT SESSION FORMAT:
The chat session history shows messages in compact XML format:
<message><from>User</from><timestamp_iso>YYYY-MM-DDTHH:MM:SS.mmm</timestamp_iso><phase>1</phase><content>Message content</content></message>

YOUR RESPONSE:
- Respond naturally with just your content (the system wraps it in XML automatically)
- Do NOT include timestamps, speaker labels, or XML tags - just provide the raw text
- You MUST contribute - passing is forbidden in the final phase

Use <think> tags to review the full discussion and organize your comprehensive summary.
Write naturally - newlines are allowed. The XML <content> tag handles them properly (human console will show as single line).
"""
            else:
                final_system_prompt = f"""{role_description}

YOUR IDENTITY:
You are {name} specialist in a panel of specialists assisting a User.

CHAT SESSION FORMAT:
The chat session history shows messages in compact XML format:
<message><from>User</from><timestamp_iso>YYYY-MM-DDTHH:MM:SS.mmm</timestamp_iso><phase>1</phase><content>Message content</content></message>

YOUR RESPONSE:
- Respond naturally with just your content
- The system automatically wraps your response in XML format
- Do NOT include timestamps, speaker labels, or XML tags - just provide the raw text

ASKING QUESTIONS:
- You CAN ask clarifying questions to the User in your response
- Do NOT wait for User responses - provide your best assessment with available information
- If the User has provided additional information during the discussion, incorporate it

FINAL ASSESSMENT PHASE:
Provide your final assessment to help the User after reviewing the full discussion.
Your own previous contributions (messages from "{name} specialist said:") are hidden - you're seeing only what others said.

Use <think> tags for reasoning. Write naturally - newlines are allowed (XML <content> preserves them; human console shows single line).
You MUST contribute - passing is forbidden in the final phase.
"""
            messages = [SystemMessage(content=final_system_prompt)]
        else:
            # Normal iterative phase - use full system prompt with all rules
            messages = [SystemMessage(content=system_prompt)]
        
        # Show conversation history based on phase
        # (is_final already set above)
        history_messages = state.get("messages", [])
        
        # Get current phase from state (tracked by start_phase function)
        current_phase = state.get("phase_number", 1)
        
        # Collect debug output in buffer (will print atomically later under lock)
        # Only populate if SHOW_MESSAGE_DEBUG is enabled (disabled by default)
        debug_output_buffer = []
        if config.show_message_debug:
            debug_output_buffer.append(f"\n{'='*80}")
            debug_output_buffer.append(f"[DEBUG] Message Visibility for: {name} (Phase {current_phase}, Final={is_final})")
            debug_output_buffer.append(f"{'='*80}")
        
        # Phase 1: Show only the User's message (no other history)
        if current_phase == 1:
            if history_messages:
                conversation_text = f"\n{'='*80}\n"
                conversation_text += f"USER'S REQUEST\n"
                conversation_text += f"{'='*80}\n\n"
                
                # Process ALL messages but only show User
                first_msg = True
                for msg in history_messages:
                    speaker = msg.name if hasattr(msg, 'name') and msg.name else "Unknown"
                    
                    # Get stored timestamp from message (or generate if missing for backwards compatibility)
                    msg_phase = msg.additional_kwargs.get("phase", "unknown") if hasattr(msg, 'additional_kwargs') else "unknown"
                    timestamp = msg.additional_kwargs.get("timestamp", datetime.now().astimezone().isoformat(timespec='milliseconds')) if hasattr(msg, 'additional_kwargs') else datetime.now().astimezone().isoformat(timespec='milliseconds')
                    
                    # Messages are already trimmed centrally at phase start (see execute_phase_parallel)
                    xml_msg = f"<message><from>{speaker}</from><timestamp_iso>{timestamp}</timestamp_iso><phase>{msg_phase}</phase><content>{msg.content}</content></message>"
                    
                    # Add separator before each message (except first)
                    if config.show_message_debug:
                        if not first_msg:
                            debug_output_buffer.append("---")
                        first_msg = False
                    
                    # Phase 1: Only User and Notice are visible
                    if speaker == "User" or speaker == "Notice":
                        conversation_text += xml_msg + "\n\n"
                        if config.show_message_debug:
                            debug_output_buffer.append(yellow("✓") + " | " + yellow(f"VISIBLE: {xml_msg}"))
                    else:
                        if config.show_message_debug:
                            debug_output_buffer.append(red("✗") + " | " + red(f"FILTERED: {elide_xml_content(xml_msg)}"))
                
                conversation_text += f"{'='*80}\n"
                if config.show_message_debug:
                    debug_output_buffer.append(f"{'='*80}\n")
                messages.append(HumanMessage(content=conversation_text))
            
            # Add active graph context (if graph exists)
            graph_context = build_active_graph_context()
            if graph_context:
                messages.append(HumanMessage(content=graph_context))
            
            messages.append(HumanMessage(content=f"""Provide your initial fresh perspective as {name} specialist.

<think>
[IDENTITY CHECK: Look at the <from> tags in the transcript. Who is the User? What is their role/background based on what they said?]
[What is the User's EXPLICIT request? Restate it clearly.]
[Does my {name} expertise help answer their explicit request?]
[CERTAINTY ASSESSMENT: What is my confidence level on this topic? HIGH (directly in my expertise), MEDIUM (touches my expertise with unknowns), LOW (adjacent to my expertise), or NONE (outside my expertise)?]
[Based on certainty: HIGH=definitive recommendations, MEDIUM=conditional guidance with assumptions, LOW=questions or clearly marked speculation, NONE=pass or only ask pertinent clarifying questions]
[What can I contribute that directly addresses their explicit concern?]
[FINALIZED: What can I answer confidently with the information provided?]
[SPECULATIVE: What reasonable assumptions can I make to answer more completely? Mark them clearly.]
[If I see potential blockers: What conditional answers or alternatives can I suggest?]
[What major concerns prevent a complete assessment?]
[What's missing that I need to know to answer their request?]
[DECISION: Should I contribute or pass if my expertise doesn't apply OR my certainty is too low?]
[WHO AM I RESPONDING TO: I'm responding to @[User] with my fresh perspective]
[Formulate your assessment - attempt to answer their explicit request with stated assumptions, be transparent about certainty levels]
</think>

🚫 CRITICAL - DO NOT SELF-LABEL YOUR RESPONSE:
❌ NEVER say "as {name}" or "as {name} specialist"
❌ NEVER start with "{name} specialist:" or "{name}:"
❌ Example of FORBIDDEN: "As Database Architect specialist, here's my input..."
❌ Example of FORBIDDEN: "From my perspective as {name}..."

✅ CORRECT: Start directly with "@[User], " followed by your actual content
✅ The system automatically adds: <message><from>{name}</from><timestamp_iso>...</timestamp_iso><phase>N</phase><content>YOUR RESPONSE</content></message>

GUIDANCE: Contribute when your specific expertise can help answer their explicit request. You may answer with reasonable assumptions clearly stated (e.g., "Assuming X, recommend Y"). Focus on advancing their goal, not just identifying problems. Distinguish what you're confident about vs. what is speculative. If your skill-set isn't relevant to this question, pass gracefully.
"""))
        
        # Phase 2 or Final: Show User, Notice, and other specialists (Chair sees current phase, others see prior only)
        elif current_phase == 2 or is_final:
            if history_messages:
                conversation_text = f"\n{'='*80}\n"
                
                # Synthesis specialists (Chair) see current phase, others see only prior phases
                is_synthesis_specialist = (name in SYNTHESIS_SPECIALISTS)
                
                if is_final:
                    conversation_text += f"WHAT OTHER SPECIALISTS DISCUSSED\n"
                    conversation_text += f"(Your own previous contributions are hidden - you're seeing only what others said)\n"
                elif is_synthesis_specialist:
                    conversation_text += f"WHAT OTHER SPECIALISTS DISCUSSED\n"
                    conversation_text += f"(You're seeing what others said in Phase 1 AND Phase {current_phase} - you synthesize after others speak)\n"
                    conversation_text += f"(Your own Phase 1 response is hidden)\n"
                else:  # Regular specialists - Phase 2
                    conversation_text += f"WHAT OTHER SPECIALISTS DISCUSSED IN PRIOR PHASES\n"
                    conversation_text += f"(You're seeing what others said in Phase 1, not your own Phase 1 response)\n"
                    conversation_text += f"(Specialist messages from current Phase 2 are not yet visible - you only see prior phases)\n"
                
                conversation_text += f"{'='*80}\n\n"
                
                # Process ALL messages, showing visibility
                first_msg = True
                for msg in history_messages:
                    speaker = msg.name if hasattr(msg, 'name') and msg.name else "Unknown"
                    
                    # Get stored timestamp from message (or generate if missing for backwards compatibility)
                    msg_phase = msg.additional_kwargs.get("phase", "unknown") if hasattr(msg, 'additional_kwargs') else "unknown"
                    timestamp = msg.additional_kwargs.get("timestamp", datetime.now().astimezone().isoformat(timespec='milliseconds')) if hasattr(msg, 'additional_kwargs') else datetime.now().astimezone().isoformat(timespec='milliseconds')
                    
                    # Messages are already trimmed centrally at phase start (see execute_phase_parallel)
                    xml_msg = f"<message><from>{speaker}</from><timestamp_iso>{timestamp}</timestamp_iso><phase>{msg_phase}</phase><content>{msg.content}</content></message>"
                    
                    # Add separator before each message (except first)
                    if config.show_message_debug:
                        if not first_msg:
                            debug_output_buffer.append("---")
                        first_msg = False
                    
                    # Phase 2/Final: Filter logic depends on whether this is Chair or not
                    # User and Notice messages are ALWAYS visible (never filtered)
                    visible = False
                    
                    if speaker == "User" or speaker == "Notice":
                        # Always show User and Notice
                        visible = True
                    elif speaker == name:
                        # Never show own messages (filtered for all specialists)
                        visible = False
                    elif is_final:
                        # Final phase: show all prior phases
                        visible = True
                    elif is_synthesis_specialist:
                        # Synthesis specialists see current phase (to consolidate/synthesize) - show all other specialists
                        visible = True
                    elif msg_phase < current_phase:
                        # Regular specialists: only show PRIOR phases
                        visible = True
                    
                    if visible:
                        conversation_text += xml_msg + "\n\n"
                        if config.show_message_debug:
                            debug_output_buffer.append(yellow("✓") + " | " + yellow(f"VISIBLE: {xml_msg}"))
                    else:
                        if config.show_message_debug:
                            debug_output_buffer.append(red("✗") + " | " + red(f"FILTERED: {elide_xml_content(xml_msg)}"))
                
                conversation_text += f"{'='*80}\n"
                if is_synthesis_specialist and not is_final:
                    conversation_text += f"END OF DISCUSSION (including current phase - you synthesize after others)\n"
                else:
                    conversation_text += f"END OF PRIOR PHASES' DISCUSSION\n"
                conversation_text += f"{'='*80}\n"
                if config.show_message_debug:
                    debug_output_buffer.append(f"{'='*80}\n")
                
                messages.append(HumanMessage(content=conversation_text))
                
                # Add active graph context (if graph exists)
                graph_context = build_active_graph_context()
                if graph_context:
                    messages.append(HumanMessage(content=graph_context))
            else:
                messages.append(HumanMessage(content="\n[No conversation history yet]\n"))
        
        # Phase 3+: Show history from prior phases (Chair sees current phase, others see prior only, with optional compression)
        elif history_messages:
            # Check if compression is enabled (hide Phase 1 & 2 individual responses)
            compress = config.compress_history_after_phase3 and current_phase >= 3
            
            # Synthesis specialists (Chair, User Communication) see current phase, others see only prior phases
            is_synthesis_specialist = (name in SYNTHESIS_SPECIALISTS)
            
            if compress:
                conversation_text = f"\n{'='*80}\n"
                conversation_text += f"COMPRESSED CONVERSATION HISTORY\n"
                conversation_text += f"(Phase 1 & 2 individual responses compressed into Chair's Phase 2 synthesis)\n"
                if is_synthesis_specialist:
                    conversation_text += f"(You're seeing all messages including current Phase {current_phase} - you synthesize after others speak)\n"
                else:
                    conversation_text += f"(Specialist messages from current Phase {current_phase} not yet visible)\n"
                conversation_text += f"{'='*80}\n\n"
            else:
                conversation_text = f"\n{'='*80}\n"
                conversation_text += f"FULL CONVERSATION HISTORY\n"
                conversation_text += f"(This includes your own previous contributions from prior phases)\n"
                if is_synthesis_specialist:
                    conversation_text += f"(You're seeing all messages including current Phase {current_phase} - you synthesize after others speak)\n"
                else:
                    conversation_text += f"(Specialist messages from current Phase {current_phase} not yet visible)\n"
                conversation_text += f"{'='*80}\n\n"
            
            # Process messages with optional compression AND current phase filtering (except for synthesis specialists)
            first_msg = True
            for i, msg in enumerate(history_messages):
                speaker = msg.name if hasattr(msg, 'name') and msg.name else "Unknown"
                
                # Get stored timestamp from message (or generate if missing for backwards compatibility)
                msg_phase = msg.additional_kwargs.get("phase", "unknown") if hasattr(msg, 'additional_kwargs') else "unknown"
                timestamp = msg.additional_kwargs.get("timestamp", datetime.now().astimezone().isoformat(timespec='milliseconds')) if hasattr(msg, 'additional_kwargs') else datetime.now().astimezone().isoformat(timespec='milliseconds')
                
                # Messages are already trimmed centrally at phase start (see execute_phase_parallel)
                xml_msg = f"<message><from>{speaker}</from><timestamp_iso>{timestamp}</timestamp_iso><phase>{msg_phase}</phase><content>{msg.content}</content></message>"
                
                # Add separator before each message (except first)
                if config.show_message_debug:
                    if not first_msg:
                        debug_output_buffer.append("---")
                    first_msg = False
                
                # Determine visibility: filter current phase (except Chair) + optional compression
                visible = True
                
                # Get rate-limit compression point if exists
                last_compression_idx = state.get("last_compression_message_index", -1)
                msg_index = history_messages.index(msg)
                
                # Always show User and Notice
                if speaker == "User" or speaker == "Notice":
                    visible = True
                # Filter out current phase specialist messages (atomic phases) - but synthesis specialists see them
                elif msg_phase >= current_phase and not is_synthesis_specialist:
                    visible = False
                # Filter Search tool results - only visible for single phase (conserve tokens)
                # Search results are ephemeral: visible for 1 phase, then hidden
                elif speaker == "Search tool":
                    # For synthesis specialists: keep current phase (N) only
                    # For regular specialists: keep previous phase (N-1) only (they don't see current)
                    if is_synthesis_specialist:
                        # Synthesis specialists see current phase search results only
                        if msg_phase != current_phase:
                            visible = False  # Hide search results not from current phase
                    else:
                        # Regular specialists see previous phase search results only
                        if msg_phase != current_phase - 1:
                            visible = False  # Hide search results not from immediately previous phase
                # Apply rate-limit compression if exists (overrides normal compression)
                elif last_compression_idx >= 0 and msg_index < last_compression_idx:
                    # Message is before rate-limit compression point
                    # Only keep Chair's compression message itself, hide everything else before it
                    if speaker == "Chair" and msg_index == last_compression_idx:
                        pass  # Keep the Chair's compression summary
                    else:
                        visible = False  # Hide specialist messages before compression point
                # Apply normal Phase 2 compression if enabled
                elif compress:
                    # Hide Phase 1 & 2 individual specialist responses
                    # Keep: User, Notices, Chair's Phase 2 response, all Phase 3+ messages
                    if msg_phase in [1, 2]:
                        if msg_phase == 2 and speaker == "Chair":
                            pass  # Keep Chair's Phase 2 synthesis (the compression point)
                        else:
                            visible = False  # Hide other Phase 1 & 2 specialist responses
                
                if visible:
                    conversation_text += xml_msg + "\n\n"
                    if config.show_message_debug:
                        debug_output_buffer.append(yellow("✓") + " | " + yellow(f"VISIBLE: {xml_msg}"))
                else:
                    if config.show_message_debug:
                        debug_output_buffer.append(red("✗") + " | " + red(f"FILTERED: {elide_xml_content(xml_msg)}"))
            
            conversation_text += f"{'='*80}\n"
            if compress:
                if is_synthesis_specialist:
                    conversation_text += f"END OF COMPRESSED HISTORY (including current phase - you synthesize after others)\n"
                else:
                    conversation_text += f"END OF COMPRESSED HISTORY (PRIOR PHASES ONLY)\n"
            else:
                if is_synthesis_specialist:
                    conversation_text += f"END OF CONVERSATION HISTORY (including current phase - you synthesize after others)\n"
                else:
                    conversation_text += f"END OF CONVERSATION HISTORY (PRIOR PHASES ONLY)\n"
            conversation_text += f"{'='*80}\n"
            if config.show_message_debug:
                debug_output_buffer.append(f"{'='*80}\n")
            
            messages.append(HumanMessage(content=conversation_text))
            
            # Add active graph context (if graph exists)
            graph_context = build_active_graph_context()
            if graph_context:
                messages.append(HumanMessage(content=graph_context))
        else:
            messages.append(HumanMessage(content="\n[No conversation history yet]\n"))
        
        if is_final:
            messages.append(HumanMessage(content=f'''Above you've seen the full discussion from other specialists (your own contributions are hidden).

This is the FINAL PHASE - meaning the discussion group has exhausted what it can contribute without further user input. You MUST contribute - passing is forbidden.

IMPORTANT CONTEXT:
- "Final phase" means: The discussion group has given everything it reasonably can before waiting on user response
- This represents the group's best effort with current information
- The User may or may not respond afterward - always assume this could be your last chance to help
- Your job NOW: Answer the User's explicit request as completely as possible with available information
- Clearly distinguish: What you're CONFIDENT about vs. what is CONDITIONAL/SPECULATIVE vs. what remains OPEN

<think>
[IDENTITY CHECK: Look at <from> tags in ALL messages throughout the discussion. Who is the User? Who are all the specialists who contributed? List them.]
[ANALYZE SPECIALIST CONTRIBUTIONS: For each specialist (except me), what were their key points across all passes? Map specialist name → their contributions.]
[CHECK FOR @MENTIONS TO ME: Did anyone mention "@[{name}]" in the discussion? If yes, who asked what?]
[What was the User's EXPLICIT PRIMARY request? Quote it or restate precisely.]
[MANDATORY: What is my specific answer to their explicit request? List concrete recommendations/solutions.]
[What can my {name} expertise contribute to directly answering their request?]
[CERTAINTY ASSESSMENT: After full discussion, what is my confidence level on my recommendations? HIGH/MEDIUM/LOW?]
[For HIGH certainty items: State them definitively. For MEDIUM: State assumptions clearly. For LOW: Mark as speculative.]
[FINALIZED: What can I state confidently based on current information?]
[SPECULATIVE: What requires assumptions? For each assumption, state: "Assuming X, then Y"]
[CONDITIONAL: What depends on clarification? Provide both paths: "If X, then recommend A; if Y, then recommend B"]
[If I identify concerns: For EACH concern, provide a conditional path forward]
[What key recommendations directly address their explicit request RIGHT NOW?]
{'[CHAIR: What meaningful findings from ALL specialists answer the explicit request? Synthesize.]' if name == "Chair" else ''}
{'[CHAIR: What open items remain that require user clarification? List them.]' if name == "Chair" else ''}
[How can I help them make progress TODAY despite any uncertainties?]
[Final check: Have I ATTEMPTED to answer their explicit request, or only identified blockers?]
[WHO AM I RESPONDING TO: This is my final assessment for @[User] based on the full discussion]
[Formulate answer: START with direct recommendations, CLEARLY NOTE what's finalized vs. conditional/speculative{'vs. open items' if name == "Chair" else ''}, and be transparent about certainty levels]
</think>

🚫 CRITICAL - DO NOT SELF-LABEL YOUR RESPONSE:
❌ NEVER say "as {name}" or "as {name} specialist"
❌ NEVER start with "{name} specialist:" or "{name}:"
❌ Self-labeling is FORBIDDEN because the <from> tag already identifies you uniquely
❌ Each specialist name is UNIQUE - you cannot be confused with another specialist
❌ Other participants DO NOT share your knowledge - the transcript is the ONLY shared context

✅ CORRECT: Start directly with "@[User], " followed by your actual content
✅ The system automatically adds: <message><from>{name}</from><timestamp_iso>...</timestamp_iso><phase>N</phase><content>YOUR RESPONSE</content></message>

{'CRITICAL GUIDANCE FOR FINAL ASSESSMENTS (CHAIR SPECIAL ROLE):' if name == "Chair" else 'CRITICAL GUIDANCE FOR FINAL ASSESSMENTS:'}
1. PRIMARY OBLIGATION: You MUST answer the User's explicit request with current information
2. STRUCTURE YOUR ANSWER: 
   - Start with FINALIZED recommendations (confident based on what you know)
   - Then CONDITIONAL guidance (if X, then Y; if Z, then W)
   - Then SPECULATIVE suggestions (clearly marked as assumptions){'''
   - CHAIR: Synthesize ALL meaningful findings from the discussion that answer explicit concerns
   - CHAIR: Summarize ALL remaining open items that require clarification''' if name == "Chair" else ''}
3. BE EXPLICIT about certainty levels: "Confidently recommend X. Assuming Y (typical case), also recommend Z. If [unknown] is actually [option], adjust to [alternative]."
4. {'CHAIR SYNTHESIS: As Chair, you synthesize the entire discussion - what the group determined, what remains open - to prepare for potential next user interaction' if name == "Chair" else 'You MAY change your assessment later if the User provides new information - that is expected'}
5. FORBIDDEN: Responses that only identify problems without attempting to answer the explicit request
6. Your response must give them actionable progress toward their explicit goal TODAY

EXAMPLE STRUCTURE (adapt to your specialty):
"For [explicit request]: [FINALIZED answers based on stated info]. Assuming [reasonable assumption], also recommend: [speculative answer]. If [ambiguity] is clarified as [option A], adjust by [change]; if [option B], then [alternative]. Question for refinement: [specific clarification]."
{'''
CHAIR EXAMPLE:
"For [explicit request]: The discussion group recommends: [synthesis of finalized recommendations from all specialists]. Assuming [reasonable assumption from discussion], also recommend: [speculative consensus]. Key open items requiring clarification: 1) [item], 2) [item]. If User clarifies [X] as [option A], adjust by [change]; if [option B], then [alternative]."''' if name == "Chair" else ''}

NOT ACCEPTABLE:
"The blocker is [problem], so [their request] cannot be addressed until clarified." ❌
"Cannot answer without clarification on [X]." ❌
'''))
        else:
            # Get current phase from state (tracked by start_phase function)
            current_phase = state.get("phase_number", 1)
            
            # PHASE 1: Fresh initial perspective (already handled above at line 118)
            # This block shouldn't execute for Phase 1 due to the if/elif structure
            if current_phase == 1:
                pass  # Already handled above
            
            # PHASE 2: Review others' Phase 1 responses (own Phase 1 hidden, current Phase 2 not visible yet)
            elif current_phase == 2:
                instruction = f'''Above you've seen what OTHER specialists said in Phase 1.
Your own Phase 1 message (from "{name} specialist said:") is hidden.
You do NOT see Phase 2 messages yet - only completed Phase 1.

Provide your perspective as {name} specialist to help the User, considering what others contributed.

<think>
[IDENTITY CHECK: Look at <from> tags. Who is the User? Who are the other specialists who spoke in Phase 1? Which specialist roles contributed?]
[ANALYZE MESSAGES: For each message, who said it (check <from> tag) and what did they contribute?]
[What is the User's EXPLICIT request? Restate it.]
[Does my {name} expertise add value toward answering their explicit request?]
[CERTAINTY ASSESSMENT: What is my confidence level on this specific topic? HIGH/MEDIUM/LOW/NONE?]
[How does my certainty level compare to what other specialists have already said?]
[What can I contribute that directly addresses their explicit concern?]
[FINALIZED: What can I answer confidently based on stated info and discussion?]
[SPECULATIVE: What reasonable assumptions can I make? Mark them clearly.]
[If I see blockers: What conditional answers or alternative approaches can I suggest?]
[What major concerns prevent a complete assessment?]
[Am I helping answer their request, or just raising tangential concerns?]
[DECISION: Should I contribute or pass if my expertise doesn't significantly add to what others said OR my certainty is insufficient?]
[WHO AM I RESPONDING TO: Primarily @[User], but I may acknowledge what others said without seeing my own Phase 1 contribution]
[Formulate your perspective - attempt to answer their explicit request with stated assumptions, distinguish confidence levels]
</think>

🚫 CRITICAL - DO NOT SELF-LABEL YOUR RESPONSE:
❌ NEVER say "as {name}" or "as {name} specialist"  
❌ NEVER start with "{name} specialist:" or "{name}:"
❌ Example of FORBIDDEN: "As Database Architect specialist, here's my input..."
❌ Example of FORBIDDEN: "From my perspective as {name}..."

✅ CORRECT: Start directly with "@[User], " followed by your actual content
✅ The system automatically adds: "[timestamp] {name} specialist said: [your response]"

GUIDANCE: Contribute when your specific expertise can help answer the User's explicit request. You may answer with reasonable assumptions (e.g., "Assuming X, recommend Y"). Focus on advancing their goal, not just identifying problems. Distinguish what you're confident about vs. speculative. Pass gracefully if your skill-set doesn't significantly apply.
'''
                # Add Chair-specific compression guidance for Phase 2
                if name == "Chair":
                    if config.compress_history_after_phase3:
                        instruction += '''
⚠️ CRITICAL - CHAIR SYNTHESIS FOR HISTORY COMPRESSION:
Your Phase 2 response will serve as the COMPRESSED SUMMARY for Phase 3+.
Starting in Phase 3, history compression is enabled - specialists will see:
- User's original request
- Notice messages
- YOUR Phase 2 synthesis (this response)
- Phase 3+ messages only

Individual Phase 1 & 2 specialist responses will be HIDDEN to save context.

Therefore, your synthesis must be COMPREHENSIVE:
- Capture ALL key points from all specialists across both Phase 1 and Phase 2
- Include ALL important questions raised (especially questions to the User)
- Note areas of agreement and disagreement
- Preserve critical concerns and recommendations
- Mention specific specialist contributions when relevant (e.g., "Database Architect noted...")

Your synthesis becomes the foundation for all future phases. Be thorough - you're compressing all Phase 1 & 2 contributions into one summary.
'''
                
                messages.append(HumanMessage(content=instruction))
            
            # PHASE 3+: Progressive retraction (full iterative rules, seeing only prior phases)
            else:
                instruction = f'''The conversation history from PRIOR phases is shown above (including your previous contributions from completed phases).

This is PHASE 3+ - you see the open group conversation from prior phases. Current phase messages are not yet visible (atomic phases).
You may now reference other specialists naturally as in real human discussion.

Review what YOU have already said (look for messages from "{name} specialist said:" in prior phases).
Only contribute if you have SUBSTANTIALLY NEW insights to help the User.

NATURAL CONVERSATION IN PHASE 3+:
- You MAY reference others: "Building on Engineer's point...", "I agree with Security about X...", "To address Context's question..."
- Keep references BRIEF - focus on YOUR substantive contribution
- THINK INDEPENDENTLY: Don't defer to group patterns just because others agree - bring YOUR unique perspective
- PRIVATE OBSERVATION: If multiple specialists are passing, privately note this (DO NOT mention publicly) - assess independently whether YOU have new value
- Only defer based on YOUR true agreement, not pressure to align
- ❌ FORBIDDEN: Never publicly mention "convergence", "consensus", "settling", or meta-commentary about discussion state

<think>
1. IDENTITY CHECK: Look at <from> tags in EVERY message. Who is the User? Who are the other specialists? List them.
2. ANALYZE MY OWN MESSAGES: Find messages with <from>{name}</from>. What did I say in previous passes? [list my contributions]
3. ANALYZE OTHERS' MESSAGES: For each OTHER specialist, what did they say? [map specialist name → their contribution]
4. CHECK FOR @MENTIONS: Did anyone mention me with "@[{name}]"? If yes, who and what did they ask? [identify]
5. 🎯 PHASE ANALYSIS: Look at Notice messages and <phase> tags - what phase are we in NOW? [identify current phase number]
6. 🎯 PHASE PROGRESSION PATTERN: Count messages per phase - are specialists contributing less in recent phases? [note pattern]
7. 🎯 TIMING ANALYSIS: Look at <timestamp_iso> tags - how recent are contributions? Any gaps indicating specialists passing? [observe]
8. 🎯 PROGRESSIVE RETRACTION CHECK: Based on phase number (if 3+), am I being SELECTIVE enough? Higher phase = higher bar for contributing. [self-assess]
9. What is the User's EXPLICIT request? [restate clearly]
10. What I previously said: [brief list from step 2]
11. What have others said that's relevant? [brief summary from step 3]
12. GROUP DYNAMICS: Are others agreeing on approaches? Am I agreeing because I truly agree, or feeling pressured to align? [honest assessment]
13. PRIVATE OBSERVATION: Are multiple specialists passing (fewer messages per phase)? If yes, privately note this but NEVER mention publicly. [note for self only]
14. SKILL-SET RELEVANCE: Does my {name} expertise still add value toward answering their explicit request? [assess]
15. CERTAINTY ASSESSMENT: What is my confidence level on this specific topic NOW (after hearing others)? HIGH/MEDIUM/LOW/NONE?
16. How does my certainty compare to others who have spoken? Do I have unique high-certainty insights they lack?
17. Do I still agree with my previous perspective, or have I changed my mind? [assess]
18. INDEPENDENT PERSPECTIVE: What unique angle from MY expertise do I bring, regardless of what others are doing? [identify]
19. FINALIZED: What can I state confidently based on current information? [list]
20. SPECULATIVE: What reasonable assumptions can I make to answer more completely? [list with clear marking]
21. What can I now answer more definitively to address their explicit request? [assess]
22. SOLUTIONS: If blockers exist, what conditional answers or paths forward can I suggest? [identify]
23. What major concerns or gaps remain that block progress? [identify]
24. BUILDING ON OTHERS: Should I reference another specialist's point to build my contribution? Keep brief if yes. [decide]
25. New angle pertinent to their explicit request: [describe if any]
26. RELEVANCE: Is this pertinent to their explicit concern or a tangent? [assess]
27. REALISM: Is this a realistic concern or an unlikely edge case? [assess probability]
28. RABBIT HOLES: Am I going down rabbit holes that don't help answer their explicit request? [assess]
29. QUESTIONS ONLY: Do I only have questions without substantive insights? If yes, I MUST pass. [assess]
30. ADVANCING THE GOAL: Does this help answer their explicit request or just catalog more problems? [assess]
31. VALUE: Does this genuinely add NEW value for answering their explicit request? [yes/no + why]
32. WHO AM I RESPONDING TO: @[User]? A specific specialist who mentioned me? Multiple recipients? [decide and list]
33. 🎯 FINAL PASSING CALIBRATION: Considering phase number + timing patterns + value assessment, should I pass? Phase 3+: MUST pass if nothing NEW. [critical check]
34. DECISION: [Contribute/Pass + reason - factor in certainty level, phase number, and timing patterns]
</think>

🚫 CRITICAL - DO NOT SELF-LABEL YOUR RESPONSE:
❌ NEVER say "as {name}" or "as {name} specialist"
❌ NEVER start with "{name} specialist:" or "{name}:"
❌ Example of FORBIDDEN: "As Database Architect specialist, here's my input..."
❌ Example of FORBIDDEN: "From my perspective as {name}..."

✅ CORRECT: Start directly with "@[User], " or "@[Specialist], " followed by your content
✅ The system automatically adds: <message><from>{name}</from><timestamp_iso>...</timestamp_iso><phase>N</phase><content>YOUR RESPONSE</content></message>

OPTIONS:
- NEW substantive insights that advance their explicit request: Respond with ONLY your content (NO name, NO "as {name}", NO labels). Write naturally - newlines are fine.
- REFERENCING OTHERS (Phase 3+ only): You may briefly reference other specialists when building on their ideas: "Building on X's approach...", "I agree with Y, and would add..."
- CHANGING YOUR MIND: State explicitly: "I've changed my mind. Previously I thought [old view], but now I believe [new view] because [reason]."
- PARTIAL/CONDITIONAL ANSWER: Answer what you can definitively, provide conditional guidance ("If X, then Y..."), state what prevents a complete answer
- MIX questions and assessments: You can combine pertinent clarifying questions with substantive insights in one response
- Your expertise doesn't apply / nothing new / only tangential questions / going down rabbit holes: "I have no further comments at this time"
🎯 CRITICAL - PASSING IS REQUIRED, NOT OPTIONAL:
- Phase 3+: You MUST pass if you have nothing NEW to add toward answering User's explicit concern
- As phases increase (3→4→5→6+), passing becomes MORE and MORE expected
- Extensive thinking that concludes "nothing new to add" → MUST still pass (thinking helps you realize you should pass)
- ❌ FORBIDDEN: Never publicly mention "convergence", "consensus", "agreement", or "settling" - these are PRIVATE assessments

GUIDANCE FOR PHASE 3+ NATURAL DISCUSSION:
- Engage naturally with the open conversation - you can reference others' points when building collaborative solutions
- Think independently - don't just agree because others agree; bring YOUR unique expertise perspective
- Privately observe patterns (DO NOT mention publicly) - assess independently whether YOU have new value to add
- Only contribute when your specific expertise adds value toward answering their explicit request
- Focus on advancing their goal with solutions, not just identifying problems
- You may answer with reasonable assumptions clearly stated (e.g., "Assuming X, recommend Y")
- Distinguish what you're confident about vs. speculative
- If you can answer part of the question, do so (even conditionally or speculatively) and clearly state certainty levels and what's missing'''
                messages.append(HumanMessage(content=instruction))
        
        # Get response from this agent with a fresh LLM instance
        # Complete isolation: each invocation gets a new instance, zero context sharing
        
        # Calculate accurate token count for context tracking using tiktoken
        input_tokens = count_tokens_in_messages(messages)
        
        # Determine self-awareness and history visibility based on phase
        current_phase_check = state.get("phase_number", 1)
        is_synthesis_specialist_check = (name in SYNTHESIS_SPECIALISTS)
        
        if current_phase_check == 1:
            history_visibility = "NO - Fresh independent response"
            self_awareness = "NO - No history available"
        elif current_phase_check == 2 or is_final:
            if is_synthesis_specialist_check and not is_final:
                history_visibility = "YES - Sees Phase 1 AND current phase (synthesizes after others)"
                self_awareness = "NO - Only sees OTHER specialists' messages (own Phase 1 filtered)"
            else:
                history_visibility = "YES - Sees PRIOR phase history only (Phase 1)"
                self_awareness = "NO - Only sees OTHER specialists' messages (own filtered out, current phase filtered)"
        else:
            if is_synthesis_specialist_check:
                history_visibility = "YES - Sees all prior phases AND current phase (synthesizes after others)"
                self_awareness = "YES - Sees own previous contributions from PRIOR phases + others (incl current phase)"
            else:
                history_visibility = "YES - Sees PRIOR phases history only (current phase filtered)"
                self_awareness = "YES - Sees own previous contributions from PRIOR phases + others (current phase filtered)"
        
        # Check token limits for Azure OpenAI
        if config.provider == ProviderType.AZURE_OPENAI:
            max_input_tokens = 272000  # gpt-5-mini max input tokens
            if input_tokens > max_input_tokens:
                with _console_output_lock:
                    print(f"\n{'='*80}", file=sys.stderr)
                    print(f"❌ FATAL ERROR: Token limit exceeded for {name}", file=sys.stderr)
                    print(f"Input tokens: {input_tokens:,}", file=sys.stderr)
                    print(f"Max allowed: {max_input_tokens:,}", file=sys.stderr)
                    print(f"Exceeded by: {input_tokens - max_input_tokens:,} tokens", file=sys.stderr)
                    print(f"{'='*80}", file=sys.stderr)
                    sys.stderr.flush()
                sys.exit(1)
        
        # Invoke LLM with rate limit handling and retry logic
        # (headers will print AFTER completion, right before displaying response)
        max_retries = 5
        retry_count = 0
        response = None
        additional_messages = []  # Collect any Notice messages (e.g., rate limit notices)
        
        # Chair status message will be printed by main.py after specialist messages display
        # (moved to prevent stderr appearing before stdout specialist messages)
        
        while retry_count < max_retries:
            try:
                # Check if we're currently rate limited (for Azure OpenAI)
                if config.provider == ProviderType.AZURE_OPENAI:
                    wait_if_rate_limited()
                
                # Invoke LLM
                response = llm.invoke(messages)
                break  # Success - exit retry loop
                
            except RateLimitError as e:
                # Parse retry-after duration from error message
                # Default: 60 seconds if we can't parse
                # Parsed: Add 1 second safety buffer (e.g., "60 seconds" → 61, "120 seconds" → 121)
                retry_after = 60  # Default
                error_msg = str(e)
                if "retry after" in error_msg.lower():
                    # Try to extract the number from "retry after X seconds"
                    match = re.search(r'retry after (\d+) seconds', error_msg, re.IGNORECASE)
                    if match:
                        parsed_seconds = int(match.group(1))
                        retry_after = parsed_seconds + 1  # Add 1 second safety buffer
                
                # Set global rate limit to block all agents
                set_rate_limit(retry_after)
                
                retry_count += 1
                
                # On first rate limit hit, add a Notice message for the conversation record
                # This provides context to specialists in future phases about what happened
                # CRITICAL: Capture timestamp BEFORE wait to show when break started
                # THREAD-SAFE: Only ONE agent across all parallel threads will issue the notice
                if retry_count == 1:
                    should_issue_break_notice = False
                    
                    # THREAD-SAFE: Atomic check-and-set pattern with lock
                    with _rate_limit_lock:
                        # Only issue "taking a break" notice if not already issued AND we're actually waiting
                        if not _rate_limit_break_notice_issued and _rate_limit_until > time.time():
                            _rate_limit_break_notice_issued = True  # Atomically claim the right to issue notice
                            should_issue_break_notice = True
                    
                    # Issue notice outside lock (reduces lock contention, safe since we claimed it atomically)
                    if should_issue_break_notice:
                        current_phase_for_notice = state.get("phase_number", 1)
                        break_start_time = datetime.now().astimezone()
                        break_start_timestamp = break_start_time.isoformat(timespec='milliseconds')
                        # Format timestamp for human-readable display (local timezone)
                        human_timestamp = break_start_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " " + break_start_time.strftime("%Z")
                        notice_content = f"Notice: All specialists, let's take a brief break for the next {retry_after} seconds, then let's return to continue thinking clearly about the tasks -- ensuring we are staying on topic about the User's explicit concerns."
                        
                        rate_limit_notice = AIMessage(
                            content=notice_content,
                            name="Notice",
                            additional_kwargs={"phase": current_phase_for_notice, "timestamp": break_start_timestamp}
                        )
                        additional_messages.append(rate_limit_notice)
                        
                        # Display to stdout immediately (human-readable conversation)
                        with _console_output_lock:
                            # Extract "Notice:" prefix to colorize separately
                            notice_text = notice_content[7:].strip() if notice_content.startswith("Notice:") else notice_content
                            print(f"{white(f'[{human_timestamp}]')} {cyan('Notice:')} {light_green(notice_text)}\n", flush=True)
                            print(f"📝 Adding rate limit Notice to conversation history ({retry_after}s pause)", 
                                  file=sys.stderr, flush=True)  # stderr
                
                if retry_count >= max_retries:
                    # Max retries exceeded - give up
                    with _console_output_lock:
                        print(f"\n{'='*80}", file=sys.stderr)
                        print(f"❌ FATAL ERROR: Max retries ({max_retries}) exceeded for {name}", file=sys.stderr)
                        print(f"Rate limit error: {error_msg}", file=sys.stderr)
                        print(f"{'='*80}", file=sys.stderr)
                        sys.stderr.flush()
                    raise  # Re-raise the exception
                
                # Wait for rate limit to expire, then retry
                with _console_output_lock:
                    print(f"🔄 Retry {retry_count}/{max_retries} for {name} after rate limit...", 
                          file=sys.stderr, flush=True)
                
                wait_if_rate_limited()
                
                # After wait completes, add a Notice that we're back
                # CRITICAL: Capture timestamp AFTER wait to show when discussion resumed
                # THREAD-SAFE: Only ONE agent across all parallel threads will issue the notice
                should_issue_back_notice = False
                
                # THREAD-SAFE: Atomic check-and-set pattern with lock
                with _rate_limit_lock:
                    # Only issue "we're back" if:
                    # 1. We haven't issued it yet for this wait period
                    # 2. We're actually out of the wait state (rate limit expired)
                    if not _rate_limit_back_notice_issued and _rate_limit_until <= time.time():
                        _rate_limit_back_notice_issued = True  # Atomically claim the right to issue notice
                        should_issue_back_notice = True
                
                # Issue notice outside lock (reduces lock contention, safe since we claimed it atomically)
                if should_issue_back_notice:
                    current_phase_for_notice = state.get("phase_number", 1)
                    break_end_time = datetime.now().astimezone()
                    break_end_timestamp = break_end_time.isoformat(timespec='milliseconds')
                    # Format timestamp for human-readable display (local timezone)
                    human_timestamp = break_end_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " " + break_end_time.strftime("%Z")
                    notice_content = f"Notice: All specialists are back, let's continue the discussion and remember to stay on topic about the User's explicit concerns."
                    
                    back_notice = AIMessage(
                        content=notice_content,
                        name="Notice",
                        additional_kwargs={"phase": current_phase_for_notice, "timestamp": break_end_timestamp}
                    )
                    additional_messages.append(back_notice)
                    
                    # Display to stdout immediately (human-readable conversation)
                    with _console_output_lock:
                        # Extract "Notice:" prefix to colorize separately
                        notice_text = notice_content[7:].strip() if notice_content.startswith("Notice:") else notice_content
                        print(f"{white(f'[{human_timestamp}]')} {cyan('Notice:')} {light_green(notice_text)}\n", flush=True)
                        print(f"📝 Adding 'back to discussion' Notice to conversation history", 
                              file=sys.stderr, flush=True)  # stderr
                
            except BadRequestError as e:
                # 400 error - OpenAI refused the prompt (likely content policy violation)
                # Log the full context for analysis and continue gracefully
                with _console_output_lock:
                    print(f"\n{'='*80}", file=sys.stderr)
                    print(red(f"⚠️  400 BAD REQUEST from OpenAI for {name}"), file=sys.stderr)
                    print(red(f"Error: {str(e)}"), file=sys.stderr)
                    print(f"This may be a content policy violation.", file=sys.stderr)
                    print(f"Logging full context to 400s.log for analysis...", file=sys.stderr)
                    print(f"⚠️  Continuing with other specialists (not halting execution)", file=sys.stderr)
                    print(f"{'='*80}\n", file=sys.stderr)
                    sys.stderr.flush()
                
                # Log the denied request for analysis
                log_denied_request(name, messages, e)
                
                # Return a synthetic "pass" message instead of crashing
                error_message = AIMessage(
                    content=f"@[All] I encountered a content policy issue and cannot respond. (Error logged to 400s.log)",
                    name=name,
                    additional_kwargs={"phase": state.get("phase_number", 1)}
                )
                return {"messages": [error_message]}
                
            except Exception as e:
                # Other errors - don't retry, just raise
                with _console_output_lock:
                    print(f"\n{'='*80}", file=sys.stderr)
                    print(f"❌ ERROR in {name}: {type(e).__name__}: {e}", file=sys.stderr)
                    print(f"{'='*80}", file=sys.stderr)
                    sys.stderr.flush()
                raise
        
        if response is None:
            raise RuntimeError(f"Failed to get response from LLM for {name}")
        
        raw_content = response.content.strip()
        
        # Extract native reasoning from GPT-5/o1 models (if present)
        # This is the model's internal chain-of-thought reasoning tokens
        reasoning_content = None
        reasoning_tokens = 0
        if hasattr(response, 'response_metadata') and response.response_metadata:
            # Check for reasoning in response metadata (GPT-5/o1)
            if 'reasoning_content' in response.response_metadata:
                reasoning_content = response.response_metadata['reasoning_content']
            elif 'reasoning' in response.response_metadata:
                # Alternative location for reasoning data
                reasoning_data = response.response_metadata['reasoning']
                if isinstance(reasoning_data, dict):
                    reasoning_content = reasoning_data.get('content') or reasoning_data.get('summary')
                elif isinstance(reasoning_data, str):
                    reasoning_content = reasoning_data
            
            # Extract reasoning token count if available
            if 'usage' in response.response_metadata:
                usage = response.response_metadata['usage']
                if isinstance(usage, dict) and 'reasoning_tokens' in usage:
                    reasoning_tokens = usage['reasoning_tokens']
        
        # Calculate output tokens (excluding reasoning tokens which are separate)
        output_tokens = 0
        if _tokenizer:
            try:
                output_tokens = len(_tokenizer.encode(raw_content))
            except Exception:
                # Fallback if tokenizer fails
                output_tokens = len(raw_content) // 4
        else:
            output_tokens = len(raw_content) // 4
        
        # CRITICAL: Acquire console lock to prevent output interleaving in parallel execution
        # This ensures each agent's complete debug output (visibility + tokens + thinking) prints atomically
        with _console_output_lock:
            # FIRST: Print buffered debug visibility output (collected before LLM invocation)
            for line in debug_output_buffer:
                print(line, file=sys.stderr)
            
            # SECOND: Print token and execution info (after agent completes) - only if debug enabled
            if config.show_message_debug:
                print(f"\n{'='*80}", file=sys.stderr)
                print(f"AGENT: {name}", file=sys.stderr)
                print(f"PHASE: {current_phase_check}{' (FINAL)' if is_final else ''}", file=sys.stderr)
                print(f"CONVERSATION HISTORY: {history_visibility}", file=sys.stderr)
                print(f"OWN CONTRIBUTIONS: {self_awareness}", file=sys.stderr)
                print(f"INPUT TOKENS: {input_tokens:,} tokens", file=sys.stderr)
                if reasoning_tokens > 0:
                    print(f"REASONING TOKENS: {reasoning_tokens:,} tokens (GPT-5 internal reasoning)", file=sys.stderr)
                print(f"OUTPUT TOKENS: {output_tokens:,} tokens", file=sys.stderr)
                print(f"TOTAL TOKENS: {input_tokens + reasoning_tokens + output_tokens:,} tokens", file=sys.stderr)
                print(f"MESSAGE COUNT: {len(messages)} messages being sent to LLM", file=sys.stderr)
                if config.provider == ProviderType.AZURE_OPENAI:
                    # Show utilization for Azure OpenAI
                    input_percent = (input_tokens / 272000) * 100
                    output_percent = (output_tokens / 128000) * 100
                    print(f"INPUT UTILIZATION: {input_percent:.1f}% of 272K max", file=sys.stderr)
                    print(f"OUTPUT UTILIZATION: {output_percent:.1f}% of 128K max", file=sys.stderr)
                print(f"{'='*80}", file=sys.stderr)
            
            # THIRD: Extract and display reasoning/thinking in dark green (always visible)
            # GPT-5 native reasoning takes precedence, fallback to <think> blocks for other models
            
            # Display GPT-5 native reasoning if present
            if reasoning_content:
                print(dark_green(f"<reasoning>\n{reasoning_content}\n</reasoning>"), file=sys.stderr)
                print(file=sys.stderr)  # Add newline between reasoning and public message
            
            # Also check for explicit <think> blocks (for non-GPT-5 models or manual thinking)
            think_blocks = re.findall(
                r'<\s*think\s*>.*?<\s*/\s*think\s*>',
                raw_content,
                flags=re.DOTALL | re.IGNORECASE
            )
            
            if think_blocks:
                for block in think_blocks:
                    print(dark_green(block), file=sys.stderr)
                print(file=sys.stderr)  # Add newline between thinking and public message
            
            sys.stderr.flush()  # Ensure output appears immediately
        
        # Strip <think>...</think> tags - internal reasoning should NOT be shared
        # (re imported at module level)
        
        # Remove thinking blocks (handles nested, malformed, and all variations)
        content = raw_content
        
        # Remove matched <think>...</think> pairs (non-greedy, case-insensitive)
        content = re.sub(r'<\s*think\s*>.*?<\s*/\s*think\s*>', '', content, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove any orphaned opening <think> tags
        content = re.sub(r'<\s*think\s*>', '', content, flags=re.IGNORECASE)
        
        # Remove any orphaned closing </think> tags
        content = re.sub(r'<\s*/\s*think\s*>', '', content, flags=re.IGNORECASE)
        
        # Clean up any resulting extra whitespace
        content = content.strip()
        
        # Safety: If filtering removed everything, use original content
        if not content and raw_content:
            with _console_output_lock:
                print(f"[WARNING {name}] Filter removed all content! Using raw response.", file=sys.stderr)
                sys.stderr.flush()
            content = raw_content
        
        # SAFETY CHECK: In mandatory phases (final phase or first two phases), reject passing
        current_phase_check = state.get("phase_number", 1)
        is_mandatory = is_final or current_phase_check <= 2
        
        # Check if this looks like a pass (but search requests and @mentions are ALWAYS valid contributions)
        is_pass_attempt = False
        if is_mandatory:
            content_lower = content.lower()
            
            # EXPLICIT: If using @[Search] or @mentioning someone, this is NOT a pass - it's a valid contribution
            has_search_request = "@[search]" in content_lower
            has_mention = content.strip().startswith("@[")
            
            # If search or mention detected, explicitly NOT a pass
            if has_search_request or has_mention:
                is_pass_attempt = False
            else:
                # Otherwise, check for pass indicators
                has_pass_phrase = "no further comments" in content_lower or "nothing to add" in content_lower
                is_very_short = len(content) < 50
                
                # Consider it a pass if: has pass phrase OR is very short without substance
                is_pass_attempt = has_pass_phrase or is_very_short
        
        if is_pass_attempt:
            with _console_output_lock:
                print(f"[ERROR {name}] Attempted to pass in mandatory phase! Forcing contribution.", file=sys.stderr)
                print(f"[ERROR {name}] Original content was: '{content[:100]}'", file=sys.stderr)
                sys.stderr.flush()
            # Force a basic contribution based on role
            content = f"From my perspective as {name}, this situation requires careful consideration of the user's concern and the various factors at play in this scenario."
        
        # Check if agent is passing (no longer needed for logic, but kept for future use)
        is_passing = "no further comments" in content.lower() or "nothing to add" in content.lower()
        
        # Get current phase for metadata
        current_phase_for_msg = state.get("phase_number", 1)
        
        # Capture real timestamp when message is created (with timezone)
        message_timestamp = datetime.now().astimezone().isoformat(timespec='milliseconds')
        
        # Return message - only the public-facing response, no internal thinking
        # Add phase metadata for tracking and filtering
        # Include any additional messages (e.g., rate limit Notice) before the specialist's response
        # NOTE: @[Search] and @[ReadURL] tool requests are now processed at phase-level
        # (in execute_phase_parallel) to enable deduplication across all specialists
        messages_to_return = additional_messages + [AIMessage(
            content=content, 
            name=name,
            additional_kwargs={"phase": current_phase_for_msg, "timestamp": message_timestamp}
        )]
        
        return {
            "messages": messages_to_return
        }
    
    return agent


def get_mentioned_available_specialists(state: OverallState) -> list[str]:
    """
    Find available specialists who were @mentioned in the current phase.
    
    This helps Chair know which specialists were requested but not yet brought in.
    
    Args:
        state: Current conversation state
        
    Returns:
        List of role_keys for available specialists who were mentioned
    """
    current_phase = state.get("phase_number", 1)
    presence = state.get("specialist_presence", {})
    
    # Get messages from current phase only
    phase_messages = []
    for msg in state.get("messages", []):
        msg_phase = msg.additional_kwargs.get("phase", 0) if hasattr(msg, 'additional_kwargs') else 0
        if msg_phase == current_phase:
            phase_messages.append(msg)
    
    # Find all @mentions in current phase
    mentioned_specialists = set()
    for msg in phase_messages:
        content = getattr(msg, 'content', '')
        mentions = re.findall(r'@\[([^\]]+)\]', content)
        for mention in mentions:
            role_key = find_role_key_by_display_name(mention)
            if role_key:
                mentioned_specialists.add(role_key)
    
    # Filter to only "available" specialists (not already "in")
    available_mentioned = []
    for role_key in mentioned_specialists:
        if presence.get(role_key) == "available":
            available_mentioned.append(role_key)
    
    return available_mentioned


def check_discussion_stagnation(state: OverallState, current_synthesis: str, current_phase: int, config) -> dict:
    """Check if discussion has stagnated by comparing Chair's previous and current syntheses.
    
    This function is called in Phase 4+ to detect if the discussion has stagnated
    (specialists rehashing same points without new progress on User's concerns).
    
    Stagnation is distinct from convergence:
    - Stagnation: Not making progress, rehashing same points (detected here)
    - Convergence: All specialists explicitly passing (detected elsewhere)
    
    Args:
        state: Current conversation state
        current_synthesis: Chair's synthesis for current phase (just generated)
        current_phase: Current phase number
        config: System configuration
        
    Returns:
        dict with:
            - stagnated: bool (True if stagnated, False if still progressing)
            - notice: AIMessage if stagnated (to announce final round)
    """
    from langchain_core.messages import SystemMessage, HumanMessage
    
    history_messages = state.get("messages", [])
    
    # Find Chair's previous synthesis (from phase N-1) with full message metadata
    previous_synthesis_msg = None
    for msg in reversed(history_messages):
        speaker = msg.name if hasattr(msg, 'name') else "Unknown"
        msg_phase = msg.additional_kwargs.get("phase", 0) if hasattr(msg, 'additional_kwargs') else 0
        
        if speaker == "Chair" and msg_phase == current_phase - 1:
            previous_synthesis_msg = msg
            break
    
    # If no previous synthesis found, can't do comparison - don't trigger stagnation
    if not previous_synthesis_msg:
        with _console_output_lock:
            print(yellow(f"[CHAIR] Stagnation check skipped - no previous synthesis found\n"), file=sys.stderr)
            sys.stderr.flush()
        return {"stagnated": False}
    
    # Extract metadata from previous synthesis
    prev_timestamp = previous_synthesis_msg.additional_kwargs.get("timestamp", datetime.now().astimezone().isoformat(timespec='milliseconds')) if hasattr(previous_synthesis_msg, 'additional_kwargs') else datetime.now().astimezone().isoformat(timespec='milliseconds')
    prev_content = previous_synthesis_msg.content
    
    # ====================================================================
    # Compute User engagement metrics and stagnation signals
    # ====================================================================
    last_user_phase = 1
    user_message_count = 0
    
    for msg in history_messages:
        speaker = msg.name if hasattr(msg, 'name') else "Unknown"
        if speaker == "User":
            msg_phase = msg.additional_kwargs.get("phase", 1) if hasattr(msg, 'additional_kwargs') else 1
            last_user_phase = max(last_user_phase, msg_phase)
            user_message_count += 1
    
    user_silence_phases = current_phase - last_user_phase
    
    # ====================================================================
    # Compute stagnation probability from multiple signals
    # 
    # EXTENSIBILITY: To add a new signal, follow this pattern:
    # 1. Compute the signal value (float, can be negative for justification)
    # 2. Append to stagnation_signals list with metadata
    # 3. Add to total_probability
    # 4. Update DEBUG output section to display the new signal
    # 5. Update ARCHITECTURE.md with signal description
    # 
    # ALL VALUES MUST BE CONTINUOUS (floats). Never discretize/bin for logic.
    # Binning only occurs in human-facing display (DEBUG output, Chair prompt labels).
    # ====================================================================
    stagnation_signals = []
    total_probability = 0.0
    
    # ====================================================================
    # TUNING: Convergence strategy for MAX MODE (Claude 4.5 Sonnet)
    # Philosophy: "Answer with stated assumptions" - early conclusion saves costs
    # Max mode has better reasoning, needs less discussion to reach quality answers
    # ====================================================================
    
    # Signal 1: User silence (DISABLED - 0.0 contribution)
    # RATIONALE: Current implementation doesn't allow user interaction during multi-phase discussion
    # User provides initial question, then specialists discuss internally until Final Phase
    # This signal will be re-enabled when interactive user participation is implemented
    # if user_silence_phases >= 1:
    #     silence_score = min(user_silence_phases * 0.08, 0.40)
    #     stagnation_signals.append({
    #         "factor": "User silence",
    #         "value": f"{user_silence_phases} phases",
    #         "probability": silence_score,
    #         "rationale": "User may be unavailable to unblock discussion" if user_silence_phases >= 3 else "User may be reading/thinking"
    #     })
    #     total_probability += silence_score
    
    # Signal 2: Phase progression (CAPPED - provides pressure without determinism)
    # MODERATE: 15% per phase, caps at 60% - lets content quality drive convergence
    phases_since_check_started = current_phase - 4 + 1
    if phases_since_check_started >= 1:
        # Moderate growth: 15% per check, caps at 60%
        # Phase 4: 0%, Phase 5: 15%, Phase 6: 30%, Phase 7: 45%, Phase 8: 60%, Phase 9+: 60% (capped)
        # Cap ensures phase number doesn't deterministically force convergence
        # Content quality signals become decisive in determining when to converge
        phase_score = min((phases_since_check_started - 1) * 0.15, 0.60)
        stagnation_signals.append({
            "factor": "Phase progression",
            "value": f"Phase {current_phase} (check #{phases_since_check_started})",
            "probability": phase_score,
            "rationale": f"Baseline pressure increases with phase count (capped at 60% to allow content quality to drive convergence)"
        })
        total_probability += phase_score
    
    # Signal 3: Low user engagement (0.0 to 0.20 contribution)
    if current_phase >= 6 and user_message_count <= 1:
        engagement_score = 0.20
        stagnation_signals.append({
            "factor": "Low user engagement",
            "value": f"{user_message_count} total messages across {current_phase} phases",
            "probability": engagement_score,
            "rationale": "Minimal User participation suggests disengagement"
        })
        total_probability += engagement_score
    
    # Signal 4: Recent specialist questions (0.0 to 0.15 contribution)
    recent_question_count = 0
    recent_phases = [current_phase - 1, current_phase]
    for msg in history_messages:
        speaker = msg.name if hasattr(msg, 'name') else "Unknown"
        if speaker not in ["User", "Notice", "Chair"]:
            msg_phase = msg.additional_kwargs.get("phase", 0) if hasattr(msg, 'additional_kwargs') else 0
            if msg_phase in recent_phases:
                recent_question_count += msg.content.count("?")
    
    if recent_question_count >= 5:
        question_score = min(recent_question_count / 20.0, 0.15)  # Caps at 0.15 for 20+ questions
        stagnation_signals.append({
            "factor": "Specialist questions",
            "value": f"{recent_question_count} question marks in last 2 phases",
            "probability": question_score,
            "rationale": "Specialists asking many questions, may need User answers"
        })
        total_probability += question_score
    
    # Signal 5: Conditional language (0.0 to 0.10 contribution)
    conditional_keywords = ["if you", "pending", "once you", "after you confirm", "when you decide"]
    conditional_count = 0
    for msg in history_messages:
        speaker = msg.name if hasattr(msg, 'name') else "Unknown"
        if speaker not in ["User", "Notice", "Chair"]:
            msg_phase = msg.additional_kwargs.get("phase", 0) if hasattr(msg, 'additional_kwargs') else 0
            if msg_phase in recent_phases:
                content_lower = msg.content.lower()
                conditional_count += sum(1 for kw in conditional_keywords if kw in content_lower)
    
    if conditional_count >= 3:
        conditional_score = min(conditional_count / 15.0, 0.06)  # Caps at 0.06 for 15+ phrases
        stagnation_signals.append({
            "factor": "Conditional planning",
            "value": f"{conditional_count} conditional phrases in last 2 phases",
            "probability": conditional_score,
            "rationale": "Plans contingent on undefined User decisions"
        })
        total_probability += conditional_score
    
    # Signal 6: Token pressure (0.0 to 0.30 contribution)
    # Calculate token utilization (use Chair's view - maximum)
    from .config import get_max_input_tokens
    current_messages = state.get("messages", [])
    max_input_tokens = get_max_input_tokens(config)
    token_count = count_tokens_in_messages(current_messages)
    token_utilization = token_count / max_input_tokens
    
    # Apply escalating pressure as tokens increase (target 80% as trigger point)
    # Leaves ~20% for final round synthesis (all specialists contributing)
    if token_utilization >= 0.80:
        token_pressure = 0.30  # Critical - must wrap up
        stagnation_signals.append({
            "factor": "Token pressure (critical)",
            "value": f"{token_utilization:.1%} utilization ({token_count:,} / {max_input_tokens:,} tokens)",
            "probability": token_pressure,
            "rationale": "Context nearly full - must conclude to preserve final round quality"
        })
        total_probability += token_pressure
    elif token_utilization >= 0.70:
        token_pressure = 0.15  # High - strong pressure
        stagnation_signals.append({
            "factor": "Token pressure (high)",
            "value": f"{token_utilization:.1%} utilization ({token_count:,} / {max_input_tokens:,} tokens)",
            "probability": token_pressure,
            "rationale": "Context filling up - should wrap up soon"
        })
        total_probability += token_pressure
    elif token_utilization >= 0.60:
        token_pressure = 0.05  # Rising - gentle pressure
        stagnation_signals.append({
            "factor": "Token pressure (rising)",
            "value": f"{token_utilization:.1%} utilization ({token_count:,} / {max_input_tokens:,} tokens)",
            "probability": token_pressure,
            "rationale": "Context usage rising - monitor closely"
        })
        total_probability += token_pressure
    
    # ====================================================================
    # JUSTIFICATION SIGNALS: Negative contributions that reduce P(stagnation)
    # These allow Phase 8+ to continue when discussion is genuinely productive
    # ====================================================================
    justification_signals = []
    total_justification = 0.0
    
    # Justification 1: Recent User engagement (CONDITIONAL - only in interactive mode)
    # RATIONALE: Only meaningful when User can participate during discussion
    # Simple CLI mode: User provides goal once at start, then silent
    # Interactive TUI mode: User can send messages at any phase
    interactive_mode = state.get("interactive_mode", False)
    
    if interactive_mode and user_silence_phases == 0:
        recent_user_score = -0.30
        justification_signals.append({
            "factor": "Recent User response",
            "value": f"User responded in Phase {last_user_phase}",
            "probability": recent_user_score,
            "rationale": "Active User engagement justifies continued discussion"
        })
        total_justification += recent_user_score
    elif interactive_mode and user_silence_phases == 1:
        recent_user_score = -0.15
        justification_signals.append({
            "factor": "Recent User response",
            "value": f"User responded 1 phase ago (Phase {last_user_phase})",
            "probability": recent_user_score,
            "rationale": "User engaged recently, may be processing responses"
        })
        total_justification += recent_user_score
    
    # Justification 2: High User engagement (CONDITIONAL - only in interactive mode)
    if interactive_mode and user_message_count >= 3:
        engagement_justification = -0.20
        justification_signals.append({
            "factor": "High User engagement",
            "value": f"{user_message_count} User messages",
            "probability": engagement_justification,
            "rationale": "Multiple User inputs show active collaboration"
        })
        total_justification += engagement_justification
    
    # Justification 3: Recent search/research activity (-0.18)
    # New external information justifies continuation + synthesis phase
    # Tuned 2025-10-12: -0.15 → -0.18 to protect research→synthesis pattern
    search_tool_count = 0
    for msg in history_messages:
        speaker = msg.name if hasattr(msg, 'name') else "Unknown"
        msg_phase = msg.additional_kwargs.get("phase", 0) if hasattr(msg, 'additional_kwargs') else 0
        if speaker == "Search tool" and msg_phase in recent_phases:
            search_tool_count += 1
    
    if search_tool_count >= 2:
        research_justification = -0.18
        justification_signals.append({
            "factor": "Recent research activity",
            "value": f"{search_tool_count} search results in last 2 phases",
            "probability": research_justification,
            "rationale": "New external information justifies exploration + synthesis"
        })
        total_justification += research_justification
    
    # Justification 4: Low question density (-0.10)
    # Few questions means specialists are providing answers, not asking
    if recent_question_count <= 2:
        answer_mode_score = -0.10
        justification_signals.append({
            "factor": "Answer mode (low questions)",
            "value": f"{recent_question_count} questions in last 2 phases",
            "probability": answer_mode_score,
            "rationale": "Specialists providing answers rather than asking questions"
        })
        total_justification += answer_mode_score
    
    # Apply justification: can reduce probability below phase_score baseline
    # This allows Phase 8+ to continue if justified
    total_probability += total_justification
    
    # Floor at 0.0, ceiling at 1.0
    total_probability = max(0.0, min(total_probability, 1.0))
    
    # ====================================================================
    # Determine stagnation likelihood category (BEFORE DEBUG output)
    # 
    # IMPORTANT: These categories are ONLY for human display purposes.
    # Chair receives the actual continuous total_probability value (0.0-1.0 float)
    # in its prompt. Do NOT use these bins for any logic or computation.
    # ====================================================================
    if total_probability < 0.20:
        likelihood_category = "🟢 LOW (0-20%)"
        threshold_guidance = "HIGH threshold - need clear, obvious stagnation to trigger final phase"
    elif total_probability < 0.40:
        likelihood_category = "🟡 LOW-MODERATE (20-40%)"
        threshold_guidance = "MODERATE-HIGH threshold - need substantial stagnation signals"
    elif total_probability < 0.60:
        likelihood_category = "🟠 MODERATE (40-60%)"
        threshold_guidance = "MODERATE threshold - minor stagnation signals should be considered seriously"
    elif total_probability < 0.75:
        likelihood_category = "🔴 MODERATE-HIGH (60-75%)"
        threshold_guidance = "LOW-MODERATE threshold - even minor hints should trigger stagnation"
    else:
        likelihood_category = "🔴 HIGH (75-100%)"
        threshold_guidance = "LOW threshold - any hint of stagnation should trigger final phase"
    
    # ====================================================================
    # DEBUG: Output stagnation probability computation details
    # ====================================================================
    with _console_output_lock:
        print(f"\n{'='*80}", file=sys.stderr)
        print(f"[DEBUG] STAGNATION PROBABILITY COMPUTATION (Phase {current_phase})", file=sys.stderr)
        print(f"{'='*80}", file=sys.stderr)
        
        # Show state tracking context
        print(f"\nSTATE TRACKING & CONTEXT:", file=sys.stderr)
        print(f"  Current Phase: {current_phase}", file=sys.stderr)
        print(f"  Stagnation Check Phase: Phase {phases_since_check_started + 3} (check #{phases_since_check_started})", file=sys.stderr)
        print(f"  First Check: Phase 4 (stagnation detection starts here)", file=sys.stderr)
        print(f"  Last User Phase: {last_user_phase} (most recent User message)", file=sys.stderr)
        print(f"  User Silence: {user_silence_phases} phases since last User message", file=sys.stderr)
        print(f"  Total User Messages: {user_message_count}", file=sys.stderr)
        print(f"  Recent Phases: {recent_phases} (last 2 phases for analysis)", file=sys.stderr)
        print(f"  Total Conversation Messages: {len(history_messages)}", file=sys.stderr)
        
        # Show the equation
        print(f"\nEQUATION: P(stagnation) = max(0.0, min(Σ(stagnation_signals) + Σ(justification_signals), 1.0))", file=sys.stderr)
        print(f"Where each signal contributes a weighted score based on observable metrics.", file=sys.stderr)
        print(f"Stagnation signals (POSITIVE): Push toward final phase", file=sys.stderr)
        print(f"Justification signals (NEGATIVE): Allow Phase 8+ continuation\n", file=sys.stderr)
        
        # Show raw inputs
        print(f"RAW INPUTS:", file=sys.stderr)
        print(f"  user_silence_phases = {user_silence_phases}", file=sys.stderr)
        print(f"  current_phase = {current_phase}", file=sys.stderr)
        print(f"  last_user_phase = {last_user_phase}", file=sys.stderr)
        print(f"  user_message_count = {user_message_count}", file=sys.stderr)
        print(f"  phases_since_check_started = {phases_since_check_started}", file=sys.stderr)
        print(f"  recent_question_count = {recent_question_count}", file=sys.stderr)
        print(f"  conditional_count = {conditional_count}", file=sys.stderr)
        
        # Show signal computations
        print(f"\nSIGNAL COMPUTATIONS:", file=sys.stderr)
        
        # Signal 1: User silence (DISABLED)
        print(f"  1. User Silence: DISABLED (no user interaction during multi-phase discussion)", file=sys.stderr)
        
        # Signal 2: Phase progression
        if phases_since_check_started >= 1:
            phase_score = min((phases_since_check_started - 1) * 0.15, 0.60)
            print(f"  2. Phase Progression (CAPPED - MODERATE):", file=sys.stderr)
            print(f"     Formula: min((phases_since_check - 1) * 0.15, 0.60)", file=sys.stderr)
            print(f"     Calculation: min(({phases_since_check_started} - 1) * 0.15, 0.60) = {phase_score:.4f}", file=sys.stderr)
            print(f"     Contribution: {phase_score:.4f} ({phase_score*100:.1f}%)", file=sys.stderr)
            print(f"     Schedule: Ph4=0%, Ph5=15%, Ph6=30%, Ph7=45%, Ph8+=60% (CAPPED - content quality drives)", file=sys.stderr)
        else:
            print(f"  2. Phase Progression: 0.0000 (phase < 4)", file=sys.stderr)
        
        # Signal 3: Low user engagement
        if current_phase >= 6 and user_message_count <= 1:
            engagement_score = 0.20
            print(f"  3. Low User Engagement:", file=sys.stderr)
            print(f"     Formula: 0.20 (flat score if phase≥6 AND user_msgs≤1)", file=sys.stderr)
            print(f"     Triggered: phase={current_phase}≥6, msgs={user_message_count}≤1", file=sys.stderr)
            print(f"     Contribution: 0.2000 (20.0%)", file=sys.stderr)
        else:
            print(f"  3. Low User Engagement: 0.0000 (not triggered)", file=sys.stderr)
        
        # Signal 4: Specialist questions
        if recent_question_count >= 5:
            question_score = min(recent_question_count / 20.0, 0.15)
            print(f"  4. Specialist Questions:", file=sys.stderr)
            print(f"     Formula: min(question_count / 20.0, 0.15)", file=sys.stderr)
            print(f"     Calculation: min({recent_question_count} / 20.0, 0.15) = {question_score:.4f}", file=sys.stderr)
            print(f"     Contribution: {question_score:.4f} ({question_score*100:.1f}%)", file=sys.stderr)
        else:
            print(f"  4. Specialist Questions: 0.0000 (count={recent_question_count}<5)", file=sys.stderr)
        
        # Signal 5: Conditional language
        if conditional_count >= 3:
            conditional_score = min(conditional_count / 15.0, 0.06)
            print(f"  5. Conditional Planning:", file=sys.stderr)
            print(f"     Formula: min(conditional_count / 15.0, 0.06)", file=sys.stderr)
            print(f"     Calculation: min({conditional_count} / 15.0, 0.06) = {conditional_score:.4f}", file=sys.stderr)
            print(f"     Contribution: {conditional_score:.4f} ({conditional_score*100:.1f}%)", file=sys.stderr)
        else:
            print(f"  5. Conditional Planning: 0.0000 (count={conditional_count}<3)", file=sys.stderr)
        
        # Show subtotal before justification
        subtotal_before_justification = sum(s['probability'] for s in stagnation_signals)
        print(f"\n  SUBTOTAL (stagnation signals): {subtotal_before_justification:.4f} ({subtotal_before_justification*100:.1f}%)", file=sys.stderr)
        
        # Show justification signals (NEGATIVE - reduce probability)
        print(f"\nJUSTIFICATION SIGNALS (negative contributions):", file=sys.stderr)
        
        # Justification 1: Recent User engagement (CONDITIONAL - only in interactive mode)
        if not interactive_mode:
            print(f"  1. Recent User Response: DISABLED (simple CLI mode - user only provides initial goal)", file=sys.stderr)
        elif user_silence_phases == 0:
            print(f"  1. Recent User Response:", file=sys.stderr)
            print(f"     Formula: -0.30 (user spoke this phase)", file=sys.stderr)
            print(f"     Value: User spoke in Phase {last_user_phase}", file=sys.stderr)
            print(f"     Contribution: -0.3000 (-30.0%)", file=sys.stderr)
        elif user_silence_phases == 1:
            print(f"  1. Recent User Response:", file=sys.stderr)
            print(f"     Formula: -0.15 (user spoke 1 phase ago)", file=sys.stderr)
            print(f"     Value: User spoke in Phase {last_user_phase}", file=sys.stderr)
            print(f"     Contribution: -0.1500 (-15.0%)", file=sys.stderr)
        else:
            print(f"  1. Recent User Response: +0.0000 (user silence={user_silence_phases} phases)", file=sys.stderr)
        
        # Justification 2: High User engagement (CONDITIONAL - only in interactive mode)
        if not interactive_mode:
            print(f"  2. High User Engagement: DISABLED (simple CLI mode - user only provides initial goal)", file=sys.stderr)
        elif user_message_count >= 3:
            print(f"  2. High User Engagement:", file=sys.stderr)
            print(f"     Formula: -0.20 (message_count >= 3)", file=sys.stderr)
            print(f"     Value: {user_message_count} User messages total", file=sys.stderr)
            print(f"     Contribution: -0.2000 (-20.0%)", file=sys.stderr)
        else:
            print(f"  2. High User Engagement: +0.0000 (user_messages={user_message_count}<3)", file=sys.stderr)
        
        # Justification 3: Research activity
        if search_tool_count >= 2:
            print(f"  3. Recent Research Activity:", file=sys.stderr)
            print(f"     Formula: -0.18 (search_count >= 2)", file=sys.stderr)
            print(f"     Value: {search_tool_count} searches in last 2 phases", file=sys.stderr)
            print(f"     Contribution: -0.1800 (-18.0%)", file=sys.stderr)
        else:
            print(f"  3. Recent Research Activity: +0.0000 (searches={search_tool_count}<2)", file=sys.stderr)
        
        # Justification 4: Answer mode
        if recent_question_count <= 2:
            print(f"  4. Answer Mode (low questions):", file=sys.stderr)
            print(f"     Formula: -0.10 (questions <= 2)", file=sys.stderr)
            print(f"     Value: {recent_question_count} questions in last 2 phases", file=sys.stderr)
            print(f"     Contribution: -0.1000 (-10.0%)", file=sys.stderr)
        else:
            print(f"  4. Answer Mode: +0.0000 (questions={recent_question_count}>2)", file=sys.stderr)
        
        print(f"\n  SUBTOTAL (justification): {total_justification:.4f} ({total_justification*100:.1f}%)", file=sys.stderr)
        
        # Show summation
        print(f"\nFULL EQUATION SUMMATION:", file=sys.stderr)
        
        # Build stagnation terms
        stagnation_terms = []
        for signal in stagnation_signals:
            stagnation_terms.append(f"{signal['probability']:.4f}")
        
        # Build justification terms
        justification_terms = []
        for signal in justification_signals:
            justification_terms.append(f"({signal['probability']:.4f})")  # Negative, show in parens
        
        # Show full equation
        if stagnation_terms or justification_terms:
            all_terms = stagnation_terms + justification_terms
            equation_str = " + ".join(all_terms)
            print(f"  P(stagnation) = {equation_str}", file=sys.stderr)
            
            # Show intermediate calculation
            subtotal_stag = sum(s['probability'] for s in stagnation_signals)
            subtotal_just = sum(s['probability'] for s in justification_signals)
            print(f"  P(stagnation) = {subtotal_stag:.4f} + ({subtotal_just:.4f})", file=sys.stderr)
            print(f"  P(stagnation) = {subtotal_stag:.4f} - {abs(subtotal_just):.4f}", file=sys.stderr)
            
            uncapped_total = subtotal_stag + subtotal_just
            print(f"  P(stagnation) = {uncapped_total:.4f} (before bounds)", file=sys.stderr)
            
            # Show bounding
            if uncapped_total > 1.0:
                print(f"  P(stagnation) = min({uncapped_total:.4f}, 1.0) = 1.0000 (capped at ceiling)", file=sys.stderr)
            elif uncapped_total < 0.0:
                print(f"  P(stagnation) = max({uncapped_total:.4f}, 0.0) = 0.0000 (floored at zero)", file=sys.stderr)
        else:
            print(f"  P(stagnation) = 0.0000 (no signals)", file=sys.stderr)
        
        # Show final result
        print(f"\nFINAL STAGNATION PROBABILITY: {total_probability:.4f} ({total_probability*100:.1f}%)", file=sys.stderr)
        
        # Show threshold mapping
        print(f"\nTHRESHOLD MAPPING:", file=sys.stderr)
        print(f"  0.00-0.20 (0-20%):   🟢 LOW → HIGH threshold (need obvious stagnation)", file=sys.stderr)
        print(f"  0.20-0.40 (20-40%):  🟡 LOW-MOD → MODERATE-HIGH threshold", file=sys.stderr)
        print(f"  0.40-0.60 (40-60%):  🟠 MODERATE → MODERATE threshold", file=sys.stderr)
        print(f"  0.60-0.75 (60-75%):  🔴 MOD-HIGH → LOW-MODERATE threshold", file=sys.stderr)
        print(f"  0.75-1.00 (75-100%): 🔴 HIGH → LOW threshold (any hint triggers)", file=sys.stderr)
        print(f"  Current: {likelihood_category}", file=sys.stderr)
        
        # Show weights for tuning
        print(f"\nWEIGHT CONFIGURATION (DYNAMIC CONVERGENCE):", file=sys.stderr)
        print(f"  STAGNATION SIGNALS (positive, push toward final):", file=sys.stderr)
        print(f"    • SILENCE_WEIGHT = DISABLED  (no user interaction during discussion)", file=sys.stderr)
        print(f"    • PHASE_WEIGHT = +0.60 max   (15%/check, caps at Phase 8+ - content quality drives beyond baseline)", file=sys.stderr)
        print(f"    • LOW_ENGAGEMENT_WEIGHT = +0.20  (flat score)", file=sys.stderr)
        print(f"    • MAX_QUESTION_WEIGHT = +0.15 (caps at 20 questions)", file=sys.stderr)
        print(f"    • MAX_CONDITIONAL_WEIGHT = +0.06 (caps at 15 phrases)", file=sys.stderr)
        print(f"  ", file=sys.stderr)
        print(f"  JUSTIFICATION SIGNALS (negative, allow continuation):", file=sys.stderr)
        print(f"    • RECENT_USER_RESPONSE = DISABLED (no user interaction during discussion)", file=sys.stderr)
        print(f"    • RECENT_USER_1PHASE = DISABLED (no user interaction during discussion)", file=sys.stderr)
        print(f"    • HIGH_USER_ENGAGEMENT = DISABLED (no user interaction during discussion)", file=sys.stderr)
        print(f"    • RESEARCH_ACTIVITY = -0.18 (if searches >= 2 in last 2 phases)", file=sys.stderr)
        print(f"    • ANSWER_MODE = -0.10 (if questions <= 2 in last 2 phases)", file=sys.stderr)
        print(f"  ", file=sys.stderr)
        print(f"  MAX JUSTIFICATION = -0.28 (both active signals)", file=sys.stderr)
        print(f"  NET EFFECT: Justification reduces baseline (e.g., 60% - 28% = 32%)", file=sys.stderr)
        print(f"  ", file=sys.stderr)
        print(f"  BASELINE: Phase 8+ reaches 60% baseline (caps - no forced convergence)", file=sys.stderr)
        print(f"  CONVERGENCE: Content quality signals (engagement/questions/conditional) drive final decision", file=sys.stderr)
        print(f"  WITH JUSTIFICATION: Research + answer mode can reduce probability, allowing longer discussions", file=sys.stderr)
        print(f"  TARGET: Dynamic - stagnant discussions end early, productive ones continue naturally", file=sys.stderr)
        print(f"  PHILOSOPHY: Phase provides pressure, content quality determines convergence", file=sys.stderr)
        
        # Show tuning guidance
        print(f"\nTUNING NOTES (for intuitive iteration):", file=sys.stderr)
        print(f"  Observe this output over multiple conversations, then consider:", file=sys.stderr)
        print(f"    • Ending too early? Maybe adjust PHASE_WEIGHT down slightly next time", file=sys.stderr)
        print(f"    • Ending too late? Maybe adjust PHASE_WEIGHT up slightly next time", file=sys.stderr)
        print(f"    • Specific signal misbehaving? Maybe tweak that signal's weight", file=sys.stderr)
        print(f"  ", file=sys.stderr)
        print(f"  Expect minor adjustments only - typically ±3-5% per term per iteration", file=sys.stderr)
        print(f"  No strict thresholds - just observe, discuss, and make small changes", file=sys.stderr)
        print(f"  SEE: ARCHITECTURE.md 'DATA COLLECTION LOG' for tracking observations", file=sys.stderr)
        
        print(f"{'='*80}\n", file=sys.stderr)
        sys.stderr.flush()
    
    # Gather all User messages for context
    user_concerns_xml = "<user_concerns>\n"
    for msg in history_messages:
        speaker = msg.name if hasattr(msg, 'name') else "Unknown"
        if speaker == "User":
            timestamp = msg.additional_kwargs.get("timestamp", datetime.now().astimezone().isoformat(timespec='milliseconds')) if hasattr(msg, 'additional_kwargs') else datetime.now().astimezone().isoformat(timespec='milliseconds')
            msg_phase = msg.additional_kwargs.get("phase", "unknown") if hasattr(msg, 'additional_kwargs') else "unknown"
            content = msg.content
            user_concerns_xml += f'<message><from>User</from><timestamp_iso>{timestamp}</timestamp_iso><phase>{msg_phase}</phase><content>{content}</content></message>\n\n'
    user_concerns_xml += "</user_concerns>"
    
    # Build stagnation detection prompt with full <message> XML format
    # Current synthesis just generated, use current timestamp (with timezone)
    current_timestamp = datetime.now().astimezone().isoformat(timespec='milliseconds')
    
    stagnation_system = """You are Chair, the discussion coordinator analyzing whether the discussion has stagnated."""
    
    # Build formatted signals display
    signals_display = ""
    for signal in stagnation_signals:
        prob_percent = signal['probability'] * 100
        signals_display += f"""
• {signal['factor']}: {signal['value']}
  → Contribution: {prob_percent:.1f}% ({signal['probability']:.3f})
  → {signal['rationale']}
"""
    
    # ====================================================================
    # Build Chair's prompt with CONTINUOUS probability value
    # 
    # CRITICAL: Chair receives the actual total_probability float (0.0-1.0)
    # The category labels are for human readability only - Chair makes decisions
    # based on the precise continuous value, not binned categories.
    # ====================================================================
    user_engagement_status = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPUTED STAGNATION LIKELIHOOD: {total_probability:.1%} {likelihood_category}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This probability is computed from multiple quantitative signals:
{signals_display if signals_display else "• No significant stagnation signals detected\n"}
TOTAL STAGNATION LIKELIHOOD: {total_probability:.3f} ({total_probability:.1%})

INFERRED THRESHOLD GUIDANCE:
{threshold_guidance}

ANALYSIS FRAMEWORK:

1. **Synthesis Evolution** (compare your Phase {current_phase-1} vs Phase {current_phase} syntheses):
   - Do they contain substantially NEW insights, information, or progress?
   - Or are they repackaging the same points with minor elaborations?
   - Are specialists converging on solutions or diverging into more options?

2. **Blocking Indicators** (check for these patterns):
   - Specialists repeatedly asking User for decisions/clarifications
   - Plans contingent on undefined User requirements ("if you...", "pending...")
   - Same questions rephrased across phases without answers
   - Circular discussions without resolution

3. **Progress Indicators** (signs discussion is productive):
   - User actively engaged and answering questions
   - Decisions being made, blockers getting resolved
   - New information from external sources (research, data)
   - Discussion converging toward specifics

CALIBRATED DECISION FRAMEWORK:

Given the computed stagnation likelihood of {total_probability:.1%}, calibrate your judgment:

• If likelihood is HIGH (75-100%):
  → Trigger on ANY hint of stagnation in synthesis comparison
  → Conclude immediately if rehashing same points

• If likelihood is MODERATE-HIGH (60-75%):
  → Trigger if synthesis shows MINOR but clear hints of stagnation
  → Be sensitive to repetition and lack of progress

• If likelihood is MODERATE (40-60%):
  → Trigger if synthesis shows MINOR but definite stagnation signals
  → Balance between allowing exploration and preventing spinning

• If likelihood is LOW-MODERATE (20-40%):
  → Trigger ONLY if synthesis shows SUBSTANTIAL stagnation
  → Allow discussion to continue unless clearly blocked

• If likelihood is LOW (0-20%):
  → Trigger ONLY if synthesis shows CLEAR, OBVIOUS stagnation
  → Strong bias toward continuing productive discussion

Your job: Compare the syntheses objectively, identify any stagnation patterns, then apply the threshold calibration based on the computed {total_probability:.1%} probability to make your decision.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    stagnation_prompt = f"""Based on the User's concerns, User engagement status, your previous synthesis, and your current synthesis, has the conversation STAGNATED?

CONTEXT:
You are analyzing two syntheses you wrote in consecutive phases. Each synthesis is a SUMMARY of an ongoing multi-phase conversation where specialists discuss the User's concerns. Your previous synthesis summarized the discussion up through Phase {current_phase - 1}, and your current synthesis summarized the discussion up through Phase {current_phase}.

{user_concerns_xml}

<previous_synthesis>
<message><from>Chair</from><timestamp_iso>{prev_timestamp}</timestamp_iso><phase>{current_phase - 1}</phase><content>{prev_content}</content></message>
</previous_synthesis>

<current_synthesis>
<message><from>Chair</from><timestamp_iso>{current_timestamp}</timestamp_iso><phase>{current_phase}</phase><content>{current_synthesis}</content></message>
</current_synthesis>

{user_engagement_status}

STAGNATION ANALYSIS:

Comparing Phase {current_phase - 1} synthesis to Phase {current_phase} synthesis:

BLOCKING INDICATORS (weigh severity based on computed probability):

1. **Unanswered Questions Accumulation**
   - Are specialists repeatedly asking the User for decisions or clarifications?
   - Do those questions remain unanswered across phases?
   - Are new artifacts or plans contingent on those unanswered questions?

2. **Conditional Planning Without Foundation**
   - Are specialists building elaborate plans for UNDEFINED requirements?
   - Are most statements prefaced with "if User confirms...", "pending decision on...", "once you decide..."?
   - Are specialists proposing detailed solutions before knowing the actual problem?

3. **Circular Dependency**
   - Are specialists unable to proceed without User input?
   - Yet are they continuing to elaborate on the same blocked topics?
   - Is the discussion going in circles around the same unknowns?

4. **Repetition or Same Questions Rephrased**
   - Are specialists asking variations of the same core questions?
   - Example: Similar questions being asked in different ways without progress toward answers
   - Are they repackaging questions instead of making progress?

5. **Work Plan Stagnation**
   - Are specialists repeating the same commitments across phases without delivery?
   - Example: Phase N: "I'll compile sources on X" → Phase N+1: "I'll compile sources on X" (no delivery)
   - Are specialists making vague statements without concrete action?
   - Example: "We should think about..." → "It would be good to consider..." (no progress)
   - Did specialists commit to producing deliverables but never report back?
   - This pattern indicates work is stalled without forward motion

TRUE PROGRESS INDICATORS (discussion should continue):
- Decisions are being made and assumptions are being stated clearly
- Discussion is CONVERGING on specifics (not diverging into more options)
- Concrete recommendations are emerging (not just more planning)
- New information from external sources (research, data, fresh insights)
- New specialists just brought in who haven't contributed yet
- Active research activity (external searches providing fresh information)
- Specialists completing committed work and delivering results
- Clear progression: "I'll do X" (Phase N) → "Completed X, here are results" (Phase N+1)
- Specialists reporting progress even if work is incomplete: "Completed X and Y, Z pending because [reason]"

DECISION:
Based on the analysis above and the computed stagnation probability, has the discussion STAGNATED?

Remember: You are in Phase {current_phase}.

APPLY THE COMPUTED THRESHOLD GUIDANCE:
{threshold_guidance}

Your decision should be calibrated to this threshold:
- HIGH threshold (0-20%): Only trigger if synthesis comparison shows CLEAR, OBVIOUS stagnation
- MODERATE-HIGH threshold (20-40%): Only trigger if synthesis comparison shows SUBSTANTIAL stagnation
- MODERATE threshold (40-60%): Trigger if synthesis shows minor but definite stagnation signals
- LOW-MODERATE threshold (60-75%): Trigger if synthesis shows even minor hints of stagnation
- LOW threshold (75-100%): Trigger on any hint of stagnation

Respond with ONLY one of these:
<stagnated>yes</stagnated>
OR
<stagnated>no</stagnated>

yes = stagnated (move to final round and provide concluding assessments)
no = still progressing (continue discussion)
"""
    
    # Create LLM instance for stagnation check with phase-specific settings
    llm = get_llm("Chair", config.chair, phase_number=current_phase)
    
    # Build messages
    messages = [
        SystemMessage(content=stagnation_system),
        HumanMessage(content=stagnation_prompt)
    ]
    
    # Invoke LLM
    with _console_output_lock:
        print(yellow(f"[CHAIR] Running stagnation analysis for Phase {current_phase}..."), file=sys.stderr)
        print(yellow(f"[CHAIR] Computed stagnation likelihood: {total_probability:.1%} {likelihood_category}"), file=sys.stderr)
        
        # Show contributing signals for observability
        if stagnation_signals:
            for signal in stagnation_signals:
                print(yellow(f"[CHAIR]   • {signal['factor']}: {signal['value']} → +{signal['probability']:.1%}"), file=sys.stderr)
        else:
            print(yellow(f"[CHAIR]   • No significant signals detected"), file=sys.stderr)
        
        print(yellow(f"[CHAIR] Threshold guidance: {threshold_guidance}"), file=sys.stderr)
        sys.stderr.flush()
    
    try:
        response = llm.invoke(messages)
        stagnation_response = response.content.strip()
        
        # Parse <stagnated>yes/no</stagnated> response
        match = re.search(r'<stagnated>\s*(yes|no)\s*</stagnated>', stagnation_response, re.IGNORECASE)
        
        if match:
            decision = match.group(1).lower()
            
            if decision == "yes":
                # Stagnated - Chair's public message should already explain this
                # No need for a separate Notice - the standard final phase Notice will be added by start_phase
                with _console_output_lock:
                    print(yellow(f"[CHAIR] Stagnation analysis result: STAGNATED (moving to final round)\n"), file=sys.stderr)
                    sys.stderr.flush()
                
                return {"stagnated": True}
            else:
                # Still progressing
                with _console_output_lock:
                    print(yellow(f"[CHAIR] Stagnation analysis result: STILL PROGRESSING (continuing discussion)\n"), file=sys.stderr)
                    sys.stderr.flush()
                
                return {"stagnated": False}
        else:
            # Fallback: check for plain yes/no in response
            if "yes" in stagnation_response.lower():
                # Treat as stagnated - Chair's public message should already explain this
                # No need for a separate Notice - the standard final phase Notice will be added by start_phase
                with _console_output_lock:
                    print(yellow(f"[CHAIR] Stagnation analysis result: STAGNATED (fallback parsing, moving to final round)\n"), file=sys.stderr)
                    sys.stderr.flush()
                
                return {"stagnated": True}
            else:
                # Default to not stagnated
                with _console_output_lock:
                    print(yellow(f"[CHAIR] Stagnation analysis: could not parse response, defaulting to continuing discussion\n"), file=sys.stderr)
                    sys.stderr.flush()
                
                return {"stagnated": False}
    
    except BadRequestError as e:
        # 400 error - OpenAI refused the prompt (likely content policy violation)
        # Log the full context for analysis but don't retry
        with _console_output_lock:
            print(yellow(f"[CHAIR] ❌ Stagnation check REFUSED by OpenAI (400 error)"), file=sys.stderr)
            print(yellow(f"[CHAIR] Error: {e}"), file=sys.stderr)
            print(yellow(f"[CHAIR] This may be a content policy violation."), file=sys.stderr)
            print(yellow(f"[CHAIR] Logging full context to 400s.log for analysis..."), file=sys.stderr)
            print(yellow(f"[CHAIR] Continuing discussion without stagnation detection\n"), file=sys.stderr)
            sys.stderr.flush()
        
        # Log the denied request for analysis
        log_denied_request("Chair (stagnation check)", messages, e)
        
        # Don't block discussion - default to not stagnated
        return {"stagnated": False}
    
    except Exception as e:
        # If stagnation check fails, don't block the discussion
        with _console_output_lock:
            print(yellow(f"[CHAIR] Stagnation check failed with error: {e}"), file=sys.stderr)
            print(yellow(f"[CHAIR] Continuing discussion without stagnation detection\n"), file=sys.stderr)
            sys.stderr.flush()
        
        return {"stagnated": False}


def chair_agent(state: OverallState) -> dict:
    """Chair agent with conditional participation.
    
    Chair only participates when there are specialist responses to synthesize.
    This means:
    - Phase 1: Skip (no specialist responses visible yet)
    - Phase 2+: Participate (specialist responses from Phase 1+ exist to synthesize)
    - Final: Participate (mandatory contributions ensure specialist responses exist)
    
    Chair's responsibilities when participating (Phase 2+):
    - Synthesize what specialists said in that phase
    - Perform on-topic enforcement (all phases)
    - Perform conflict resolution (Phase 3+)
    - Assess realism of concerns raised
    - [Phase 4+] Detect discussion stagnation and trigger final round if stagnated
    
    Important: Chair's SYNTHESIS (summary) is separate from COMPRESSION (filtering).
    - Synthesis: happens Phase 2+ when specialists have contributed
    - Compression: happens at specific points (end of Phase 2, rate-limit-triggered)
    """
    config = get_config()
    
    # Check if Chair has specialist responses to synthesize
    history_messages = state.get("messages", [])
    current_phase = state.get("phase_number", 1)
    is_chair = True
    
    # Phase 1: Chair participates to monitor for duplicate graph paths
    # Chair watches specialist proposals and marks duplicates early before branches form
    # No synthesis needed yet, but duplicate marking is critical
    phase_1_system_addition = ""
    if current_phase == 1:
        # Chair needs special Phase 1 system prompt focusing on duplicate detection
        phase_1_system_addition = """

🔥 PHASE 1 - YOUR SPECIFIC ROLE:

In Phase 1, specialists are providing their independent assessments. Your role is LIMITED but CRITICAL:

**PRIMARY FOCUS: Watch for duplicate graph paths**
- Specialists may independently propose similar graph questions/answers with different wording
- Mark duplicates IMMEDIATELY using `[🧹][canonical path][comment]` syntax
- Keep the first proposed path as canonical, mark later duplicates
- This prevents vote fragmentation before it starts

**DO NOT DO in Phase 1:**
- ❌ Don't synthesize (no synthesis needed - specialists haven't seen each other yet)
- ❌ Don't provide general commentary
- ❌ Don't enforce on-topic (specialists are addressing User's request directly)
- ❌ Don't table debates (no cross-specialist debates in Phase 1)

**ONLY OUTPUT if you spot duplicate graph paths** - otherwise remain silent (pass).

**Example Phase 1 output (ONLY if duplicates detected):**
```
@[All] I notice duplicate graph proposals:
@[Graph][Update][Q:single][What is approach?][A][Phased rollout][🧹][Q:single][What is approach?][A][Phased deployment][Duplicate - "Phased deployment" was proposed first]
```

If no duplicates detected: Simply respond with "I have no further comments at this time" (pass).
"""
    
    # Phase 2+: Count specialist responses to ensure there's material to synthesize
    specialist_count = 0
    
    for msg in history_messages:
        speaker = msg.name if hasattr(msg, 'name') and msg.name else "Unknown"
        msg_phase = msg.additional_kwargs.get("phase", 0) if hasattr(msg, 'additional_kwargs') else 0
        
        # Skip User, Notice, and Chair's own messages
        if speaker in ["User", "Notice", "Chair"]:
            continue
        
        # Count all specialist messages from Phase 1 onwards
        if msg_phase >= 1:
            specialist_count += 1
    
    # If no specialist responses to synthesize (e.g., all passed), skip
    if specialist_count == 0:
        with _console_output_lock:
            print(yellow(f"\n[CHAIR] Skipping Phase {current_phase} - no specialist responses to synthesize"), file=sys.stderr)
            sys.stderr.flush()
        return {"messages": []}  # No-op, don't add Chair message
    
    # Check for mentioned available specialists
    mentioned_available = get_mentioned_available_specialists(state)
    
    # If there are mentioned available specialists, add a Notice for Chair
    additional_notices = []
    if mentioned_available:
        specialist_names = [get_display_name(role) for role in mentioned_available]
        notice_content = f"Notice: @[Chair], the following available specialists were @mentioned in this phase: {', '.join(specialist_names)}. Consider whether to bring them in based on discussion needs."
        notice_msg = AIMessage(
            content=notice_content,
            name="Notice",
            additional_kwargs={"phase": current_phase, "timestamp": datetime.now().astimezone().isoformat(timespec='milliseconds')}
        )
        additional_notices.append(notice_msg)
    
    # Add any notices to state for Chair to see
    modified_state = dict(state)
    if additional_notices:
        modified_state["messages"] = list(state.get("messages", [])) + additional_notices
    
    # Build Chair's system prompt (with Phase 1 addition if applicable)
    chair_system_prompt = CHAIR_SYSTEM + phase_1_system_addition
    
    # Invoke Chair with appropriate system prompt
    # Status message now printed inside agent function just before LLM call
    result = create_agent_func("Chair", chair_system_prompt, config.chair, specialist_count)(modified_state)
    
    # If we added notices, include them in the output
    if additional_notices:
        result_messages = result.get("messages", [])
        result["messages"] = additional_notices + result_messages
    
    # Post-process Chair's response to detect specialist additions
    # Extract Chair's actual message content
    chair_messages = result.get("messages", [])
    if not chair_messages:
        return result  # No messages, return as-is
    
    # Get the Chair's response content (last message, since additional_messages come first)
    chair_message = chair_messages[-1]
    chair_content = chair_message.content if hasattr(chair_message, 'content') else ""
    
    # Detect if Chair is bringing specialists into the room
    added_specialists, notice_messages = detect_specialist_additions(chair_content, state)
    
    # If specialists were added, update state and add Notice messages
    if added_specialists:
        # Update specialist_presence state
        updated_presence = state["specialist_presence"].copy()
        for role_key in added_specialists:
            updated_presence[role_key] = "in"
        
        # Add updated presence to result
        result["specialist_presence"] = updated_presence
        
        # Add Notice messages to the message list
        result["messages"] = chair_messages + notice_messages
    
    # CHECKPOINT BEFORE STAGNATION DETECTION
    # Save checkpoint with clean state before we potentially set final_phase_needed
    # This ensures we can resume from before the final round decision on a second run
    if current_phase >= 4 and not state.get("final_phase_needed", False):
        from .checkpoint import save_checkpoint
        if config.enable_checkpoints:
            # Build checkpoint state with messages up to this point (before stagnation notice)
            checkpoint_state = {**state}
            checkpoint_state["messages"] = state.get("messages", []) + result.get("messages", [])
            checkpoint_state["phase_number"] = current_phase
            checkpoint_state["checkpoint_saved_this_phase"] = True
            save_checkpoint(checkpoint_state)
            result["checkpoint_saved_this_phase"] = True
            
            with _console_output_lock:
                print(f"💾 Checkpoint saved before stagnation check (Phase {current_phase})", file=sys.stderr)
                sys.stderr.flush()
    
    # =============================================================================
    # STAGNATION DETECTION: Phase 4+ - Detect when discussion is rehashing without progress
    # =============================================================================
    # Triggers: Chair detects discussion rehashing same points without new progress
    # Flow: Chair announces decision → Notice announces phase transition (next cycle)
    #
    # CRITICAL FLOW: Chair must publicly announce WHY we're moving to final phase
    # - Chair is the "public face" of decisions (explains reasoning)
    # - Notice is the "announcement system" (declares phase transitions, no explanations)
    #
    # Only run if not already in final phase and phase >= 4
    if current_phase >= 4 and not state.get("final_phase_needed", False):
        stagnation_result = check_discussion_stagnation(state, chair_content, current_phase, config)
        
        if stagnation_result["stagnated"]:
            # Discussion has stagnated - Chair publicly announces the decision
            # Then the standard final phase Notice will be added by start_phase() in the next cycle
            result["final_phase_needed"] = True
            
            # Add Chair's public announcement of the stagnation decision
            # This explains WHY (Chair's role) before Notice announces WHAT phase we're in
            stagnation_announcement = AIMessage(
                content="Based on discussion stagnation analysis, we should move to the final discussion phase to provide concluding assessments.",
                name="Chair",
                additional_kwargs={"phase": current_phase, "timestamp": datetime.now().astimezone().isoformat(timespec='milliseconds')}
            )
            current_messages = result.get("messages", [])
            result["messages"] = current_messages + [stagnation_announcement]
            
            with _console_output_lock:
                print(yellow(f"\n[CHAIR] Stagnation detected in Phase {current_phase} - moving to final round"), file=sys.stderr)
                sys.stderr.flush()
    
    return result


def research_agent(state: OverallState) -> dict:
    config = get_config()
    return create_agent_func("Research specialist", RESEARCH_SYSTEM, config.research)(state)


def engineer_agent(state: OverallState) -> dict:
    config = get_config()
    return create_agent_func("Engineer specialist", ENGINEER_SYSTEM, config.engineer)(state)


def skeptic_agent(state: OverallState) -> dict:
    config = get_config()
    return create_agent_func("Skeptic specialist", SKEPTIC_SYSTEM, config.skeptic)(state)


def context_agent(state: OverallState) -> dict:
    config = get_config()
    return create_agent_func("Context specialist", CONTEXT_SYSTEM, config.context)(state)


def ethicist_agent(state: OverallState) -> dict:
    config = get_config()
    return create_agent_func("Ethicist specialist", ETHICIST_SYSTEM, config.ethicist)(state)


def azuredevopsengineer_agent(state: OverallState) -> dict:
    config = get_config()
    return create_agent_func("Azure DevOps Engineer specialist", AZURE_DEVOPS_ENGINEER_SYSTEM, config.azuredevopsengineer)(state)


def cloudarchitect_agent(state: OverallState) -> dict:
    config = get_config()
    return create_agent_func("Cloud Infrastructure Architect specialist", CLOUD_INFRASTRUCTURE_ARCHITECT_SYSTEM, config.cloudarchitect)(state)


def dbarchitect_agent(state: OverallState) -> dict:
    config = get_config()
    return create_agent_func("Database Architect specialist", DATABASE_ARCHITECT_SYSTEM, config.dbarchitect)(state)


def backendengineer_agent(state: OverallState) -> dict:
    config = get_config()
    return create_agent_func("Backend Engineer specialist", BACKEND_ENGINEER_SYSTEM, config.backendengineer)(state)


def frontendengineer_agent(state: OverallState) -> dict:
    config = get_config()
    return create_agent_func("Frontend Engineer specialist", FRONTEND_ENGINEER_SYSTEM, config.frontendengineer)(state)


def devopsengineer_agent(state: OverallState) -> dict:
    config = get_config()
    return create_agent_func("DevOps Engineer specialist", DEVOPS_ENGINEER_SYSTEM, config.devopsengineer)(state)


def productmanager_agent(state: OverallState) -> dict:
    config = get_config()
    return create_agent_func("Product Manager specialist", PRODUCT_MANAGER_SYSTEM, config.productmanager)(state)


def qaengineer_agent(state: OverallState) -> dict:
    config = get_config()
    return create_agent_func("QA Engineer specialist", QA_ENGINEER_SYSTEM, config.qaengineer)(state)


def technicalwriter_agent(state: OverallState) -> dict:
    config = get_config()
    return create_agent_func("Technical Writer specialist", TECHNICAL_WRITER_SYSTEM, config.technicalwriter)(state)


def hr_agent(state: OverallState) -> dict:
    config = get_config()
    return create_agent_func("HR specialist", HR_SYSTEM, config.hr)(state)


async def invoke_agent_async(agent_func: Callable[[OverallState], dict], state: OverallState, semaphore: asyncio.Semaphore) -> dict:
    """Async wrapper for agent invocation with concurrency control.
    
    The semaphore controls concurrency:
    - For Azure OpenAI: High concurrency (e.g., 15) for parallel execution
    - For Ollama: Concurrency of 1 for sequential execution (prevents VRAM thrashing)
    """
    async with semaphore:
        # Run the synchronous agent function in a thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, agent_func, state)
        return result


async def execute_phase_parallel(state: OverallState) -> dict:
    """Execute agents in a phase with parallel support.
    
    Respects room presence - only executes specialists currently "in" the room
    (from state["agents_remaining"]).
    
    For Azure OpenAI:
    - Non-Chair specialists execute in parallel (max concurrency 15)
    - Chair executes sequentially after all specialists complete
    
    For Ollama:
    - All agents execute sequentially (concurrency=1 to prevent VRAM thrashing)
    - Order from agents_remaining (which maintains AGENT_ROSTER order)
    """
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    
    config = get_config()
    
    # Clean up old search results at the beginning of the phase (once for all agents)
    # This trims verbose <result> tags from Search tool messages that are 2+ phases old
    current_phase = state.get("phase_number", 1)
    messages = state.get("messages", [])
    
    # Debug: count Search tool messages that need trimming (2+ phases old with <result tags)
    messages_needing_trim = {}
    all_msg_names = set()
    for msg in messages:
        msg_name = msg.name if hasattr(msg, 'name') else None
        if msg_name:
            all_msg_names.add(msg_name)
        if msg_name == "Search tool":
            msg_phase = msg.additional_kwargs.get("phase", "unknown") if hasattr(msg, 'additional_kwargs') else "unknown"
            # Only count messages that are 2+ phases old and have <result tags
            if isinstance(msg_phase, int) and current_phase - msg_phase >= 2 and '<result' in msg.content:
                messages_needing_trim[msg_phase] = messages_needing_trim.get(msg_phase, 0) + 1
    
    print(f"[DEBUG] Phase {current_phase} start - All message names in state: {sorted(all_msg_names)}", file=sys.stderr)
    if messages_needing_trim:
        print(f"[DEBUG] Phase {current_phase} start - Search results needing trim: {messages_needing_trim}", file=sys.stderr)
    
    trimmed_messages = []
    for msg in messages:
        msg_phase = msg.additional_kwargs.get("phase", "unknown") if hasattr(msg, 'additional_kwargs') else "unknown"
        msg_name = msg.name if hasattr(msg, 'name') else None
        
        # Only trim Search tool messages that are 2+ phases old (gives specialists 1 full phase to see URLs)
        if msg_name == "Search tool" and isinstance(msg_phase, int) and current_phase - msg_phase >= 2:
            # Check if there are actually <result> tags to trim (not already trimmed)
            # After trimming, the message will have <results> but no <result> children, and will contain '…'
            # CRITICAL: Must check for '…' to avoid re-trimming already trimmed messages
            # This prevents repeated "Trimming search results" debug logs for the same messages
            if '<result' in msg.content and '…' not in msg.content:
                queries_to_trim = re.findall(r'<results\s+query="([^"]*)"', msg.content)
                if queries_to_trim:
                    print(f"[DEBUG] Trimming search results from Phase {msg_phase} (current Phase {current_phase}): {len(queries_to_trim)} result(s) - queries: {queries_to_trim}", file=sys.stderr)
            
            # Trim this message
            msg_content = cleanup_old_search_results(msg.content)
            # Create new message with trimmed content
            if isinstance(msg, HumanMessage):
                new_msg = HumanMessage(content=msg_content, name=msg.name, additional_kwargs=msg.additional_kwargs if hasattr(msg, 'additional_kwargs') else {})
            elif isinstance(msg, AIMessage):
                new_msg = AIMessage(content=msg_content, name=msg.name, additional_kwargs=msg.additional_kwargs if hasattr(msg, 'additional_kwargs') else {})
            elif isinstance(msg, SystemMessage):
                new_msg = SystemMessage(content=msg_content, name=msg.name, additional_kwargs=msg.additional_kwargs if hasattr(msg, 'additional_kwargs') else {})
            else:
                new_msg = msg  # Unknown type, keep as-is
            trimmed_messages.append(new_msg)
        # Only trim ReadURL tool messages that are 2+ phases old (gives specialists 1 full phase to see content)
        elif msg_name == "ReadURL tool" and isinstance(msg_phase, int) and current_phase - msg_phase >= 2:
            # Check if there is actually content to trim (not already trimmed)
            # After trimming, content will be ONLY '…' between the <content> tags
            # Check if content has substantial text (not just the ellipsis marker)
            if '<content' in msg.content:
                # Extract content between <content ...>...</content> tags
                content_match = re.search(r'<content[^>]*>(.*?)</content>', msg.content, re.DOTALL)
                if content_match:
                    inner_content = content_match.group(1).strip()
                    # Only trim if content is NOT just the ellipsis marker
                    if inner_content != '…':
                        urls_to_trim = re.findall(r'<content\s+url="([^"]*)"', msg.content)
                        if urls_to_trim:
                            print(f"[DEBUG] Trimming ReadURL results from Phase {msg_phase} (current Phase {current_phase}): {len(urls_to_trim)} URL(s) - urls: {urls_to_trim}", file=sys.stderr)
            
            # Trim this message
            msg_content = cleanup_old_search_results(msg.content)
            # Create new message with trimmed content
            if isinstance(msg, HumanMessage):
                new_msg = HumanMessage(content=msg_content, name=msg.name, additional_kwargs=msg.additional_kwargs if hasattr(msg, 'additional_kwargs') else {})
            elif isinstance(msg, AIMessage):
                new_msg = AIMessage(content=msg_content, name=msg.name, additional_kwargs=msg.additional_kwargs if hasattr(msg, 'additional_kwargs') else {})
            elif isinstance(msg, SystemMessage):
                new_msg = SystemMessage(content=msg_content, name=msg.name, additional_kwargs=msg.additional_kwargs if hasattr(msg, 'additional_kwargs') else {})
            else:
                new_msg = msg  # Unknown type, keep as-is
            trimmed_messages.append(new_msg)
        else:
            # Keep as-is (not Search/ReadURL tool, or not old enough, or already trimmed)
            trimmed_messages.append(msg)
    
    # Update state with trimmed messages for all agents to use
    state = dict(state)
    state["messages"] = trimmed_messages
    
    # Create semaphore based on provider
    max_concurrency = config.max_concurrency
    semaphore = asyncio.Semaphore(max_concurrency)
    
    # Get agents that should execute this phase from state (respects room presence)
    # start_phase() sets agents_remaining to only "in" specialists + chair
    agents_this_phase = state.get("agents_remaining", [])
    
    # Separate Chair from other specialists
    non_chair_agents = [a for a in agents_this_phase if a != "chair"]
    
    print(f"[DEBUG] Phase {current_phase}: Executing {len(non_chair_agents)} non-Chair specialists: {non_chair_agents}", file=sys.stderr, flush=True)
    
    # Map agent names to their functions
    agent_func_map = {
        "context": context_agent,
        "research": research_agent,
        "engineer": engineer_agent,
        "skeptic": skeptic_agent,
        "ethicist": ethicist_agent,
        "azuredevopsengineer": azuredevopsengineer_agent,
        "cloudarchitect": cloudarchitect_agent,
        "dbarchitect": dbarchitect_agent,
        "backendengineer": backendengineer_agent,
        "frontendengineer": frontendengineer_agent,
        "devopsengineer": devopsengineer_agent,
        "productmanager": productmanager_agent,
        "qaengineer": qaengineer_agent,
        "technicalwriter": technicalwriter_agent,
        "hr": hr_agent,
        "chair": chair_agent,
    }
    
    # Execute non-Chair specialists in parallel (Azure) or sequential (Ollama via semaphore)
    # CRITICAL: All specialists must complete as one atomic group BEFORE Chair executes
    
    # NOTE: "Thinking" notice is now added in start_phase (before this node executes)
    # so TUI sees it immediately before parallel processing starts
    all_messages = []
    
    # Create tasks for all non-Chair specialists
    tasks_list = []
    task_names = []
    for agent_name in non_chair_agents:
        agent_func = agent_func_map[agent_name]
        task = invoke_agent_async(agent_func, state, semaphore)
        tasks_list.append(task)
        task_names.append(agent_name)
    
    # Wait for ALL non-Chair specialists to complete as one atomic group
    # Using asyncio.gather() ensures all tasks complete before proceeding
    specialist_results = await asyncio.gather(*tasks_list)
    
    # Map results back to agent names and collect messages in AGENT_ROSTER order
    specialist_results_dict = dict(zip(task_names, specialist_results))
    
    # Collect specialist messages (before Chair)
    specialist_messages = []
    for agent_name in non_chair_agents:
        result = specialist_results_dict[agent_name]
        if "messages" in result:
            msg_count = len(result["messages"])
            print(f"[DEBUG] Phase {current_phase}: {agent_name} returned {msg_count} message(s)", file=sys.stderr, flush=True)
            specialist_messages.extend(result["messages"])
        else:
            print(f"[DEBUG] Phase {current_phase}: {agent_name} returned NO messages", file=sys.stderr, flush=True)
    
    # Add specialist messages after the thinking notice
    all_messages.extend(specialist_messages)
    
    # Phase-level tool request deduplication: Process Search and ReadURL requests
    # Collect all @[Search] queries and @[ReadURL] URLs from all specialist messages
    # Deduplicate and track which specialists requested each
    search_requests = {}  # query -> [specialist_names]
    readurl_requests = {}  # url -> [specialist_names]
    graph_operations = []  # [(specialist_name, content)]
    
    for msg in specialist_messages:
        if hasattr(msg, 'name') and msg.name:
            specialist_name = msg.name
            content = msg.content if hasattr(msg, 'content') else ""
            
            # Extract search queries
            queries = detect_search_requests(content)
            for query in queries:
                query_normalized = query.strip()
                if query_normalized:
                    if query_normalized not in search_requests:
                        search_requests[query_normalized] = []
                    if specialist_name not in search_requests[query_normalized]:
                        search_requests[query_normalized].append(specialist_name)
            
            # Extract ReadURL URLs
            urls = detect_readurl_requests(content)
            for url in urls:
                url_normalized = url.strip()
                if url_normalized:
                    if url_normalized not in readurl_requests:
                        readurl_requests[url_normalized] = []
                    if specialist_name not in readurl_requests[url_normalized]:
                        readurl_requests[url_normalized].append(specialist_name)
            
            # Extract Graph operations
            graph_requests = detect_graph_requests(content)
            if graph_requests:
                graph_operations.append((specialist_name, content, graph_requests))
    
    # Process unique search queries (deduplicated)
    tool_messages = []
    if search_requests:
        print(f"[DEBUG] Phase {current_phase} - Processing {len(search_requests)} unique search queries", file=sys.stderr)
        for query, requesters in search_requests.items():
            print(f"[DEBUG]   Search query '{query}' requested by: {requesters}", file=sys.stderr)
            search_data = perform_tavily_search(query, config, None)
            formatted_results = format_search_results(search_data, requesters)  # Pass list of requesters
            
            timestamp = datetime.now().astimezone().isoformat(timespec='milliseconds')
            search_message = AIMessage(
                content=formatted_results,
                name="Search tool",
                additional_kwargs={"phase": current_phase, "timestamp": timestamp}
            )
            tool_messages.append(search_message)
    
    # Process unique ReadURL requests (deduplicated)
    if readurl_requests:
        print(f"[DEBUG] Phase {current_phase} - Processing {len(readurl_requests)} unique ReadURL requests", file=sys.stderr)
        for url, requesters in readurl_requests.items():
            print(f"[DEBUG]   ReadURL '{url}' requested by: {requesters}", file=sys.stderr)
            url_data = read_url_with_jina(url, config.jina_api_key, None)
            formatted_content = format_readurl_results(url_data, requesters)  # Pass list of requesters
            
            timestamp = datetime.now().astimezone().isoformat(timespec='milliseconds')
            readurl_message = AIMessage(
                content=formatted_content,
                name="ReadURL tool",
                additional_kwargs={"phase": current_phase, "timestamp": timestamp}
            )
            tool_messages.append(readurl_message)
    
    # Process Graph operations from all specialists
    # Logs @[Graph][Create] and @[Graph][Update] operations to graph.log
    graph_create_operations = []  # Collect Create operations for Chair de-dupe pass
    
    if graph_operations:
        print(f"[DEBUG] Phase {current_phase} - Processing Graph operations from {len(graph_operations)} specialists", file=sys.stderr)
        for specialist_name, content, requests in graph_operations:
            print(f"[DEBUG]   Processing Graph operations from {specialist_name}", file=sys.stderr)
            
            # Collect Create operations that aren't already marked as duplicates
            for req in requests:
                if req.get('operation') == 'Create' and '[🧹]' not in req.get('raw', ''):
                    # Extract path to get vote counts and user thoughts
                    from .graph_tool import extract_path_from_content
                    path = extract_path_from_content(req['raw'].replace('@[Graph][Create]', ''))
                    
                    # Get vote tally from graph_parser analysis
                    vote_count = 0
                    user_thoughts_count = 0
                    
                    # We'll need to analyze graph.log to get current vote counts
                    # For now, just track the path
                    graph_create_operations.append({
                        'specialist': specialist_name,
                        'raw': req['raw'],
                        'content': content,
                        'path': path
                    })
            
            graph_messages = process_graph_operations(
                message_content=content,
                requester_name=specialist_name,
                phase=current_phase
            )
            if graph_messages:
                # Add timestamp and phase to graph response messages
                timestamp = datetime.now().astimezone().isoformat(timespec='milliseconds')
                for msg in graph_messages:
                    msg.additional_kwargs = {"phase": current_phase, "timestamp": timestamp}
                tool_messages.extend(graph_messages)
    
    # Add tool messages to all_messages (before Chair executes)
    all_messages.extend(tool_messages)
    
    # NOW execute Chair (always sequential, goes LAST after all specialists complete)
    # Chair needs to see ALL specialist responses from current phase
    state_with_specialists = dict(state)
    if specialist_messages:
        # Update state with all specialist messages for Chair to synthesize
        state_with_specialists["messages"] = state.get("messages", []) + specialist_messages
    
    # Add tool messages to state for Chair to see
    if tool_messages:
        state_with_specialists["messages"] = state_with_specialists.get("messages", []) + tool_messages
    
    # Chair executes only after all specialists have completed
    chair_result = await invoke_agent_async(chair_agent, state_with_specialists, semaphore)
    
    # Collect Chair's messages
    chair_messages = []
    if "messages" in chair_result:
        chair_messages = chair_result["messages"]
        all_messages.extend(chair_messages)
    
    # CHAIR DE-DUPE PASS: After Chair's normal synthesis, run de-dupe pass on Create operations
    # This happens at the end of each phase to mark duplicate paths WITHIN THE PHASE
    # Scope: Only compares Creates from this phase (specialists ran in parallel, can't see each other)
    if graph_create_operations:
        print(f"\n{'='*80}", file=sys.stderr)
        print(f"🧹 CHAIR DE-DUPE PASS: Reviewing {len(graph_create_operations)} @[Graph][Create] operations from Phase {current_phase}", file=sys.stderr)
        print(f"{'='*80}", file=sys.stderr)
        
        # Analyze current graph state to get vote counts and user thoughts
        from graph_parser import analyze_graph_log
        try:
            nodes, vote_tally, specialist_stats = analyze_graph_log('graph.log')
            
            # Enrich Create operations with vote counts, user thoughts, and user selections
            for op in graph_create_operations:
                path = op.get('path', '')
                if path in vote_tally:
                    op['votes'] = vote_tally[path].get('upvotes', 0)
                    op['downvotes'] = vote_tally[path].get('downvotes', 0)
                else:
                    op['votes'] = 0
                    op['downvotes'] = 0
                
                if path in nodes and 'user_thoughts' in nodes[path]:
                    op['user_thoughts'] = len(nodes[path]['user_thoughts'])
                else:
                    op['user_thoughts'] = 0
                
                # Check for user selections/dismissals on this path
                op['user_selected'] = False
                op['user_dismissed'] = False
                if path in nodes and 'votes' in nodes[path]:
                    for vote_record in nodes[path]['votes']:
                        if vote_record.get('vote') == '✅':
                            op['user_selected'] = True
                        elif vote_record.get('vote') == '❌':
                            op['user_dismissed'] = True
        except Exception as e:
            print(f"Warning: Could not enrich Create operations with vote data: {e}", file=sys.stderr)
            # Add defaults if enrichment failed
            for op in graph_create_operations:
                if 'votes' not in op:
                    op['votes'] = 0
                if 'downvotes' not in op:
                    op['downvotes'] = 0
                if 'user_thoughts' not in op:
                    op['user_thoughts'] = 0
                if 'user_selected' not in op:
                    op['user_selected'] = False
                if 'user_dismissed' not in op:
                    op['user_dismissed'] = False
        
        # Log what we're handing to Chair
        print(f"\nHanding to Chair for review:", file=sys.stderr)
        for i, op in enumerate(graph_create_operations, 1):
            print(f"  {i}. [{op['specialist']}] {op['raw'][:80]}... (👍{op.get('votes', 0)} 👎{op.get('downvotes', 0)} 💭{op.get('user_thoughts', 0)})", file=sys.stderr)
        print(file=sys.stderr)
        
        # Build dedupe prompt with ONLY graph paths (no user context - causes objective contamination)
        dedupe_prompt = CHAIR_DEDUPE_PASS_SYSTEM + "\n\n"
        dedupe_prompt += "# Graph Paths Created This Phase:\n\n"
        for i, op in enumerate(graph_create_operations, 1):
            votes = op.get('votes', 0)
            downvotes = op.get('downvotes', 0)
            thoughts = op.get('user_thoughts', 0)
            user_selected = op.get('user_selected', False)
            user_dismissed = op.get('user_dismissed', False)
            
            # Build state indicators
            state_indicators = f"👍{votes} 👎{downvotes}"
            if user_selected:
                state_indicators += " ✅"
            if user_dismissed:
                state_indicators += " ❌"
            if thoughts > 0:
                state_indicators += f" 💭{thoughts}"
            
            dedupe_prompt += f"{i}. [{op['specialist']}] {op['raw']}\n"
            dedupe_prompt += f"   Current state: {state_indicators}\n"
        
        dedupe_prompt += "\n" + "="*80 + "\n"
        dedupe_prompt += "END OF DATA INPUT\n"
        dedupe_prompt += "="*80 + "\n\n"
        dedupe_prompt += "REMINDER: You are a GRAPH PATH ANALYZER, not a conversational assistant.\n"
        dedupe_prompt += "Your response must be ONLY de-duplication commands or 'No duplicates found.'\n"
        dedupe_prompt += "Do NOT provide any other text.\n\n"
        dedupe_prompt += "Output your de-duplication analysis now:"
        
        # Log de-dupe session to chair-dedupe.log
        dedupe_log_path = "chair-dedupe.log"
        try:
            with open(dedupe_log_path, 'a', encoding='utf-8') as dedupe_log:
                dedupe_log.write(f"\n{'='*80}\n")
                dedupe_log.write(f"PHASE {current_phase} DE-DUPE PASS - {datetime.now().astimezone().isoformat()}\n")
                dedupe_log.write(f"{'='*80}\n\n")
                
                # Section 1: Full LLM prompt sent to Chair
                dedupe_log.write(f"[1] FULL PROMPT SENT TO LLM:\n\n")
                dedupe_log.write(dedupe_prompt)
                dedupe_log.write(f"\n\n{'-'*80}\n\n")
                
                # Section 2: Create operations being reviewed (for quick reference)
                dedupe_log.write(f"[2] CREATE OPERATIONS BEING REVIEWED ({len(graph_create_operations)} total):\n\n")
                for i, op in enumerate(graph_create_operations, 1):
                    dedupe_log.write(f"{i}. [{op['specialist']}] {op['raw']}\n")
                dedupe_log.write(f"\n{'-'*80}\n\n")
        except Exception as e:
            print(f"Warning: Could not write to {dedupe_log_path}: {e}", file=sys.stderr)
        
        # Create temporary state with all messages so far for Chair to see
        state_for_dedupe = dict(state)
        state_for_dedupe["messages"] = state.get("messages", []) + all_messages
        
        # Invoke Chair with de-dupe prompt
        dedupe_agent = create_agent_func("Chair", dedupe_prompt, config.chair)
        dedupe_result = await invoke_agent_async(dedupe_agent, state_for_dedupe, semaphore)
        
        if "messages" in dedupe_result and dedupe_result["messages"]:
            dedupe_messages = dedupe_result["messages"]
            print(f"\nChair de-dupe pass response ({len(dedupe_messages)} message(s)):", file=sys.stderr)
            
            # Log Chair's response and count duplicates found
            duplicates_marked = 0
            for msg in dedupe_messages:
                if hasattr(msg, 'content'):
                    content_preview = msg.content[:200].replace('\n', ' ')
                    print(f"  Chair: {content_preview}{'...' if len(msg.content) > 200 else ''}", file=sys.stderr)
                    duplicates_marked += msg.content.count('[🧹]')
            
            print(f"\n🧹 Duplicates marked by Chair: {duplicates_marked}", file=sys.stderr)
            
            # Log Chair's response to chair-dedupe.log
            try:
                with open(dedupe_log_path, 'a', encoding='utf-8') as dedupe_log:
                    dedupe_log.write(f"[3] RAW LLM RESPONSE FROM CHAIR:\n\n")
                    for msg in dedupe_messages:
                        if hasattr(msg, 'content'):
                            dedupe_log.write(msg.content)
                            dedupe_log.write("\n\n")
                    dedupe_log.write(f"{'-'*80}\n\n")
                    
                    # Section 4: Extract and show @[Graph][Update] operations Chair is broadcasting to room
                    dedupe_log.write(f"[4] GRAPH OPERATIONS CHAIR BROADCAST TO ROOM:\n\n")
                    graph_ops_found = 0
                    for msg in dedupe_messages:
                        if hasattr(msg, 'content'):
                            # Find all @[Graph][Update] operations in Chair's response
                            graph_updates = re.findall(r'@\[Graph\]\[Update\][^\n]+', msg.content)
                            if graph_updates:
                                for update_op in graph_updates:
                                    graph_ops_found += 1
                                    dedupe_log.write(f"  {graph_ops_found}. {update_op}\n")
                    
                    if graph_ops_found == 0:
                        dedupe_log.write("  (None - Chair found no duplicates)\n")
                    
                    dedupe_log.write(f"\n{'-'*80}\n")
                    dedupe_log.write(f"SUMMARY: {duplicates_marked} duplicate(s) marked with [🧹]\n")
                    dedupe_log.write(f"{'='*80}\n\n")
            except Exception as e:
                print(f"Warning: Could not write Chair response to {dedupe_log_path}: {e}", file=sys.stderr)
            
            all_messages.extend(dedupe_messages)
            
            # Process any @[Graph][Update][...][🧹][...] operations from Chair's de-dupe pass
            processed_graph_msgs = []
            for msg in dedupe_messages:
                if hasattr(msg, 'content'):
                    dedupe_graph_msgs = process_graph_operations(
                        message_content=msg.content,
                        requester_name="Chair",
                        phase=current_phase
                    )
                    if dedupe_graph_msgs:
                        # Add proper timestamp and phase to graph tool messages
                        dedupe_timestamp = datetime.now().astimezone().isoformat(timespec='milliseconds')
                        for graph_msg in dedupe_graph_msgs:
                            graph_msg.additional_kwargs = {"phase": current_phase, "timestamp": dedupe_timestamp}
                        
                        processed_graph_msgs.extend(dedupe_graph_msgs)
                        all_messages.extend(dedupe_graph_msgs)
            
            # Log what got added to the room after processing
            try:
                with open(dedupe_log_path, 'a', encoding='utf-8') as dedupe_log:
                    dedupe_log.write(f"[5] MESSAGES ADDED TO ROOM AFTER PROCESSING:\n\n")
                    if processed_graph_msgs:
                        for i, graph_msg in enumerate(processed_graph_msgs, 1):
                            if hasattr(graph_msg, 'content'):
                                dedupe_log.write(f"{i}. [{graph_msg.name if hasattr(graph_msg, 'name') else 'Unknown'}]\n")
                                dedupe_log.write(f"   {graph_msg.content[:300]}{'...' if len(graph_msg.content) > 300 else ''}\n\n")
                    else:
                        dedupe_log.write("  (None - no Graph tool acknowledgment messages generated)\n")
                    dedupe_log.write(f"\n{'='*80}\n\n")
            except Exception as e:
                print(f"Warning: Could not write final section to {dedupe_log_path}: {e}", file=sys.stderr)
        else:
            print(f"\nChair de-dupe pass: No response (Chair may have passed or returned empty)", file=sys.stderr)
            
            # Log "no response" to chair-dedupe.log
            try:
                with open(dedupe_log_path, 'a', encoding='utf-8') as dedupe_log:
                    dedupe_log.write(f"[3] RAW LLM RESPONSE FROM CHAIR:\n\n")
                    dedupe_log.write(f"(No messages returned - Chair may have found no duplicates)\n\n")
                    dedupe_log.write(f"{'-'*80}\n\n")
                    dedupe_log.write(f"[4] GRAPH OPERATIONS CHAIR BROADCAST TO ROOM:\n\n")
                    dedupe_log.write(f"  (None)\n\n")
                    dedupe_log.write(f"{'-'*80}\n")
                    dedupe_log.write(f"SUMMARY: 0 duplicate(s) marked\n")
                    dedupe_log.write(f"{'='*80}\n\n")
            except Exception as e:
                print(f"Warning: Could not write to {dedupe_log_path}: {e}", file=sys.stderr)
        
        print(f"\n{'='*80}", file=sys.stderr)
        print(f"✅ DE-DUPE PASS COMPLETE", file=sys.stderr)
        print(f"{'='*80}\n", file=sys.stderr)
    
    # CRITICAL: Collect Chair's specialist_presence update (if any)
    # Chair may bring new specialists into the room, so we must propagate this state change
    # to the next phase. Without this, added specialists won't appear in agents_remaining.
    chair_presence_update = chair_result.get("specialist_presence")
    
    # Auto-dismiss non-core specialists who responded
    # This happens AFTER Chair's synthesis AND de-dupe pass, so newly added specialists aren't immediately dismissed
    # Create a temporary state with Chair's presence updates applied
    state_for_dismiss = dict(state)
    if chair_presence_update is not None:
        state_for_dismiss["specialist_presence"] = chair_presence_update
    
    # Check all phase messages (specialist + Chair) for mentions
    # Non-core specialists who were mentioned should stay "in" to respond
    dismiss_presence_update, dismiss_notices = auto_dismiss_non_core_specialists(
        specialist_messages,  # Only specialist messages (before Chair)
        state_for_dismiss,    # State with Chair's additions already applied
        chair_messages        # Chair messages to check for mentions (from synthesis, not de-dupe)
    )
    
    # Combine presence updates: Chair's additions first, then auto-dismissals
    specialist_presence_update = None
    if chair_presence_update is not None or dismiss_presence_update is not None:
        # Start with current state or Chair's update
        if chair_presence_update is not None:
            specialist_presence_update = chair_presence_update.copy()
        else:
            specialist_presence_update = state.get("specialist_presence", {}).copy()
        
        # Apply dismissals (these override Chair's additions if there's a conflict)
        if dismiss_presence_update is not None:
            specialist_presence_update.update(dismiss_presence_update)
    
    # Add dismiss notices to messages
    if dismiss_notices:
        all_messages.extend(dismiss_notices)
    
    # Update state with all messages so far
    updated_state = dict(state)
    updated_state["messages"] = state.get("messages", []) + all_messages
    if specialist_presence_update is not None:
        updated_state["specialist_presence"] = specialist_presence_update
    
    # Check if we should apply rate-limit-triggered compression
    if should_compress_after_rate_limit(updated_state):
        print(f"\n{'='*80}", file=sys.stderr)
        print(f"📦 RATE-LIMIT COMPRESSION: Invoking Chair to compress history", file=sys.stderr)
        print(f"{'='*80}\n", file=sys.stderr)
        
        # Add a Notice message explaining compression
        compression_notice = AIMessage(
            content="Notice: Rate limit encountered. Chair is compressing recent discussion to reduce context size.",
            name="Notice",
            additional_kwargs={"phase": state.get("phase_number", 1)}
        )
        all_messages.append(compression_notice)
        updated_state["messages"] = state.get("messages", []) + all_messages
        
        # Invoke Chair with special compression prompt to summarize recent discussion
        # Chair will create a comprehensive summary
        # We'll use the regular create_agent_func but with the compression system prompt
        config = get_config()
        compression_agent = create_agent_func("Chair", CHAIR_RATE_LIMIT_COMPRESSION_SYSTEM, config.chair)
        compression_result = await invoke_agent_async(compression_agent, updated_state, semaphore)
        
        if "messages" in compression_result:
            all_messages.extend(compression_result["messages"])
            updated_state["messages"] = state.get("messages", []) + all_messages
        
        # Mark compression point (index of Chair's compression summary)
        compression_index = len(state.get("messages", [])) + len(all_messages) - 1
        
        print(f"\n{'='*80}", file=sys.stderr)
        print(f"✅ COMPRESSION COMPLETE: Compression point marked at message {compression_index}", file=sys.stderr)
        print(f"{'='*80}\n", file=sys.stderr)
        
        # Reset rate limit flag for next phase
        reset_rate_limit_flag()
        
        # Return with compression marker
        result = {
            "messages": all_messages,
            "agents_remaining": [],
            "last_compression_message_index": compression_index,
        }
        if specialist_presence_update is not None:
            result["specialist_presence"] = specialist_presence_update
        
        # CRITICAL: Propagate final_phase_needed from Chair if stagnation was detected
        if chair_result.get("final_phase_needed"):
            result["final_phase_needed"] = True
        
        return result
    
    # Return all messages (LangGraph's add_messages annotation will merge them)
    # Reset rate limit flag for next phase
    reset_rate_limit_flag()
    
    result = {
        "messages": all_messages,
        "agents_remaining": [],  # All agents completed
    }
    if specialist_presence_update is not None:
        result["specialist_presence"] = specialist_presence_update
    
    # CRITICAL: Propagate final_phase_needed from Chair if stagnation was detected
    if chair_result.get("final_phase_needed"):
        result["final_phase_needed"] = True
    
    return result


def execute_phase_parallel_sync(state: OverallState) -> dict:
    """Synchronous wrapper for execute_phase_parallel.
    
    LangGraph nodes must be synchronous, so we use asyncio.run() to execute
    the async parallel execution and return the result.
    """
    return asyncio.run(execute_phase_parallel(state))


def start_phase(state: OverallState) -> dict:
    """Initialize a new phase."""
    phase_num = state.get("phase_number", 0) + 1
    is_final = state.get("final_phase_needed", False)
    
    # Create a system message to announce the phase to agents
    messages_to_add = []
    
    # Create notice message with real timestamp when submitted (with timezone)
    notice_timestamp = datetime.now().astimezone().isoformat(timespec='milliseconds')
    if is_final:
        phase_message = "Notice: We are starting the final discussion phase. All specialists, please concisely provide your concluding assessment."
    elif phase_num == 1:
        phase_message = "Notice: We are starting discussion phase 1. All specialists, concisely provide your initial independent perspective."
    elif phase_num == 2:
        phase_message = "Notice: We are starting discussion phase 2. All specialists, review what other specialists said and concisely provide your current perspective."
    else:
        phase_message = f"Notice: We are starting discussion phase {phase_num}. All specialists, continue discussion or pass if you have nothing new to add per the guidelines and your perspectives."
    
    # Add notice message first (with phase metadata and submission timestamp)
    notice_msg = AIMessage(
        content=phase_message, 
        name="Notice",
        additional_kwargs={"phase": phase_num, "timestamp": notice_timestamp}
    )
    messages_to_add.append(notice_msg)
    
    # On Phase 1, add the User's question AFTER the notice
    if phase_num == 1:
        user_question = state.get("user_goal", "")
        user_timestamp = datetime.now().astimezone().isoformat(timespec='milliseconds')
        user_msg = AIMessage(
            content=user_question,
            name="User",
            additional_kwargs={"phase": 1, "timestamp": user_timestamp}  # User message is part of Phase 1
        )
        messages_to_add.append(user_msg)
    
    # Calculate token range that specialists will see (Phase 2+)
    # Shows min (most filtered view) to max (least filtered view)
    # This runs at START of phase before specialists contribute
    # Future-proofed for when different specialists may have different visibility
    if phase_num >= 2:
        config = get_config()
        from .config import get_max_input_tokens
        
        current_messages = state.get("messages", [])
        max_input_tokens = get_max_input_tokens(config)
        
        # Calculate minimum (most filtered specialist view)
        # Specialists don't see current phase messages or old search results
        specialist_visible_messages = []
        for msg in current_messages:
            speaker = msg.name if hasattr(msg, 'name') and msg.name else "Unknown"
            msg_phase = msg.additional_kwargs.get("phase", 0) if hasattr(msg, 'additional_kwargs') else 0
            
            # Always show User and Notice
            if speaker in ["User", "Notice"]:
                specialist_visible_messages.append(msg)
            # Filter out current phase (specialists don't see it yet)
            elif msg_phase >= phase_num:
                continue
            # Filter old search results (keep only previous phase)
            elif speaker == "Search tool":
                if msg_phase == phase_num - 1:
                    specialist_visible_messages.append(msg)
            # Keep everything else
            else:
                specialist_visible_messages.append(msg)
        
        # Calculate maximum (Chair's view - includes current phase)
        # At phase start, this equals specialist view (no current messages yet)
        # But calculation is ready for when views diverge
        chair_visible_messages = current_messages
        
        min_tokens = count_tokens_in_messages(specialist_visible_messages)
        max_tokens = count_tokens_in_messages(chair_visible_messages)
        
        # Calculate utilization percentage range
        utilization_percent_min = (min_tokens / max_input_tokens) * 100
        utilization_percent_max = (max_tokens / max_input_tokens) * 100
        
        # =============================================================================
        # TOKEN LIMIT ENFORCEMENT: Two-tier system to manage conversation complexity
        # =============================================================================
        # TIER 1 (80-90%): Force final phase - Chair announces complexity concern, then final phase
        # TIER 2 (≥90%): Hard stop - Chair announces no room for final phase, conversation ends
        #
        # CRITICAL FLOW: Chair must publicly announce WHY we're stopping/transitioning
        # - Chair is the "public face" of decisions (explains token complexity/constraint)
        # - Notice is the "announcement system" (announces phase transition or end, no explanation)
        #
        # Implementation: Return immediately with ONLY Chair in agents_remaining, flags set
        # - Chair will see token_limit_triggered or token_limit_hard_stop in state
        # - Chair explains the constraint in their response
        # - Next cycle: Notice announces either final phase or conversation end
        #
        # Skip enforcement if already in final phase or final phase is pending
        if utilization_percent_min >= 80.0 and not is_final and not state.get("final_phase_needed", False):
            
            # TIER 1: 80-90% - Force final phase (Chair announces, then final phase happens)
            if utilization_percent_min < 90.0:
                print(f"\n{'='*80}", file=sys.stderr)
                print(f"⚠️  TOKEN LIMIT ENFORCEMENT: {utilization_percent_min:.1f}% - {utilization_percent_max:.1f}% exceeds 80% threshold", file=sys.stderr)
                print(f"🎯 FORCING FINAL PHASE: @[Chair] will announce transition to final phase", file=sys.stderr)
                print(f"{'='*80}\n", file=sys.stderr)
                sys.stderr.flush()
                
                # Mark that final phase is needed - Chair will see this and announce the transition
                # Then the next phase will be the actual final phase
                return {
                    "phase_number": phase_num,  # Continue with current phase number
                    "agents_remaining": ["chair"],  # ONLY Chair speaks to announce transition
                    "messages": messages_to_add,  # Include normal phase messages
                    "continue_discussion": True,  # Continue to final phase after Chair announces
                    "final_phase_needed": True,  # Signal to Chair that this is a transition announcement
                    "token_limit_triggered": True,  # Signal that this was triggered by token limits
                    "checkpoint_saved_this_phase": False,
                }
            
            # TIER 2: >= 90% - Stop completely (Chair announces hard stop, no room for final phase)
            else:
                print(f"\n{'='*80}", file=sys.stderr)
                print(f"🛑 STOPPING: Token usage ({utilization_percent_min:.1f}% - {utilization_percent_max:.1f}%) exceeds 90% threshold", file=sys.stderr)
                print(f"❌ No room for final phase - @[Chair] will announce conversation end", file=sys.stderr)
                print(f"{'='*80}\n", file=sys.stderr)
                sys.stderr.flush()
                
                # Chair will speak to announce the hard stop, then conversation ends
                return {
                    "phase_number": phase_num,  # Continue with current phase number
                    "agents_remaining": ["chair"],  # ONLY Chair speaks to announce hard stop
                    "messages": messages_to_add,  # Include normal phase messages
                    "continue_discussion": False,  # STOP after Chair announces
                    "final_phase_needed": False,
                    "token_limit_hard_stop": True,  # Signal to Chair that this is a hard stop announcement
                    "checkpoint_saved_this_phase": False,
                }
        
        # Always add a Notice with conversation complexity range (continuous feedback)
        # Shows range to accommodate future different specialist views
        # Note: Target 80% as signal to move to final (leaves ~20% for final round synthesis)
        token_notice_timestamp = datetime.now().astimezone().isoformat(timespec='milliseconds')
        notice_content = f"Notice: Current conversation complexity is between {utilization_percent_min:.1f}% and {utilization_percent_max:.1f}%. The conversation should conclude before reaching 80%."
        
        token_notice_msg = AIMessage(
            content=notice_content,
            name="Notice",
            additional_kwargs={"phase": phase_num, "timestamp": token_notice_timestamp}
        )
        messages_to_add.append(token_notice_msg)
        
        # Log to console for human operator
        print(f"[TOKENS] Phase {phase_num}: {min_tokens:,} - {max_tokens:,} tokens ({utilization_percent_min:.1f}% - {utilization_percent_max:.1f}%)", file=sys.stderr)
        sys.stderr.flush()
    
    # Get only active specialists (those "in" the room)
    active_specialists = get_active_specialists(state)
    
    # Add Chair at the end (conditional participation logic unchanged)
    agents_for_phase = active_specialists + ["chair"]
    
    # CRITICAL: Add "thinking" notice BEFORE execute_phase starts
    # This ensures TUI displays it IMMEDIATELY before parallel processing
    # BUT: Skip if TUI just added one (when user cleared last "?" and auto-resumed)
    non_chair_specialists = [agent for agent in agents_for_phase if agent != "chair"]
    should_add_thinking_notice = False
    
    if non_chair_specialists:
        # Check if last message is already a thinking notice for this phase
        existing_messages = state.get("messages", [])
        last_msg = existing_messages[-1] if existing_messages else None
        is_duplicate_thinking = (
            last_msg and 
            hasattr(last_msg, 'name') and last_msg.name == "Notice" and
            hasattr(last_msg, 'content') and "are thinking" in last_msg.content and "🧠" in last_msg.content and
            hasattr(last_msg, 'additional_kwargs') and last_msg.additional_kwargs.get("phase") == phase_num
        )
        
        if not is_duplicate_thinking:
            should_add_thinking_notice = True
            specialist_display_names = [get_display_name(agent_name) for agent_name in non_chair_specialists]
            # Format names with @[...] for colorization in TUI
            specialist_mentions = [f"@[{name}]" for name in specialist_display_names]
            thinking_notice = f"{format_name_list(specialist_mentions)} are thinking... 🧠"
            
            thinking_timestamp = datetime.now().astimezone().isoformat(timespec='milliseconds')
            thinking_msg = AIMessage(
                content=f"Notice: {thinking_notice}\n",  # Add newline for visual separation
                name="Notice",
                additional_kwargs={"phase": phase_num, "timestamp": thinking_timestamp}
            )
            messages_to_add.append(thinking_msg)
            
            # Also print to stderr for debugging
            print(f"Notice: {thinking_notice}", file=sys.stderr, flush=True)
        else:
            print(f"[DEBUG] Skipping duplicate thinking notice for Phase {phase_num} (already added by TUI)", file=sys.stderr, flush=True)
    
    result = {
        "phase_number": phase_num,
        # Agent execution order: active specialists + Chair (always LAST)
        "agents_remaining": agents_for_phase,
        "messages": messages_to_add,
        "checkpoint_saved_this_phase": False,  # Reset flag for this phase
    }
    
    # DON'T clear final_phase_needed here - agents need to see it!
    # We'll clear it in check_continuation after the final phase completes
    if is_final:
        result["final_phase_done"] = True
        # Keep final_phase_needed=True so agents can see it during the pass
    
    return result


def check_continuation(state: OverallState) -> dict:
    """Check if discussion should continue based on last phase."""
    # Get messages from the last phase
    phase_num = state.get("phase_number", 1)
    all_messages = state.get("messages", [])
    
    # Need at least one full phase before checking
    if len(all_messages) < 6:
        return {"continue_discussion": True, "final_phase_needed": False}
    
    # If this was already the final phase, we're done
    # Clear final_phase_needed flag and stop discussion
    if state.get("final_phase_done", False):
        return {"continue_discussion": False, "final_phase_needed": False, "final_phase_done": False}
    
    # Look at last N messages (the most recent phase) - inferred from AGENT_ROSTER
    num_specialists = len(AGENT_ROSTER)
    recent_messages = all_messages[-num_specialists:] if len(all_messages) >= num_specialists else all_messages
    
    # Count how many agents said "no further comments" in this phase
    pass_count = 0
    for msg in recent_messages:
        content = msg.content.lower()
        if "no further comments" in content or "nothing to add" in content or len(content) < 30:
            pass_count += 1
    
    # Trigger final phase if ALL specialists explicitly passed (natural consensus)
    if pass_count == num_specialists:
        print(f"[INFO] All specialists passed in phase {phase_num}, triggering FINAL PHASE", file=sys.stderr)
        return {"continue_discussion": True, "final_phase_needed": True}
    
    # Otherwise continue with regular phases
    # CRITICAL: Preserve final_phase_needed if it was already set by stagnation detection
    # Don't overwrite it with False!
    final_needed = state.get("final_phase_needed", False)
    return {"continue_discussion": True, "final_phase_needed": final_needed}