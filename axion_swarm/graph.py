"""Phase-based LangGraph workflow for agent collaboration."""

import sys
from typing import Literal
from langgraph.graph import StateGraph, END
from .state import OverallState
from .agents import (
    AGENT_ROSTER,
    chair_agent,
    research_agent,
    engineer_agent,
    skeptic_agent,
    context_agent,
    ethicist_agent,
    azuredevopsengineer_agent,
    cloudarchitect_agent,
    dbarchitect_agent,
    backendengineer_agent,
    frontendengineer_agent,
    devopsengineer_agent,
    productmanager_agent,
    qaengineer_agent,
    technicalwriter_agent,
    hr_agent,
    start_phase,
    check_continuation,
    execute_phase_parallel_sync,
    get_config,
)
from .checkpoint import save_checkpoint


def route_next_agent(state: OverallState) -> Literal["context", "research", "engineer", "skeptic", "ethicist", "azuredevopsengineer", "cloudarchitect", "dbarchitect", "backendengineer", "frontendengineer", "devopsengineer", "productmanager", "qaengineer", "technicalwriter", "hr", "chair", "check_continuation"]:
    """Route to next agent in the phase or check continuation."""
    remaining = state.get("agents_remaining", [])
    
    if not remaining:
        return "check_continuation"
    
    return remaining[0]


def update_remaining_agents(agent_name: str):
    """Create a function that removes an agent from the remaining list."""
    def updater(state: OverallState) -> dict:
        remaining = state.get("agents_remaining", [])
        if agent_name in remaining:
            remaining = [a for a in remaining if a != agent_name]
        return {"agents_remaining": remaining}
    return updater


def save_checkpoint_node(state: OverallState) -> dict:
    """Save checkpoint after phase completes, before starting next phase.
    
    This ensures the checkpoint is atomically written and flushed to disk
    before proceeding to the next phase. If the program crashes or is
    interrupted, we can resume from this checkpoint.
    
    SKIP if checkpoint was already saved this phase (e.g., before stagnation detection).
    """
    config = get_config()
    
    # Skip if checkpoint was already saved this phase (before stagnation check)
    if state.get("checkpoint_saved_this_phase", False):
        print(f"💾 Skipping redundant checkpoint (already saved before stagnation check)", file=sys.stderr)
        return {"checkpoint_saved_this_phase": False}  # Reset flag for next phase
    
    if config.enable_checkpoints:
        save_checkpoint(state)
    
    return {}  # No state changes


def route_continuation(state: OverallState) -> Literal["start_phase", "__end__"]:
    """Decide whether to start a new phase or end."""
    if state.get("continue_discussion", True):
        return "start_phase"
    return "__end__"


def create_swarm_graph():
    """Create the phase-based discussion graph with parallel execution support.
    
    This graph supports two execution modes:
    - Azure OpenAI: Parallel execution (specialists run concurrently)
    - Ollama: Sequential execution (concurrency=1 via semaphore)
    """
    config = get_config()
    workflow = StateGraph(OverallState)
    
    # Use parallel execution approach for both providers
    # (Semaphore controls whether it's truly parallel or sequential)
    
    # Add nodes
    workflow.add_node("start_phase", start_phase)
    workflow.add_node("execute_phase", execute_phase_parallel_sync)
    workflow.add_node("check_continuation", check_continuation)
    workflow.add_node("save_checkpoint", save_checkpoint_node)
    
    # Start with first phase
    workflow.set_entry_point("start_phase")
    
    # After starting phase, execute all agents (parallel/sequential based on config)
    workflow.add_edge("start_phase", "execute_phase")
    
    # After executing all agents, check continuation
    workflow.add_edge("execute_phase", "check_continuation")
    
    # After checking continuation, save checkpoint (atomic, fsynced to disk)
    # This ensures we can resume from this point if interrupted
    workflow.add_edge("check_continuation", "save_checkpoint")
    
    # After saving checkpoint, either start new phase or end
    workflow.add_conditional_edges(
        "save_checkpoint",
        route_continuation,
        {
            "start_phase": "start_phase",
            "__end__": END,
        }
    )
    
    print(f"[GRAPH] Provider: {config.provider}, Max Concurrency: {config.max_concurrency}", file=sys.stderr)
    if config.parallel_execution:
        print(f"[GRAPH] Using parallel execution (Azure OpenAI mode)", file=sys.stderr)
    else:
        print(f"[GRAPH] Using sequential execution (Ollama mode - concurrency=1)", file=sys.stderr)
    
    return workflow.compile()
