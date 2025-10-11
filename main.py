#!/usr/bin/env python3
"""Run the Axion Swarm - Phase-based Natural Language Collaboration."""

import os
import re
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
from axion_swarm import create_swarm_graph, OverallState
from axion_swarm.colors import light_green, light_blue, cyan, white, yellow, LIGHT_GREEN, LIGHT_BLUE, LIGHT_PURPLE, RED, RESET, WHITE, DARK_GREEN, DARK_GREY, LIGHT_GREY
from axion_swarm.checkpoint import load_checkpoint, delete_checkpoint, checkpoint_exists
from axion_swarm.prompts import (
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

load_dotenv()


def highlight_mentions(text: str, state: dict = None) -> str:
    """Highlight @[...] mentions in light green text.
    
    - @[User] appears in light blue
    - @[Specialists in room] appear in light purple
    - @[Specialists available but not in room] appear in red
    - @[Search][query] - @[Search] in light blue, [query] in white
    - <result>...</result> - content inside result tags appears in white
    - XML attribute values:
      - url="..." and title="..." appear in dark grey
      - query="..." appears in white
      - answer="..." and requester="..." appear in dark green
    
    Returns text with embedded color codes while the rest remains in light green.
    """
    from axion_swarm.agents import find_role_key_by_display_name
    
    # First handle XML attribute values - color them based on attribute name
    # CRITICAL: Match XML-encoded attribute values (may contain &quot;, &amp;, &lt;, &gt;)
    # This regex handles nested quotes that are XML-encoded as &quot;
    def replace_attribute(match):
        attr_name = match.group(1)
        attr_value = match.group(2)
        # Different colors for different attribute types
        if attr_name == 'query':
            color = WHITE  # Query in white for emphasis
        else:
            color = DARK_GREY  # Other attributes (url, title, requester) in dark grey (metadata)
        # Attribute name and equals in light green, value in specified color, then back to light green
        # Note: @mentions in requester values will be re-colored by mention handler later
        return f'{LIGHT_GREEN}{attr_name}="{RESET}{color}{attr_value}{RESET}{LIGHT_GREEN}"'
    
    # Replace all attribute="value" patterns (in XML tags)
    # Pattern matches attribute values that may contain XML entities (&quot;, &amp;, &lt;, &gt;)
    # (?:[^"&]|&(?:quot|amp|lt|gt);)* matches:
    #   - [^"&] = any char except quote or ampersand
    #   - &(?:quot|amp|lt|gt); = XML entities
    text = re.sub(r'(\w+)="((?:[^"&]|&(?:quot|amp|lt|gt);)*)"', replace_attribute, text)
    
    # Then handle <answer>...</answer> tags - color content white (primary content), tags stay light green
    def replace_answer(match):
        content = match.group(1)
        # Opening tag in light green, content in white (main answer), closing tag in light green
        return f'{LIGHT_GREEN}<answer>{WHITE}{content}{RESET}{LIGHT_GREEN}</answer>'
    
    # Replace all <answer>...</answer> patterns
    text = re.sub(r'<answer>(.*?)</answer>', replace_answer, text, flags=re.DOTALL)
    
    # Then handle <result>...</result> tags - color content light grey (supporting evidence), tags stay light green
    def replace_result(match):
        # Group 1 is the attributes (already colored), group 2 is the content
        attributes = match.group(1)
        content = match.group(2)
        # Opening tag in light green, content in light grey (supporting evidence - brighter), closing tag in light green
        # Note: attributes already include color codes and end with LIGHT_GREEN, so > will be light green
        return f'{LIGHT_GREEN}<result{attributes}>{LIGHT_GREY}{content}{RESET}{LIGHT_GREEN}</result>'
    
    # Replace all <result ...>...</result> patterns (with or without attributes)
    text = re.sub(r'<result([^>]*)>(.*?)</result>', replace_result, text, flags=re.DOTALL)
    
    # Then handle @[Search][query] pattern specially
    def replace_search(match):
        query = match.group(1)
        # @[Search] in light blue, query in white (brackets stay light green)
        return f'{LIGHT_BLUE}@[Search]{RESET}{LIGHT_GREEN}[{WHITE}{query}{RESET}{LIGHT_GREEN}]{RESET}{LIGHT_GREEN}'
    
    # Replace @[Search][...] patterns
    text = re.sub(r'@\[Search\]\[([^\]]+)\]', replace_search, text, flags=re.IGNORECASE)
    
    # Then handle regular @[...] mentions
    def replace_mention(match):
        import html
        mention = match.group(0)
        
        # Extract name from @[Name] and decode any XML entities
        name = mention[2:-1]  # Remove @[ and ]
        decoded_name = html.unescape(name)
        
        # Special cases: User, tool references
        if decoded_name == 'User':
            # User mentions in light blue
            return f'{LIGHT_BLUE}{mention}{RESET}{LIGHT_GREEN}'
        elif decoded_name in ['Search tool', 'ReadURL tool', 'Search', 'ReadURL']:
            # Tool citations (when specialists reference tool results) in light blue
            # Handles both @[Search tool] and @[Search], @[ReadURL tool] and @[ReadURL]
            return f'{LIGHT_BLUE}{mention}{RESET}{LIGHT_GREEN}'
        
        # Check if this is a known specialist name (including Chair)
        role_key = find_role_key_by_display_name(decoded_name)
        if role_key:
            # This is a valid specialist mention
            if state:
                presence = state.get("specialist_presence", {})
                if presence.get(role_key) == "in":
                    # In room: purple
                    return f'{LIGHT_PURPLE}{mention}{RESET}{LIGHT_GREEN}'
                elif presence.get(role_key) == "available":
                    # Available but not in room: red
                    return f'{RED}{mention}{RESET}{LIGHT_GREEN}'
            
            # Default to purple if no state available
            return f'{LIGHT_PURPLE}{mention}{RESET}{LIGHT_GREEN}'
        
        # Not a known specialist, User, or tool - return unchanged (don't colorize)
        # This handles cases like @[A-Za-z0-9.-] from web content
        return mention
    
    # Find and replace all @[...] patterns (except Search which was already handled)
    return re.sub(r'@\[[^\]]+\]', replace_mention, text)


def display_persona_prompts():
    """Display all specialist personas and their system prompts at startup."""
    # Import the base prompts to show unique parts only
    from axion_swarm.prompts import (
        CHAIR_SYSTEM_BASE,
        CONTEXT_SYSTEM_BASE,
        RESEARCH_SYSTEM_BASE,
        ENGINEER_SYSTEM_BASE,
        SKEPTIC_SYSTEM_BASE,
        ETHICIST_SYSTEM_BASE,
        AZURE_DEVOPS_ENGINEER_SYSTEM_BASE,
        CLOUD_INFRASTRUCTURE_ARCHITECT_SYSTEM_BASE,
        DATABASE_ARCHITECT_SYSTEM_BASE,
        BACKEND_ENGINEER_SYSTEM_BASE,
        FRONTEND_ENGINEER_SYSTEM_BASE,
        DEVOPS_ENGINEER_SYSTEM_BASE,
        PRODUCT_MANAGER_SYSTEM_BASE,
        QA_ENGINEER_SYSTEM_BASE,
        TECHNICAL_WRITER_SYSTEM_BASE,
        HR_SYSTEM_BASE,
        ROLE_DESCRIPTIONS,
        generate_specialist_roster,
    )
    
    personas = [
        ("Context", "context", CONTEXT_SYSTEM_BASE),
        ("Research", "research", RESEARCH_SYSTEM_BASE),
        ("Engineer", "engineer", ENGINEER_SYSTEM_BASE),
        ("Skeptic", "skeptic", SKEPTIC_SYSTEM_BASE),
        ("Ethicist", "ethicist", ETHICIST_SYSTEM_BASE),
        ("Azure DevOps Engineer", "azuredevopsengineer", AZURE_DEVOPS_ENGINEER_SYSTEM_BASE),
        ("Cloud Infrastructure Architect", "cloudarchitect", CLOUD_INFRASTRUCTURE_ARCHITECT_SYSTEM_BASE),
        ("Database Architect", "dbarchitect", DATABASE_ARCHITECT_SYSTEM_BASE),
        ("Backend Engineer", "backendengineer", BACKEND_ENGINEER_SYSTEM_BASE),
        ("Frontend Engineer", "frontendengineer", FRONTEND_ENGINEER_SYSTEM_BASE),
        ("DevOps Engineer", "devopsengineer", DEVOPS_ENGINEER_SYSTEM_BASE),
        ("Product Manager", "productmanager", PRODUCT_MANAGER_SYSTEM_BASE),
        ("QA Engineer", "qaengineer", QA_ENGINEER_SYSTEM_BASE),
        ("Technical Writer", "technicalwriter", TECHNICAL_WRITER_SYSTEM_BASE),
        ("HR", "hr", HR_SYSTEM_BASE),
        ("Chair", "chair", CHAIR_SYSTEM_BASE),
    ]
    
    print(f"\n{'='*80}", file=sys.stderr)
    print("# 🤖 AXION SWARM - SPECIALIST PERSONAS", file=sys.stderr)
    print(f"{'='*80}\n", file=sys.stderr)
    
    # First, show the common BASE_INSTRUCTION that all specialists share
    print(f"{'─'*80}", file=sys.stderr)
    print("COMMON INSTRUCTION (SHARED BY ALL SPECIALISTS)", file=sys.stderr)
    print(f"{'─'*80}", file=sys.stderr)
    # Show BASE_INSTRUCTION with a real example roster (excluding Context as an example)
    example_roster = generate_specialist_roster(exclude_role_key="context")
    print(BASE_INSTRUCTION.format(
        display_name="[Specialist Name]",
        specialist_roster=example_roster
    ), file=sys.stderr)
    print(file=sys.stderr)
    
    print(f"{'='*80}", file=sys.stderr)
    print("# INDIVIDUAL SPECIALIST PERSONAS (UNIQUE PARTS)", file=sys.stderr)
    print(f"{'='*80}\n", file=sys.stderr)
    
    # Now show each specialist's unique persona + role description
    for i, (name, role_key, base_prompt) in enumerate(personas, 1):
        print(f"{'─'*80}", file=sys.stderr)
        print(f"SPECIALIST {i}/{len(personas)}: {name.upper()}", file=sys.stderr)
        print(f"{'─'*80}", file=sys.stderr)
        
        # Get the first-person role description
        role_info = ROLE_DESCRIPTIONS.get(role_key, {})
        role_description = role_info.get("first_person", "")
        
        # Insert role description right after "You are [Name]." line
        if role_description:
            lines = base_prompt.split('\n', 1)
            if len(lines) > 1:
                print(lines[0], file=sys.stderr)  # "You are [Name]."
                print(f"\nYour role in this discussion: {role_description}", file=sys.stderr)
                print(lines[1], file=sys.stderr)  # Rest of the base prompt
            else:
                print(base_prompt, file=sys.stderr)
                print(f"\nYour role in this discussion: {role_description}", file=sys.stderr)
        else:
            print(base_prompt, file=sys.stderr)
        
        print(file=sys.stderr)  # Blank line after each persona
    
    print(f"{'='*80}", file=sys.stderr)
    print("# END OF PERSONA DEFINITIONS", file=sys.stderr)
    print(f"{'='*80}\n", file=sys.stderr)


def display_initial_room_composition():
    """Display the initial room composition at startup."""
    from axion_swarm.config import get_core_team
    from axion_swarm.agents import AGENT_ROSTER, get_display_name
    
    core_team = get_core_team()
    
    # Get display names for core team (in the room)
    core_display = [get_display_name(role) for role in core_team]
    
    # Get display names for available specialists
    available = [get_display_name(role) for role in AGENT_ROSTER 
                 if role != "chair" and role not in core_team]
    
    print(f"\n{'='*80}", file=sys.stderr)
    print("# 🏢 INITIAL ROOM COMPOSITION", file=sys.stderr)
    print(f"{'='*80}\n", file=sys.stderr)
    
    print(f"{'─'*80}", file=sys.stderr)
    print("CORE TEAM (In the Room)", file=sys.stderr)
    print(f"{'─'*80}", file=sys.stderr)
    print("These specialists are actively participating from the start:\n", file=sys.stderr)
    for specialist in core_display:
        print(f"  • {specialist}", file=sys.stderr)
    print(file=sys.stderr)
    
    if available:
        print(f"{'─'*80}", file=sys.stderr)
        print("AVAILABLE SPECIALISTS", file=sys.stderr)
        print(f"{'─'*80}", file=sys.stderr)
        print("These specialists can be brought in by Chair when needed:\n", file=sys.stderr)
        for specialist in available:
            print(f"  • {specialist}", file=sys.stderr)
        print(file=sys.stderr)
    
    print(f"{'─'*80}", file=sys.stderr)
    print("Chair can bring additional specialists into the discussion as needed.", file=sys.stderr)
    print(f"{'─'*80}", file=sys.stderr)


def create_initial_state(user_goal: str) -> OverallState:
    """Create a fresh initial state for a new discussion.
    
    Args:
        user_goal: The user's discussion topic
    
    Returns:
        Fresh initial state
    """
    # Clean up user input (remove extra quotes if present)
    user_goal = user_goal.strip().strip('"').strip("'")
    
    from axion_swarm.config import initialize_specialist_presence
    
    return {
        "messages": [],
        "user_goal": user_goal,
        "phase_number": 0,
        "agents_remaining": [],
        "continue_discussion": True,
        "final_phase_needed": False,
        "final_phase_done": False,
        "specialist_presence": initialize_specialist_presence(),  # Initialize room presence
        "last_compression_message_index": -1,  # No compression yet
        "rate_limit_compression_pending": False,  # No pending compression
    }


def run_discussion(initial_state: OverallState):
    """Run the phase-based discussion from a given initial state.
    
    Args:
        initial_state: The starting state (either fresh or from checkpoint)
    """
    # Check if debug mode is enabled
    debug_mode = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
    
    # Create graph
    graph = create_swarm_graph()
    
    # Run discussion
    current_phase = initial_state.get("phase_number", 0)
    final_state = initial_state
    conversation_start_time = datetime.now()  # Track when conversation starts
    
    try:
        # Set very high recursion limit for local LLMs (no practical limit)
        config = {"recursion_limit": 10000}
        for output in graph.stream(initial_state, config):
            # Track the final state
            for node_output in output.values():
                if node_output and "messages" in node_output:
                    final_state = {**final_state, **node_output}
            for node_name, node_output in output.items():
                # DEBUG: Print what we received (only when DEBUG=true)
                if debug_mode:
                    print(f"[DEBUG] Node: {node_name}, Has output: {node_output is not None}, Keys: {list(node_output.keys()) if node_output else 'N/A'}", file=sys.stderr, flush=True)
                    if node_output and "messages" in node_output:
                        print(f"[DEBUG] Messages count: {len(node_output['messages'])}, First message speaker: {node_output['messages'][0].name if node_output['messages'] and hasattr(node_output['messages'][0], 'name') else 'unknown'}", file=sys.stderr, flush=True)
                
                # Handle checkpoint save - prompt user to continue (BEFORE empty check)
                # save_checkpoint returns empty dict, so must check before skipping empty nodes
                if node_name == "save_checkpoint":
                    # Only prompt for phase 3+ (not phases 1-2, and not final phase)
                    completed_phase = final_state.get("phase_number", 0)
                    is_final_phase = final_state.get("final_phase_needed", False) or final_state.get("final_phase_done", False)
                    
                    if completed_phase >= 3 and not is_final_phase:
                        sys.stderr.write("\n⏸️ Press ENTER to continue to next phase (or Ctrl+C to stop): ")
                        sys.stderr.flush()
                        try:
                            input()
                        except KeyboardInterrupt:
                            print("\n\n🛑 Discussion stopped by user.", file=sys.stderr)
                            return
                    continue
                
                # Skip nodes that return None or empty
                if not node_output:
                    continue
                    
                # Track phase number
                if node_name == "start_phase":
                    current_phase = node_output.get("phase_number", current_phase)
                    # Don't continue - we want to process the Notice message below
                
                # Skip other utility nodes
                if node_name.startswith("update_") or node_name == "check_continuation":
                    continue
                
                # Print messages in chat-room format
                if "messages" in node_output and node_output["messages"]:
                    # Add newline before first message (after DEBUG output) for readability
                    if node_name == "start_phase":
                        sys.stdout.write("\n")
                        sys.stdout.flush()
                    
                    chair_status_printed = False
                    for msg in node_output["messages"]:
                        speaker = msg.name if hasattr(msg, 'name') else node_name
                        
                        # Print Chair status BEFORE Chair's first message (after specialists have been shown)
                        if speaker == "Chair" and not chair_status_printed and node_name == "execute_phase":
                            # Count non-Chair specialist messages that came before this
                            specialist_count = sum(
                                1 for m in node_output["messages"]
                                if hasattr(m, 'name') and m.name not in ["Chair", "Notice", "User", "Search tool"]
                            )
                            phase_num = final_state.get("phase_number", current_phase)
                            print(yellow(f"[CHAIR] Participating in Phase {phase_num}; {specialist_count} specialist response(s) to synthesize"), file=sys.stderr)
                            sys.stderr.flush()
                            chair_status_printed = True
                        
                        # Notice messages need timestamps added
                        if speaker == "Notice":
                            # Retrieve stored timestamp from message
                            stored_timestamp_iso = msg.additional_kwargs.get("timestamp", datetime.now().astimezone().isoformat(timespec='milliseconds'))
                            # Convert ISO timestamp to human-readable local timezone format
                            dt_object = datetime.fromisoformat(stored_timestamp_iso)
                            timestamp = dt_object.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " " + dt_object.astimezone().strftime("%Z")
                            # Extract "Notice:" prefix from content to colorize separately
                            if msg.content.startswith("Notice:"):
                                notice_content = msg.content[7:].strip()  # Remove "Notice:" and leading whitespace
                                content_with_highlights = highlight_mentions(notice_content, final_state)
                                print(f"{white(f'[{timestamp}]')} {cyan('Notice:')} {light_green(content_with_highlights)}\n", flush=True)
                            else:
                                # Fallback if format changes
                                content_with_highlights = highlight_mentions(msg.content, final_state)
                                print(f"{white(f'[{timestamp}]')} {light_green(content_with_highlights)}\n", flush=True)
                        # User messages
                        elif speaker == "User":
                            # Retrieve stored timestamp from message
                            stored_timestamp_iso = msg.additional_kwargs.get("timestamp", datetime.now().astimezone().isoformat(timespec='milliseconds'))
                            # Convert ISO timestamp to human-readable local timezone format
                            dt_object = datetime.fromisoformat(stored_timestamp_iso)
                            timestamp = dt_object.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " " + dt_object.astimezone().strftime("%Z")
                            content_with_highlights = highlight_mentions(msg.content, final_state)
                            print(f"{white(f'[{timestamp}]')} {cyan('User:')} {light_green(content_with_highlights)}\n", flush=True)  # Timestamp white, speaker cyan, content light green
                        # Search tool messages
                        elif speaker == "Search tool":
                            import html
                            # Retrieve stored timestamp or generate if missing
                            stored_timestamp_iso = msg.additional_kwargs.get("timestamp", datetime.now().astimezone().isoformat(timespec='milliseconds'))
                            # Convert ISO timestamp to human-readable local timezone format
                            dt_object = datetime.fromisoformat(stored_timestamp_iso)
                            timestamp = dt_object.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " " + dt_object.astimezone().strftime("%Z")
                            # CRITICAL ORDER: Colorize BEFORE decoding HTML entities
                            # 1. Colorize XML-encoded content (regex expects &quot;, &amp;, etc.)
                            # 2. Then decode for human display (color codes preserved)
                            # This prevents nested quotes from breaking colorization
                            content_with_highlights = highlight_mentions(msg.content, final_state)
                            # Dual-audience architecture: LLMs receive XML-encoded text (e.g., &amp;, &lt;)
                            # for valid XML parsing, but humans see decoded text for natural readability.
                            # Decode HTML/XML entities for human display: &amp; → &, &lt; → <, &quot; → ", etc.
                            decoded_content = html.unescape(content_with_highlights)
                            # Use light blue for Search tool (distinct from specialists)
                            print(f"{white(f'[{timestamp}]')} {light_blue('Search tool:')} {light_green(decoded_content)}\n", flush=True)
                        else:
                            # Retrieve stored timestamp from message
                            stored_timestamp_iso = msg.additional_kwargs.get("timestamp", datetime.now().astimezone().isoformat(timespec='milliseconds'))
                            # Convert ISO timestamp to human-readable local timezone format
                            dt_object = datetime.fromisoformat(stored_timestamp_iso)
                            timestamp = dt_object.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " " + dt_object.astimezone().strftime("%Z")
                            
                            # Handle triple-backtick blocks for structured content
                            if '```' in msg.content:
                                # Split on triple backticks
                                parts = msg.content.split('```')
                                formatted_parts = []
                                
                                for i, part in enumerate(parts):
                                    if i % 2 == 0:
                                        # Outside backticks - collapse whitespace
                                        collapsed = part.replace('\n', ' ').replace('\r', ' ')
                                        collapsed = re.sub(r'\s+', ' ', collapsed).strip()
                                        if collapsed:
                                            formatted_parts.append(collapsed)
                                    else:
                                        # Inside backticks - preserve formatting, add indentation
                                        if part.strip():
                                            # Add each line with indentation for readability
                                            lines = part.strip().split('\n')
                                            formatted_parts.append('\n    ' + '\n    '.join(lines))
                                
                                content_for_display = '\n'.join(formatted_parts)
                            else:
                                # No backticks - collapse all whitespace (current behavior)
                                content_for_display = msg.content.replace('\n', ' ').replace('\r', ' ')
                                content_for_display = re.sub(r'\s+', ' ', content_for_display).strip()
                            
                            # Format specialist response in chat-room style with timestamp
                            # Speaker name already includes "specialist" suffix
                            # Highlight @mentions: User in blue, specialists in purple (in room) or red (available)
                            content_with_highlights = highlight_mentions(content_for_display, final_state)
                            print(f"{white(f'[{timestamp}]')} {cyan(f'{speaker} said:')} {light_green(content_with_highlights)}\n", flush=True)  # Timestamp white, speaker cyan, content light green
        
    except Exception as e:
        print(yellow(f"\n## ❌ Error\n"), file=sys.stderr)
        print(yellow(f"**Error:** {e}\n"), file=sys.stderr)
        import traceback
        traceback.print_exc()


def main():
    """Main entry point."""
    # Display all persona prompts at startup
    display_persona_prompts()
    
    # Display initial room composition
    display_initial_room_composition()
    
    # Now show the welcome header and prompt for input
    print(f"\n{'='*80}", file=sys.stderr)
    print("# 🤖 Axion Swarm - Multi-Agent Discussion System", file=sys.stderr)
    print(f"{'='*80}\n", file=sys.stderr)
    
    # Check if checkpoint exists
    if checkpoint_exists():
        print("📂 Checkpoint file found!", file=sys.stderr)
        sys.stderr.write("Resume from checkpoint? (y/n): ")
        sys.stderr.flush()
        resume = input().strip().lower()
        
        if resume in ('y', 'yes'):
            # Load checkpoint and resume (returns None if incompatible)
            checkpoint_state = load_checkpoint()
            if checkpoint_state:
                print(f"✅ Resuming from Phase {checkpoint_state['phase_number']}", file=sys.stderr)
                print(f"{'='*80}", file=sys.stderr)
                run_discussion(checkpoint_state)
                return
            else:
                # Checkpoint was incompatible or corrupted - delete it and start fresh
                print("❌ Checkpoint is incompatible with current code.", file=sys.stderr)
                delete_checkpoint()
                print("   Starting fresh conversation\n", file=sys.stderr)
        else:
            # Delete checkpoint and start fresh
            delete_checkpoint()
            print("🗑️  Starting fresh conversation\n", file=sys.stderr)
    
    # Prompt for discussion topic
    sys.stderr.write("Enter your discussion topic: ")
    sys.stderr.flush()
    user_goal = input().strip()
    
    if not user_goal:
        print("No goal provided. Exiting.", file=sys.stderr)
        return
    
    print()  # Blank line after user input
    
    # Create fresh initial state and run
    initial_state = create_initial_state(user_goal)
    run_discussion(initial_state)


if __name__ == "__main__":
    main()