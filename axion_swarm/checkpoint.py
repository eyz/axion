"""Checkpoint and resume functionality for conversation state."""

import json
import os
import sys
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage


def compute_config_checksum() -> str:
    """Compute a checksum of the current agent roster and prompts.
    
    This ensures checkpoints are only loaded if the agent configuration
    (roster, role descriptions, and prompts) matches exactly. If the code
    changes (e.g., adding/removing agents, changing prompts), the checksum
    will differ and the checkpoint will be rejected.
    
    Returns:
        SHA256 hex digest of the configuration
    """
    from .agents import AGENT_ROSTER
    from .config import DEFAULT_CORE_TEAM
    from .prompts import (
        ROLE_DESCRIPTIONS,
        CHAIR_SYSTEM,
        CONTEXT_SYSTEM,
        RESEARCH_SYSTEM,
        ENGINEER_SYSTEM,
        SKEPTIC_SYSTEM,
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
        BASE_INSTRUCTION,
    )
    
    # Collect all configuration data
    config_data = {
        "roster": AGENT_ROSTER,
        "default_core_team": DEFAULT_CORE_TEAM,
        "role_descriptions": ROLE_DESCRIPTIONS,
        "base_instruction": BASE_INSTRUCTION,
        "prompts": {
            "chair": CHAIR_SYSTEM,
            "context": CONTEXT_SYSTEM,
            "research": RESEARCH_SYSTEM,
            "engineer": ENGINEER_SYSTEM,
            "skeptic": SKEPTIC_SYSTEM,
            "ethicist": ETHICIST_SYSTEM,
            "azuredevopsengineer": AZURE_DEVOPS_ENGINEER_SYSTEM,
            "cloudarchitect": CLOUD_INFRASTRUCTURE_ARCHITECT_SYSTEM,
            "dbarchitect": DATABASE_ARCHITECT_SYSTEM,
            "backendengineer": BACKEND_ENGINEER_SYSTEM,
            "frontendengineer": FRONTEND_ENGINEER_SYSTEM,
            "devopsengineer": DEVOPS_ENGINEER_SYSTEM,
            "productmanager": PRODUCT_MANAGER_SYSTEM,
            "qaengineer": QA_ENGINEER_SYSTEM,
            "technicalwriter": TECHNICAL_WRITER_SYSTEM,
            "hr": HR_SYSTEM,
        }
    }
    
    # Serialize to JSON with sorted keys for deterministic output
    config_json = json.dumps(config_data, sort_keys=True, ensure_ascii=False)
    
    # Compute SHA256 hash
    return hashlib.sha256(config_json.encode('utf-8')).hexdigest()


def get_checkpoint_path() -> Path:
    """Get the checkpoint file path from environment or use default."""
    checkpoint_file = os.getenv("CHECKPOINT_FILE", ".axion_checkpoint.json")
    return Path(checkpoint_file)


def serialize_message(msg: BaseMessage) -> Dict[str, Any]:
    """Serialize a LangChain message to a JSON-compatible dict."""
    msg_dict = {
        "content": msg.content,
        "type": msg.__class__.__name__,
    }
    
    # Add name if present
    if hasattr(msg, 'name') and msg.name:
        msg_dict["name"] = msg.name
    
    # Add additional_kwargs if present
    if hasattr(msg, 'additional_kwargs') and msg.additional_kwargs:
        msg_dict["additional_kwargs"] = msg.additional_kwargs
    
    return msg_dict


def deserialize_message(msg_dict: Dict[str, Any]) -> BaseMessage:
    """Deserialize a dict back to a LangChain message."""
    msg_type = msg_dict.get("type", "HumanMessage")
    content = msg_dict.get("content", "")
    name = msg_dict.get("name")
    additional_kwargs = msg_dict.get("additional_kwargs", {})
    
    # Create the appropriate message type
    if msg_type == "HumanMessage":
        msg = HumanMessage(content=content, additional_kwargs=additional_kwargs)
    elif msg_type == "AIMessage":
        msg = AIMessage(content=content, additional_kwargs=additional_kwargs)
    elif msg_type == "SystemMessage":
        msg = SystemMessage(content=content, additional_kwargs=additional_kwargs)
    else:
        # Default to HumanMessage for unknown types
        msg = HumanMessage(content=content, additional_kwargs=additional_kwargs)
    
    # Set name if present
    if name:
        msg.name = name
    
    return msg


def save_checkpoint(state: Dict[str, Any], checkpoint_path: Optional[Path] = None) -> None:
    """Save conversation state to a checkpoint file atomically.
    
    Uses atomic write (write to temp, then rename) and fsync to ensure data is
    fully written to disk before proceeding. This ensures checkpoint integrity
    even if the program crashes or is interrupted.
    
    Args:
        state: The conversation state to save
        checkpoint_path: Optional path to checkpoint file (uses default if None)
    """
    if checkpoint_path is None:
        checkpoint_path = get_checkpoint_path()
    
    # Compute configuration checksum
    config_checksum = compute_config_checksum()
    
    # Get runtime config options that affect conversation behavior
    from .agents import get_config
    config = get_config()
    
    # Serialize the state (with timezone)
    checkpoint_data = {
        "timestamp": datetime.now().astimezone().isoformat(),
        "config_checksum": config_checksum,
        "phase_number": state.get("phase_number", 1),
        "user_goal": state.get("user_goal", ""),
        "agents_remaining": state.get("agents_remaining", []),
        "continue_discussion": state.get("continue_discussion", True),
        "final_phase_needed": state.get("final_phase_needed", False),
        "final_phase_done": state.get("final_phase_done", False),
        "specialist_presence": state.get("specialist_presence", {}),
        "last_compression_message_index": state.get("last_compression_message_index", -1),
        "rate_limit_compression_pending": state.get("rate_limit_compression_pending", False),
        "messages": [serialize_message(msg) for msg in state.get("messages", [])],
        "runtime_config": {
            "compress_history_after_phase3": config.compress_history_after_phase3,
            "provider": config.provider,
        },
    }
    
    # Atomic write: write to temp file, fsync, then rename
    # This ensures either the old checkpoint or new checkpoint exists, never partial data
    temp_path = checkpoint_path.with_suffix('.tmp')
    
    try:
        # Write to temp file
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
            f.flush()  # Flush Python buffers
            os.fsync(f.fileno())  # Ensure data is written to disk
        
        # Atomic rename (overwrites existing checkpoint if present)
        # On POSIX systems (Linux/Mac), this is atomic
        temp_path.replace(checkpoint_path)
        
        # Fsync the parent directory to ensure the rename is persisted
        # (This is important for crash consistency on some filesystems)
        parent_fd = os.open(checkpoint_path.parent, os.O_RDONLY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
        
        print(f"💾 Checkpoint saved and synced to disk: {checkpoint_path} (Phase {checkpoint_data['phase_number']})", file=sys.stderr, flush=True)
    
    except Exception as e:
        # Clean up temp file if something went wrong
        if temp_path.exists():
            temp_path.unlink()
        raise RuntimeError(f"Failed to save checkpoint: {e}") from e


def load_checkpoint(checkpoint_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Load conversation state from a checkpoint file.
    
    Verifies that the checkpoint's configuration checksum matches the current
    code. If the roster or prompts have changed, the checkpoint is rejected.
    
    Args:
        checkpoint_path: Optional path to checkpoint file (uses default if None)
    
    Returns:
        The deserialized state dict, or None if checkpoint doesn't exist or is incompatible
    """
    if checkpoint_path is None:
        checkpoint_path = get_checkpoint_path()
    
    if not checkpoint_path.exists():
        return None
    
    # Read and deserialize
    with open(checkpoint_path, 'r', encoding='utf-8') as f:
        checkpoint_data = json.load(f)
    
    # Verify configuration checksum
    current_checksum = compute_config_checksum()
    checkpoint_checksum = checkpoint_data.get("config_checksum")
    
    if checkpoint_checksum != current_checksum:
        print(f"⚠️  Checkpoint configuration mismatch!", flush=True)
        print(f"   Checkpoint was created with a different agent roster or prompts.", flush=True)
        print(f"   Checkpoint checksum: {checkpoint_checksum[:16]}...", flush=True)
        print(f"   Current checksum:    {current_checksum[:16]}...", flush=True)
        print(f"   The checkpoint cannot be used and will be ignored.\n", flush=True)
        return None
    
    # Check runtime config (warning only - not fatal)
    from .agents import get_config
    config = get_config()
    checkpoint_runtime_config = checkpoint_data.get("runtime_config", {})
    
    if checkpoint_runtime_config:
        # Check compression setting
        saved_compression = checkpoint_runtime_config.get("compress_history_after_phase3")
        if saved_compression is not None and saved_compression != config.compress_history_after_phase3:
            print(f"⚠️  Runtime config differs from checkpoint:", flush=True)
            print(f"   compress_history_after_phase3: saved={saved_compression}, current={config.compress_history_after_phase3}", flush=True)
            print(f"   Conversation will continue with CURRENT config setting.\n", flush=True)
        
        # Check provider setting
        saved_provider = checkpoint_runtime_config.get("provider")
        if saved_provider is not None and saved_provider != config.provider:
            print(f"⚠️  Provider differs from checkpoint:", flush=True)
            print(f"   provider: saved={saved_provider}, current={config.provider}", flush=True)
            print(f"   Conversation will continue with CURRENT provider.\n", flush=True)
    
    # Reconstruct state
    state = {
        "phase_number": checkpoint_data.get("phase_number", 1),
        "user_goal": checkpoint_data.get("user_goal", ""),
        "agents_remaining": checkpoint_data.get("agents_remaining", []),
        "continue_discussion": checkpoint_data.get("continue_discussion", True),
        "final_phase_needed": checkpoint_data.get("final_phase_needed", False),
        "final_phase_done": checkpoint_data.get("final_phase_done", False),
        "last_compression_message_index": checkpoint_data.get("last_compression_message_index", -1),
        "rate_limit_compression_pending": checkpoint_data.get("rate_limit_compression_pending", False),
        "messages": [deserialize_message(msg_dict) for msg_dict in checkpoint_data.get("messages", [])],
    }
    
    # Handle specialist_presence (may not exist in old checkpoints)
    if "specialist_presence" in checkpoint_data:
        state["specialist_presence"] = checkpoint_data["specialist_presence"]
    else:
        # Migrate old checkpoint: initialize specialist_presence for all specialists
        from .config import initialize_specialist_presence
        state["specialist_presence"] = initialize_specialist_presence()
        print(f"⚠️  Old checkpoint format detected - initialized specialist_presence with default core team\n", flush=True)
    
    timestamp = checkpoint_data.get("timestamp", "unknown")
    phase = state["phase_number"]
    msg_count = len(state["messages"])
    
    print(f"✅ Checkpoint loaded: {checkpoint_path}", flush=True)
    print(f"   Phase: {phase}, Messages: {msg_count}, Saved: {timestamp}", flush=True)
    print(f"   Config checksum: {current_checksum[:16]}... (matches)\n", flush=True)
    
    return state


def delete_checkpoint(checkpoint_path: Optional[Path] = None) -> bool:
    """Delete the checkpoint file.
    
    Args:
        checkpoint_path: Optional path to checkpoint file (uses default if None)
    
    Returns:
        True if file was deleted, False if it didn't exist
    """
    if checkpoint_path is None:
        checkpoint_path = get_checkpoint_path()
    
    if checkpoint_path.exists():
        checkpoint_path.unlink()
        print(f"🗑️  Checkpoint deleted: {checkpoint_path}\n", flush=True)
        return True
    
    return False


def checkpoint_exists(checkpoint_path: Optional[Path] = None) -> bool:
    """Check if a checkpoint file exists.
    
    Args:
        checkpoint_path: Optional path to checkpoint file (uses default if None)
    
    Returns:
        True if checkpoint exists, False otherwise
    """
    if checkpoint_path is None:
        checkpoint_path = get_checkpoint_path()
    
    return checkpoint_path.exists()

