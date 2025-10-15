"""State for the Axion Swarm - Phase-based discussion."""

from typing import Annotated, TypedDict
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage


class OverallState(TypedDict):
    """Shared state for phase-based discussions."""
    messages: Annotated[list[BaseMessage], add_messages]
    user_goal: str
    phase_number: int
    agents_remaining: list[str]  # Agents who haven't spoken this phase
    continue_discussion: bool
    final_phase_needed: bool
    final_phase_done: bool
    specialist_presence: dict[str, str]  # Specialist room presence: {"context": "in", "cloud": "available", ...}
    last_compression_message_index: int  # Index of last compression point (Chair summary)
    rate_limit_compression_pending: bool  # True if we need to do rate-limit compression
    checkpoint_saved_this_phase: bool  # True if checkpoint was saved before stagnation detection (skip regular checkpoint)
    interactive_mode: bool  # True if running in interactive TUI mode (enables User engagement signals in stagnation detection)