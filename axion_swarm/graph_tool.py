"""Graph tool - Collaborative semantic knowledge construction (PROTOTYPE).

This is a STUB implementation while we observe usage patterns before building the full backend.
Specialists can use @[Graph] syntax to express structured thinking.

OPERATIONS:
- @[Graph][Create] - Propose new Q->A paths (must not already exist)
- @[Graph][Update] - Vote on, extend, or add rationale to existing paths
"""

import re
import os
import sys
from datetime import datetime, timezone
from typing import List, Set
from langchain_core.messages import AIMessage

# Global set tracking all created paths (for Create vs Update validation)
_created_paths: Set[str] = set()


def load_existing_paths_from_log(log_path: str = "graph.log") -> Set[str]:
    """Load all existing graph paths from graph.log.
    
    This populates _created_paths with all paths that have been created
    so we can validate Create (must not exist) vs Update (must exist).
    
    Returns:
        Set of normalized path strings
    """
    global _created_paths
    
    if not os.path.exists(log_path):
        return set()
    
    paths = set()
    
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or 'Graph][Update]' not in line and 'Graph][Create]' not in line:
                    continue
                
                # Extract the path from the line
                # Pattern: @[Graph][Create/Update][path components...]
                match = re.search(r'@\[Graph\]\[(?:Create|Update)\](.+)$', line)
                if match:
                    path_content = match.group(1)
                    # Extract normalized path (before vote markers)
                    path = extract_path_from_content(path_content)
                    if path:
                        paths.add(path)
    
    except Exception as e:
        print(f"Warning: Could not load paths from {log_path}: {e}", file=sys.stderr)
    
    _created_paths = paths
    return paths


def extract_path_from_content(content: str) -> str:
    """Extract normalized path from bracket content (before vote markers).
    
    Args:
        content: The content after @[Graph][Create] or @[Graph][Update]
        
    Returns:
        Normalized path string like [Q:single][text][A][text]
    """
    # Parse brackets character by character
    bracket_contents = []
    i = 0
    while i < len(content):
        if content[i] == '[':
            depth = 1
            j = i + 1
            while j < len(content) and depth > 0:
                if content[j] == '[':
                    depth += 1
                elif content[j] == ']':
                    depth -= 1
                j += 1
            if depth == 0:
                bracket_contents.append(content[i+1:j-1])
                i = j
            else:
                i += 1
        else:
            i += 1
    
    # Build path until we hit vote markers
    vote_markers = ['👍', '👎', '✅', '❌', '➖', '🧹']
    path_parts = []
    
    i = 0
    while i < len(bracket_contents):
        item = bracket_contents[i]
        
        if item in vote_markers:
            break
        
        if item.startswith('Q:') or item.startswith('A:') or item == 'A':
            path_parts.append(f"[{item}]")
            
            # Check if next item is text
            if i + 1 < len(bracket_contents):
                next_item = bracket_contents[i + 1]
                if (next_item not in vote_markers and 
                    not next_item.startswith('Q:') and 
                    not next_item.startswith('A:') and 
                    next_item != 'A'):
                    # Normalize text for comparison
                    normalized = normalize_text(next_item)
                    path_parts.append(f"[{normalized}]")
                    i += 1
        
        i += 1
    
    return ''.join(path_parts)


def normalize_text(text: str) -> str:
    """Normalize text for duplicate detection (same as graph_parser.py)."""
    # Replace various dash/hyphen characters with standard hyphen
    text = text.replace('‑', '-')  # NON-BREAKING HYPHEN
    text = text.replace('‐', '-')  # HYPHEN
    text = text.replace('–', '-')  # EN DASH
    text = text.replace('—', '-')  # EM DASH
    # Replace various space characters
    text = text.replace('\u00A0', ' ')  # NO-BREAK SPACE
    text = text.replace('\u2009', ' ')  # THIN SPACE
    # Normalize quotes
    text = text.replace('"', '"').replace('"', '"')  # Smart quotes
    text = text.replace(''', "'").replace(''', "'")  # Smart apostrophes
    return text


def get_existing_paths_summary(max_paths: int = 50) -> str:
    """Get a concise summary of existing graph paths for specialist context.
    
    Returns a formatted string listing existing paths that specialists can @[Graph][Update].
    Limits to most recent max_paths to avoid overwhelming the context.
    
    Args:
        max_paths: Maximum number of paths to include in summary
        
    Returns:
        Formatted string with existing paths or empty string if no paths exist
    """
    global _created_paths
    
    if not _created_paths:
        load_existing_paths_from_log()
    
    if not _created_paths:
        return ""
    
    # Get most recent paths (simple approach - just take from set)
    paths_list = list(_created_paths)
    
    if len(paths_list) == 0:
        return ""
    
    # Limit to max_paths
    if len(paths_list) > max_paths:
        paths_list = paths_list[:max_paths]
        truncated = True
    else:
        truncated = False
    
    summary = "\n**EXISTING GRAPH PATHS** (use @[Graph][Update] to vote on these):\n\n"
    for path in paths_list:
        summary += f"- {path}\n"
    
    if truncated:
        summary += f"\n(Showing {max_paths} of {len(_created_paths)} paths - use @[Graph][Create] for new paths, @[Graph][Update] for existing)\n"
    else:
        summary += f"\n(Total: {len(_created_paths)} paths exist)\n"
    
    return summary


def detect_graph_requests(message_content: str) -> List[dict]:
    """Extract @[Graph] operations from specialist message.
    
    Pattern: @[Graph][Operation][Layer1][Layer2][...]
    
    Supports operations:
        @[Graph][Create] - Propose new Q->A paths
        @[Graph][Update] - Vote on or extend existing paths
        @[Graph][Because] - Citation (existing path)
        @[Graph][If] - Citation (potential path)
        @[Graph][Regarding] - User comment on path
    
    Examples:
        @[Graph][Create][Q:single][What is the approach?]
        @[Graph][Create][Q:single][What is the approach?][A][Phased implementation]
        @[Graph][Update][Q:single][What is the approach?][A][Phased][👍][Good idea]
        @[Graph][Because][Q][...][A][...]
            
    Returns:
        List of dicts with 'raw' (full match) and 'operation' (Create/Update/etc)
    """
    # Pattern: @[Graph][Operation][...] with nested brackets
    pattern = r'@\[Graph\]\[([^\]]+)\]((?:\[[^\]]+\])*)'
    matches = re.findall(pattern, message_content, re.IGNORECASE)
    
    # Return list with operation type extracted
    results = []
    for operation, rest in matches:
        full_match = f"@[Graph][{operation}]{rest}"
        results.append({
            "raw": full_match,
            "operation": operation
        })
    
    return results


def validate_graph_update(content: str) -> tuple[bool, str, dict]:
    """
    Validate that a @[Graph][Update] entry is well-formed.
    
    Returns (is_valid, error_message, pattern_info)
    
    pattern_info dict contains:
        - has_question: bool
        - answer_count: int
        - has_nested_question: bool
    
    INVALID patterns:
    - Multiple consecutive [A] segments without intervening [Q] segments
      e.g., [A][text1][A][text2] is INVALID - each answer must be a separate @[Graph][Update]
    
    VALID patterns:
    - [Q:type][text]
    - [Q:type][text][A][text]
    - [Q:type][text][A][text][Q:type][text]
    - [Q:type][text][A][text][Q:type][text][A][text]
    """
    # Parse brackets character by character
    bracket_contents = []
    i = 0
    while i < len(content):
        if content[i] == '[':
            depth = 1
            j = i + 1
            while j < len(content) and depth > 0:
                if content[j] == '[':
                    depth += 1
                elif content[j] == ']':
                    depth -= 1
                j += 1
            if depth == 0:
                bracket_contents.append(content[i+1:j-1])
                i = j
            else:
                i += 1
        else:
            i += 1
    
    # Analyze pattern for targeted guidance
    has_question = any(item.startswith('Q:') for item in bracket_contents)
    answer_count = 0
    has_nested_question = False
    found_answer = False
    
    # Track the last structural element we saw
    last_element = None
    vote_markers = ['👍', '👎', '✅', '❌', '➖', '🧹']
    
    for item in bracket_contents:
        # Skip vote markers and comments
        if item in vote_markers:
            break
        
        # Count answers and detect nesting
        if item == 'A' or item.startswith('A:'):
            answer_count += 1
            if last_element == 'A':
                # Found consecutive [A] segments!
                pattern_info = {
                    'has_question': has_question,
                    'answer_count': answer_count,
                    'has_nested_question': has_nested_question
                }
                return False, "INVALID: Multiple consecutive [A] segments found. Each answer must be a separate @[Graph][Update] entry.", pattern_info
            found_answer = True
            last_element = 'A'
        elif item.startswith('Q:'):
            if found_answer:
                has_nested_question = True
            last_element = 'Q'
        # Text content doesn't change the last_element
    
    pattern_info = {
        'has_question': has_question,
        'answer_count': answer_count,
        'has_nested_question': has_nested_question
    }
    return True, "", pattern_info


def log_graph_operations(graph_requests: List[dict], requester_name: str, phase: int = None) -> List[AIMessage]:
    """Log @[Graph][Create] and @[Graph][Update] operations to graph.log.
    Validates each operation and returns Notice messages for malformed entries.
        
    Args:
        graph_requests: List of detected graph operations with 'raw' and 'operation' fields
        requester_name: Name of the specialist who made the request
        phase: Current discussion phase (if available)
        
    Returns:
        List of Notice AIMessages for malformed operations (injected into conversation)
    """
    # Load existing paths if not already loaded
    global _created_paths
    if not _created_paths:
        load_existing_paths_from_log()
    
    # Filter for Create and Update operations only
    operations = [req for req in graph_requests 
                  if req.get('operation') in ['Create', 'Update']]
    
    if not operations:
        return []
    
    # Append to graph.log
    log_path = "graph.log"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    notice_messages = []
    auto_clear_operations = []  # Collect operations to auto-clear user selections from duplicates
    
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            for req in operations:
                operation_type = req.get('operation', 'Update')
                phase_str = f"Phase {phase}" if phase is not None else "Phase ?"
                
                # Clean up whitespace in vote markers (emoji format only)
                cleaned_raw = req['raw']
                cleaned_raw = re.sub(r'\[\s*👍\s*\]', '[👍]', cleaned_raw)
                cleaned_raw = re.sub(r'\[\s*👎\s*\]', '[👎]', cleaned_raw)
                cleaned_raw = re.sub(r'\[\s*✅\s*\]', '[✅]', cleaned_raw)
                cleaned_raw = re.sub(r'\[\s*❌\s*\]', '[❌]', cleaned_raw)
                cleaned_raw = re.sub(r'\[\s*➖\s*\]', '[➖]', cleaned_raw)
                cleaned_raw = re.sub(r'\[\s*🧹\s*\]', '[🧹]', cleaned_raw)
                
                # Extract the path from this operation
                path = extract_path_from_content(cleaned_raw.replace(f'@[Graph][{operation_type}]', ''))
                
                # Validate Create vs Update semantics
                if operation_type == 'Create':
                    if path in _created_paths:
                        # Path already exists - reject Create
                        notice_content = (
                            f"@[All] Notice: @[{requester_name}]'s @[Graph][Create] was REJECTED - path already exists.\n\n"
                            f"Attempted: {cleaned_raw[:120]}{'...' if len(cleaned_raw) > 120 else ''}\n\n"
                            f"Error: Path already created. Use @[Graph][Update] to vote on or extend existing paths.\n\n"
                            f"**Correct approach** - Vote on the existing path:\n"
                            f"  @[Graph][Update]{path}[👍][Your rationale here]\n\n"
                            f"@[{requester_name}], please use @[Graph][Update] instead of @[Graph][Create] for this path."
                        )
                        
                        validation_timestamp = datetime.now().astimezone().isoformat(timespec='milliseconds')
                        notice_msg = AIMessage(
                            content=notice_content,
                            name="Notice",
                            additional_kwargs={
                                "phase": phase if phase is not None else "?",
                                "timestamp": validation_timestamp
                            }
                        )
                        notice_messages.append(notice_msg)
                        continue
                
                elif operation_type == 'Update':
                    # Check if this is question-only or rationale-only (allowed even if path doesn't exist)
                    has_vote = any(marker in cleaned_raw for marker in ['👍', '👎', '✅', '❌', '➖', '🧹'])
                    is_question_only = '[Q:' in cleaned_raw and '[A]' not in cleaned_raw and not has_vote
                    is_rationale_only = has_vote and path
                    
                    # If it's a full Q->A path and doesn't exist, reject
                    if path and '[A]' in cleaned_raw and path not in _created_paths and not is_question_only:
                        notice_content = (
                            f"@[All] Notice: @[{requester_name}]'s @[Graph][Update] was REJECTED - path does not exist.\n\n"
                            f"Attempted: {cleaned_raw[:120]}{'...' if len(cleaned_raw) > 120 else ''}\n\n"
                            f"Error: Path not yet created. Use @[Graph][Create] to propose new paths first.\n\n"
                            f"**Correct approach** - Create the path first:\n"
                            f"  @[Graph][Create]{path}\n"
                            f"  @[Graph][Update]{path}[👍][Your rationale here]\n\n"
                            f"@[{requester_name}], you can create and vote in the same message with two @[Graph] operations."
                        )
                        
                        validation_timestamp = datetime.now().astimezone().isoformat(timespec='milliseconds')
                        notice_msg = AIMessage(
                            content=notice_content,
                            name="Notice",
                            additional_kwargs={
                                "phase": phase if phase is not None else "?",
                                "timestamp": validation_timestamp
                            }
                        )
                        notice_messages.append(notice_msg)
                        continue
                
                # Validate the graph structure (consecutive [A] check, etc.)
                is_valid, error_msg, pattern_info = validate_graph_update(cleaned_raw)
                
                if not is_valid:
                    # Print warning to stderr (for TUI display)
                    print(f"\n{'='*80}", file=sys.stderr)
                    print(f"⚠️  MALFORMED @[Graph][Update] from {requester_name} (not logged to graph.log)", file=sys.stderr)
                    print(f"{'='*80}", file=sys.stderr)
                    print(f"Error: {error_msg}", file=sys.stderr)
                    print(f"Content: {cleaned_raw[:200]}{'...' if len(cleaned_raw) > 200 else ''}", file=sys.stderr)
                    print(f"{'='*80}\n", file=sys.stderr)
                    
                    # Extract pattern info from validation (no re-parsing needed)
                    has_question = pattern_info['has_question']
                    answer_count = pattern_info['answer_count']
                    has_nested_question = pattern_info['has_nested_question']
                    
                    # Extract a short preview
                    preview = cleaned_raw[:120] + '...' if len(cleaned_raw) > 120 else cleaned_raw
                    
                    # Create targeted Notice based on detected pattern
                    notice_content = (
                        f"@[All] Notice: @[{requester_name}]'s @[Graph][Update] was MALFORMED and not added to the graph.\n\n"
                        f"Attempted: {preview}\n\n"
                        f"Error: {error_msg}\n\n"
                    )
                    
                    # Provide targeted guidance based on what they tried
                    if has_question and answer_count > 1 and not has_nested_question:
                        # Pattern: [Q][text][A][text][A][text] - multiple answers at same level
                        notice_content += (
                            f"**Detected pattern**: Multiple answers to the same question in one entry.\n\n"
                            f"**Correct approach** - Each answer must be a separate @[Graph][Update]:\n"
                            f"  @[Graph][Update][Q:type][Your question][A][First option]\n"
                            f"  @[Graph][Update][Q:type][Your question][A][Second option]\n"
                            f"  @[Graph][Update][Q:type][Your question][A][Third option]\n"
                        )
                    elif has_nested_question and answer_count > 1:
                        # Pattern: [Q][A][text][A][text][Q] or [Q][A][Q][A] - trying to nest with multiple A's
                        notice_content += (
                            f"**Detected pattern**: Multiple answers across nested levels.\n\n"
                            f"**Correct approach** - Build nested paths with separate entries:\n"
                            f"  @[Graph][Update][Q:type][Parent question][A][Parent answer]\n"
                            f"  @[Graph][Update][Q:type][Parent question][A][Parent answer][Q:type][Child question][A][Child answer]\n"
                            f"  (Each path has only ONE answer per level)\n"
                        )
                    else:
                        # Generic case - show general pattern
                        notice_content += (
                            f"**Correct approach** - Each answer must be a separate @[Graph][Update]:\n"
                            f"  @[Graph][Update][Q:type][Question][A][Option 1]\n"
                            f"  @[Graph][Update][Q:type][Question][A][Option 2]\n"
                        )
                    
                    notice_content += (
                        f"\n**Key rule**: Valid patterns have at most one [A] per nesting level.\n"
                        f"Invalid: [A][text][A][text] ❌\n"
                        f"Valid: [Q:type][text][A][text] ✅ | [Q:type][text][A][text][Q:type][text][A][text] ✅\n\n"
                        f"@[{requester_name}], your contribution is valuable—please resubmit the SAME content using separate @[Graph][Update] entries. "
                        f"Don't skip this contribution; just use the correct format above."
                    )
                    
                    validation_timestamp = datetime.now().astimezone().isoformat(timespec='milliseconds')
                    notice_msg = AIMessage(
                        content=notice_content,
                        name="Notice",
                        additional_kwargs={
                            "phase": phase if phase is not None else "?",
                            "timestamp": validation_timestamp
                        }
                    )
                    notice_messages.append(notice_msg)
                    
                    # Skip writing this malformed entry to graph.log
                    continue
                
                # Valid - write to graph.log
                f.write(f"[{timestamp}] {phase_str} | {requester_name} | {cleaned_raw}\n")
                
                # If this is a duplicate marker ([🧹]) from Chair, validate and queue auto-clear operation
                if operation_type == 'Update' and '[🧹]' in cleaned_raw and requester_name == 'Chair':
                    # Extract the duplicate path (the one being marked as duplicate)
                    # Format: @[Graph][Update][duplicate_path][🧹][canonical_path]
                    broom_index = cleaned_raw.find('[🧹]')
                    if broom_index > 0:
                        before_broom = cleaned_raw[:broom_index]
                        after_broom = cleaned_raw[broom_index + len('[🧹]'):]
                        
                        duplicate_path = extract_path_from_content(before_broom)
                        canonical_path = extract_path_from_content(after_broom)
                        
                        # VALIDATION: Reject nonsensical duplicate markers
                        is_valid_duplicate = True
                        rejection_reason = None
                        
                        if duplicate_path and canonical_path:
                            # Check 1: Duplicate and canonical must be DIFFERENT paths
                            if duplicate_path == canonical_path:
                                is_valid_duplicate = False
                                rejection_reason = "Duplicate and canonical paths are identical"
                            
                            # Check 2: Answer cannot be duplicate of its parent question
                            # If duplicate has [A] but canonical doesn't, and canonical is a prefix of duplicate,
                            # then duplicate is an answer under canonical question - INVALID
                            elif '[A]' in duplicate_path and '[A]' not in canonical_path:
                                if duplicate_path.startswith(canonical_path):
                                    is_valid_duplicate = False
                                    rejection_reason = "Answer cannot be marked as duplicate of its parent question"
                            
                            # Check 3: Question cannot be duplicate of answer under that question
                            # If canonical has [A] but duplicate doesn't, and canonical starts with duplicate,
                            # then canonical is an answer under duplicate question - INVALID
                            elif '[A]' in canonical_path and '[A]' not in duplicate_path:
                                if canonical_path.startswith(duplicate_path):
                                    is_valid_duplicate = False
                                    rejection_reason = "Question cannot be marked as duplicate of its own answer"
                        
                        if is_valid_duplicate and duplicate_path:
                            auto_clear_operations.append(duplicate_path)
                        elif not is_valid_duplicate:
                            # Log rejection to stderr and graph.log as a validation notice
                            print(f"\n{'='*80}", file=sys.stderr)
                            print(f"⚠️  REJECTED INVALID DUPLICATE MARKER from Chair", file=sys.stderr)
                            print(f"{'='*80}", file=sys.stderr)
                            print(f"Reason: {rejection_reason}", file=sys.stderr)
                            print(f"Chair attempted: {cleaned_raw[:150]}{'...' if len(cleaned_raw) > 150 else ''}", file=sys.stderr)
                            print(f"{'='*80}\n", file=sys.stderr)
                            
                            # Write rejection notice to graph.log
                            f.write(f"[{timestamp}] {phase_str} | REJECTED | {cleaned_raw} | Reason: {rejection_reason}\n")
                
                # Track newly created paths for future Create/Update validation
                if operation_type == 'Create' and path:
                    _created_paths.add(path)
                
    except Exception as e:
        # Don't fail if logging doesn't work - just continue
        print(f"Warning: Could not log to graph.log: {e}", file=sys.stderr)
    
    # Process auto-clear operations for duplicates with user selections
    if auto_clear_operations:
        try:
            # Read graph.log to find which duplicate paths have user selections
            paths_to_clear = []
            with open(log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    for duplicate_path in auto_clear_operations:
                        # Look for user selections on this duplicate path
                        if ('User (Web UI)' in line and 
                            duplicate_path in line and 
                            '[✅]' in line):
                            paths_to_clear.append(duplicate_path)
                            break
            
            # Write auto-clear operations for paths that have user selections
            if paths_to_clear:
                with open(log_path, 'a', encoding='utf-8') as f:
                    for duplicate_path in paths_to_clear:
                        clear_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                        clear_operation = f"@[Graph][Update]{duplicate_path}[➖][Auto-cleared: path marked as duplicate by Chair]"
                        # Write as User (Web UI) so it appears as a user action in the room
                        f.write(f"[{clear_timestamp}] User (Web UI) | {clear_operation}\n")
                        print(f"🧹 Auto-cleared user selection from duplicate path: {duplicate_path[:80]}...", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Could not auto-clear duplicate selections: {e}", file=sys.stderr)
    
    return notice_messages


def process_graph_operations(message_content: str, requester_name: str = None, phase: int = None) -> List[AIMessage]:
    """Process @[Graph] operations and return response messages.
    
    PROTOTYPE: Currently just acknowledges the syntax without building a real graph.
    Also logs all @[Graph][Create] and @[Graph][Update] operations to graph.log.
    Validates Create (must not exist) vs Update (must exist) and returns Notice messages for violations.
    
    Args:
        message_content: The specialist's message content
        requester_name: Name of the specialist requesting graph operations
        phase: Current discussion phase (for logging)
        
    Returns:
        List of AIMessage responses (includes Notice messages for malformed/invalid operations)
    """
    graph_requests = detect_graph_requests(message_content)
    
    if not graph_requests:
        return []
    
    # Log Create/Update operations to graph.log (returns Notice messages for invalid operations)
    notice_messages = []
    if requester_name:
        notice_messages = log_graph_operations(graph_requests, requester_name, phase)
    
    # If there were malformed/invalid operations, return Notice messages immediately
    # (don't add the normal acknowledgment message)
    if notice_messages:
        return notice_messages
    
    # For prototype: Just return a single acknowledgment message
    # In full implementation, this would create/update graph nodes and return structured feedback
    
    requester_display = f"@[{requester_name}]" if requester_name else "Specialist"
    
    response_content = f"""Graph tool (PROTOTYPE): Acknowledged {len(graph_requests)} @[Graph] operation(s) from {requester_display}.

⚠️ **NOTE**: The graph backend is not yet implemented. Your @[Graph] syntax has been recorded for observing usage patterns before building the full implementation.

What you requested:
"""
    
    for i, req in enumerate(graph_requests, 1):
        response_content += f"\n{i}. {req['raw']}"
    
    response_content += """

**For now**: Continue using @[Graph] syntax naturally in your responses. We're observing how specialists collaborate to build structured knowledge before implementing the full graph database backend.

**Next**: Other specialists can extend your graph proposals by referencing the same paths in their @[Graph] operations."""
    
    # Return as AIMessage so it appears in conversation like Search/ReadURL results
    return [AIMessage(
        content=response_content,
        name="Graph tool",
        additional_kwargs={
            "timestamp": None,  # Will be added by system
            "phase": None  # Will be added by system
        }
    )]


class QuestionGraph:
    """Placeholder for future graph database implementation.
    
    PROTOTYPE: Not yet implemented. This class exists to satisfy imports
    while we observe usage patterns.
    """
    
    def __init__(self):
        """Initialize placeholder graph."""
        pass
    
    def create_question(self, *args, **kwargs):
        """Placeholder - not yet implemented."""
        raise NotImplementedError("Graph backend not yet implemented")
    
    def create_answer(self, *args, **kwargs):
        """Placeholder - not yet implemented."""
        raise NotImplementedError("Graph backend not yet implemented")
    
    def vote(self, *args, **kwargs):
        """Placeholder - not yet implemented."""
        raise NotImplementedError("Graph backend not yet implemented")
