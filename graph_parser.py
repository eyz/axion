#!/usr/bin/env python3
"""
Parse graph.log for the Axion Swarm web interface.

This module contains the core parsing logic used by webserver.py to convert
graph.log entries into structured data for the Vue.js frontend.
"""

import re
from collections import defaultdict


def normalize_text(text):
    """Normalize Unicode characters to avoid duplicates from lookalike characters"""
    # Replace various dash/hyphen characters with standard hyphen
    text = text.replace('‑', '-')  # U+2011 NON-BREAKING HYPHEN
    text = text.replace('‐', '-')  # U+2010 HYPHEN
    text = text.replace('–', '-')  # U+2013 EN DASH
    text = text.replace('—', '-')  # U+2014 EM DASH
    # Replace various space characters with standard space
    text = text.replace('\u00A0', ' ')  # NO-BREAK SPACE
    text = text.replace('\u2009', ' ')  # THIN SPACE
    # Normalize quotes
    text = text.replace('"', '"').replace('"', '"')  # Smart quotes to straight
    text = text.replace(''', "'").replace(''', "'")  # Smart apostrophes to straight
    return text


def validate_graph_path(bracket_contents):
    """
    Validate that a graph path is well-formed.
    
    Returns (is_valid, error_message)
    
    INVALID patterns:
    - Multiple consecutive [A] segments without intervening [Q] segments
      e.g., [A][text1][A][text2] is INVALID - each answer must be a separate @[Graph][Update]
    
    VALID patterns:
    - [Q:type][text]
    - [Q:type][text][A][text]
    - [Q:type][text][A][text][Q:type][text]
    - [Q:type][text][A][text][Q:type][text][A][text]
    """
    # Track the last structural element we saw
    last_element = None
    
    for i, item in enumerate(bracket_contents):
        # Skip vote markers and comments
        if item in ['👍', '👎', '✅', '❌', '➖', '🧹']:
            break
        
        # Check for consecutive [A] segments
        if item == 'A' or item.startswith('A:'):
            if last_element == 'A':
                # Found consecutive [A] segments!
                return False, "Multiple consecutive [A] segments found. Each answer must be a separate @[Graph][Update] entry."
            last_element = 'A'
        elif item.startswith('Q:'):
            last_element = 'Q'
        # Text content doesn't change the last_element
    
    return True, None


def handle_regarding_entry(content, timestamp, specialist, nodes):
    """Parse and store user [Regarding] comments on graph nodes"""
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
    
    if not bracket_contents:
        return
    
    # Build path segments (same logic as Update entries)
    vote_markers = ['👍', '👎', '✅', '❌', '➖', '🧹']
    path_segments = []
    current_path = ""
    i = 0
    
    while i < len(bracket_contents):
        item = bracket_contents[i]
        
        if item in vote_markers:
            break
        
        if item.startswith('Q:') or item.startswith('A:') or item == 'A':
            current_path += f"[{item}]"
            
            if i + 1 < len(bracket_contents):
                next_item = bracket_contents[i + 1]
                if (next_item not in vote_markers and 
                    not next_item.startswith('Q:') and 
                    not next_item.startswith('A:') and 
                    next_item != 'A'):
                    normalized = normalize_text(next_item)
                    current_path += f"[{normalized}]"
                    i += 1
            
            path_segments.append(current_path)
        
        i += 1
    
    # The full path is the last segment
    full_path = path_segments[-1] if path_segments else ""
    if not full_path:
        return
    
    # The comment is the last bracket content (after the path)
    comment = bracket_contents[-1] if bracket_contents else ""
    
    # Create node if it doesn't exist
    if full_path not in nodes:
        nodes[full_path] = {
            'votes': [],
            'first_seen_phase': 'User',
            'first_seen_specialist': specialist,
            'timestamp': timestamp
        }
    
    # Add user_thoughts array if it doesn't exist
    if 'user_thoughts' not in nodes[full_path]:
        nodes[full_path]['user_thoughts'] = []
    
    # Add the user thought
    nodes[full_path]['user_thoughts'].append({
        'specialist': specialist,
        'comment': comment,
        'timestamp': timestamp
    })


def analyze_graph_log(log_path):
    """Parse graph.log and return analysis data"""
    with open(log_path, 'r') as f:
        lines = f.readlines()
    
    nodes = {}
    vote_tally = defaultdict(lambda: {'upvotes': 0, 'downvotes': 0, 'duplicates': 0, 'up_by': [], 'down_by': [], 'duplicate_by': [], 'canonical_path': None})
    specialist_stats = defaultdict(lambda: {'upvotes': 0, 'downvotes': 0, 'duplicates': 0, 'total': 0, 'by_phase': defaultdict(int)})
    canonical_paths = []  # Track KeepCanonical paths to link with MarkDuplicate
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Try to match [Regarding] entries (user thoughts/comments)
        regarding_match = re.match(r'\[([^\]]+)\] ([^|]+) \| @\[Graph\]\[Regarding\](.+)$', line)
        if regarding_match:
            timestamp, specialist, content = regarding_match.groups()
            specialist = specialist.strip()
            # Process [Regarding] entry
            handle_regarding_entry(content, timestamp, specialist, nodes)
            continue
        
        # Try to match with phase number (specialist operations)
        match = re.match(r'\[([^\]]+)\] Phase (\d+) \| ([^|]+) \| @\[Graph\]\[(?:Create|Update|KeepCanonical|MarkDuplicate)\](.+)$', line)
        if match:
            timestamp, phase, specialist, content = match.groups()
            specialist = specialist.strip()
            # Extract operation type
            operation_match = re.search(r'@\[Graph\]\[(\w+)\]', line)
            operation_type = operation_match.group(1) if operation_match else 'Update'
        else:
            # Try to match without phase number (user votes from Web UI - always Update)
            match = re.match(r'\[([^\]]+)\] ([^|]+) \| @\[Graph\]\[Update\](.+)$', line)
            if not match:
                continue
            timestamp, specialist, content = match.groups()
            specialist = specialist.strip()
            phase = 'User'  # Mark as user-submitted
            operation_type = 'Update'
        
        # Parse brackets character by character
        bracket_contents = []
        i = 0
        while i < len(content):
            if content[i] == '[':
                # Find matching ]
                depth = 1
                j = i + 1
                while j < len(content) and depth > 0:
                    if content[j] == '[':
                        depth += 1
                    elif content[j] == ']':
                        depth -= 1
                    j += 1
                if depth == 0:
                    # Extract content between [ and ]
                    bracket_contents.append(content[i+1:j-1])
                    i = j
                else:
                    i += 1
            else:
                i += 1
        
        if not bracket_contents:
            continue
        
        # Validate the graph path structure
        is_valid, error_msg = validate_graph_path(bracket_contents)
        if not is_valid:
            print(f"⚠️  [graph_parser.py] MALFORMED GRAPH UPDATE (line skipped): {error_msg}")
            print(f"    Timestamp: {timestamp}")
            print(f"    Specialist: {specialist}")
            print(f"    Content: {content[:200]}{'...' if len(content) > 200 else ''}")
            continue
        
        # Build path segments incrementally, creating intermediate nodes
        # Vote markers that signal end of path
        vote_markers = ['👍', '👎', '✅', '❌', '➖', '🧹']
        
        path_segments = []
        current_path = ""
        i = 0
        
        while i < len(bracket_contents):
            item = bracket_contents[i]
            
            # Stop at vote markers
            if item in vote_markers:
                break
            
            # Q: or A markers start a new node component
            if item.startswith('Q:') or item.startswith('A:') or item == 'A':
                current_path += f"[{item}]"
                
                # Check if next item is the text (not another marker)
                if i + 1 < len(bracket_contents):
                    next_item = bracket_contents[i + 1]
                    if (next_item not in vote_markers and 
                        not next_item.startswith('Q:') and 
                        not next_item.startswith('A:') and 
                        next_item != 'A'):
                        # This is text, normalize and include it
                        normalized = normalize_text(next_item)
                        current_path += f"[{normalized}]"
                        i += 1
                
                # Save this segment
                path_segments.append(current_path)
            
            i += 1
        
        # Create nodes for all intermediate segments to maintain hierarchy
        for segment_path in path_segments:
            if segment_path and segment_path not in nodes:
                nodes[segment_path] = {
                    'votes': [],
                    'first_seen_phase': phase,
                    'first_seen_specialist': specialist,
                    'timestamp': timestamp
                }
        
        # The full path is the last segment (or empty if no segments)
        full_path = path_segments[-1] if path_segments else ""
        if not full_path:
            continue
        
        # HANDLE NEW DEDUPE OPERATIONS (KeepCanonical / MarkDuplicate)
        if operation_type == 'KeepCanonical':
            # Record this path as canonical for tooltip lookup
            canonical_paths.append(full_path)
            continue
        elif operation_type == 'MarkDuplicate':
            # Mark this path as a duplicate
            vote_tally[full_path]['duplicates'] += 1
            vote_tally[full_path]['duplicate_by'].append(specialist)
            specialist_stats[specialist]['duplicates'] += 1
            
            # Find matching canonical path (same parent question)
            # Extract question part from duplicate path
            question_match = re.match(r'(\[Q:[^\]]+\]\[[^\]]+\])', full_path)
            if question_match:
                question_part = question_match.group(1)
                # Find KeepCanonical path with same question
                for canonical in canonical_paths:
                    if canonical.startswith(question_part):
                        vote_tally[full_path]['canonical_path'] = canonical
                        break
            
            continue
        
        # Detect vote and comment (support both old ASCII and new emoji format)
        vote = None
        vote_comment = None
        canonical_path = None  # For old duplicate markers (legacy support)
        vote_map = {
            '+': '👍',      # Specialist upvote
            '-': '👎',      # Specialist downvote
            'X': '❌',      # User dismiss (legacy)
            '=': '➖',      # User neutral (legacy)
            '👍': '👍',    # Specialist upvote
            '👎': '👎',    # Specialist downvote
            '✅': '✅',    # User approval
            '❌': '❌',    # User dismiss
            '➖': '➖',    # User neutral
            '🧹': '🧹',    # Duplicate marker
        }
        
        for i, item in enumerate(bracket_contents):
            if item in vote_map:
                vote = vote_map[item]
                
                # Special handling for duplicate marker - extract canonical path reference
                if vote == '🧹' and i + 1 < len(bracket_contents):
                    # After [🧹], parse the canonical path
                    # Format: [🧹][Q:type][text][A][text]...[comment]
                    # We need to extract everything until we hit a non-structural bracket
                    canonical_parts = []
                    j = i + 1
                    while j < len(bracket_contents):
                        part = bracket_contents[j]
                        # Check if this is a structural element (Q:, A:, A) or text
                        if part.startswith('Q:') or part.startswith('A:') or part == 'A':
                            canonical_parts.append(f"[{part}]")
                            j += 1
                        elif canonical_parts and not part.startswith('Q:') and not part.startswith('A:'):
                            # This is text content following a structural marker
                            canonical_parts.append(f"[{part}]")
                            j += 1
                        else:
                            # This looks like the comment - stop parsing canonical path
                            vote_comment = part
                            break
                    
                    if canonical_parts:
                        canonical_path = ''.join(canonical_parts)
                
                # For non-duplicate votes, capture comment normally
                elif i + 1 < len(bracket_contents):
                    next_item = bracket_contents[i + 1]
                    # Validate: comment should not be a vote marker or structural element
                    if (next_item not in vote_map and 
                        not next_item.startswith('Q:') and 
                        not next_item.startswith('A:') and 
                        next_item not in ['A', 'If', 'Because']):
                        vote_comment = next_item
                break
        
        # Store node info
        if full_path not in nodes:
            nodes[full_path] = {
                'votes': [],
                'first_seen_phase': phase,
                'first_seen_specialist': specialist,
                'timestamp': timestamp  # Add timestamp for "NEW" badge detection
            }
        
        # Record vote if present (votes are always on the full path - the last segment)
        if vote:
            vote_record = {
                'specialist': specialist,
                'vote': vote,
                'comment': vote_comment,
                'phase': phase,
                'timestamp': timestamp
            }
            # For duplicate markers, include the canonical path reference
            if canonical_path:
                vote_record['canonical_path'] = canonical_path
            
            nodes[full_path]['votes'].append(vote_record)
            
            # Count upvotes vs downvotes (emoji-aware)
            if vote in ['👍', '✅']:  # Upvote or User approval
                vote_tally[full_path]['upvotes'] += 1
                vote_tally[full_path]['up_by'].append(specialist)
                specialist_stats[specialist]['upvotes'] += 1
            elif vote in ['👎', '❌']:  # Downvote or User dismiss
                vote_tally[full_path]['downvotes'] += 1
                vote_tally[full_path]['down_by'].append(specialist)
                specialist_stats[specialist]['downvotes'] += 1
            elif vote == '🧹':  # Duplicate marker
                vote_tally[full_path]['duplicates'] += 1
                vote_tally[full_path]['duplicate_by'].append(specialist)
                specialist_stats[specialist]['duplicates'] += 1
                # Store the canonical path reference (only one since only Chair marks duplicates)
                if canonical_path:
                    vote_tally[full_path]['canonical_path'] = canonical_path
            # '➖' (neutral) is not counted as up or down
            
            specialist_stats[specialist]['total'] += 1
            specialist_stats[specialist]['by_phase'][phase] += 1
    
    return nodes, vote_tally, specialist_stats

