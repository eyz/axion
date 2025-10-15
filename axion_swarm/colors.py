"""ANSI color codes for terminal output."""

# ANSI color codes
DARK_GREEN = '\033[32m'
LIGHT_GREEN = '\033[92m'
LIGHT_BLUE = '\033[94m'
CYAN = '\033[96m'
LIGHT_PURPLE = '\033[95m'
YELLOW = '\033[93m'
ORANGE = '\033[38;5;208m'  # 256-color orange
RED = '\033[91m'
WHITE = '\033[97m'
GREY = '\033[90m'
DARK_GREY = '\033[90m'  # Same as GREY but named for clarity in different contexts
LIGHT_GREY = '\033[37m'  # Brighter grey for more prominent secondary content
RESET = '\033[0m'

def dark_green(text: str) -> str:
    """Wrap text in dark green color."""
    return f"{DARK_GREEN}{text}{RESET}"

def light_green(text: str) -> str:
    """Wrap text in light green color."""
    return f"{LIGHT_GREEN}{text}{RESET}"

def light_blue(text: str) -> str:
    """Wrap text in light blue color."""
    return f"{LIGHT_BLUE}{text}{RESET}"

def cyan(text: str) -> str:
    """Wrap text in cyan color."""
    return f"{CYAN}{text}{RESET}"

def light_purple(text: str) -> str:
    """Wrap text in light purple color."""
    return f"{LIGHT_PURPLE}{text}{RESET}"

def yellow(text: str) -> str:
    """Wrap text in yellow color."""
    return f"{YELLOW}{text}{RESET}"

def orange(text: str) -> str:
    """Wrap text in orange color."""
    return f"{ORANGE}{text}{RESET}"

def red(text: str) -> str:
    """Wrap text in red color."""
    return f"{RED}{text}{RESET}"

def white(text: str) -> str:
    """Wrap text in white color."""
    return f"{WHITE}{text}{RESET}"

def grey(text: str) -> str:
    """Wrap text in grey color."""
    return f"{GREY}{text}{RESET}"

def dark_grey(text: str) -> str:
    """Wrap text in dark grey color."""
    return f"{DARK_GREY}{text}{RESET}"

def light_grey(text: str) -> str:
    """Wrap text in light grey color (brighter for more prominent secondary content)."""
    return f"{LIGHT_GREY}{text}{RESET}"

def colorize_graph_mentions(text: str) -> str:
    """Colorize @[Graph][...][...][...] mentions with specific color scheme.
    
    Color scheme:
    - @[Graph] → light blue (tool mention, same as @[Search])
    - [Update], [Collapse], [Because], [If] → orange
    - [Q:*], [A], [A:ReadURL], [A:Search], [+], [-], [X] → yellow  
    - Question/answer text and comments in [...] → light blue
    
    Returns to LIGHT_GREEN after each Graph mention to maintain message color context.
    
    Examples: 
    - @[Graph][Update][Q:single][What is X?][A][Answer text]
    - @[Graph][If][Q:single][What is X?][A][Option 1]
    - @[Graph][Because][Q:single][What is X?][A][Chosen answer]
    """
    # Simple state-machine approach: find @[Graph] then consume consecutive [...] brackets
    result = []
    i = 0
    
    while i < len(text):
        # Look for @[Graph]
        if text[i:i+8] == '@[Graph]':
            # Start with @[Graph] in light blue (tool mention, same as @[Search])
            result.append(f"{LIGHT_BLUE}@[Graph]{RESET}{LIGHT_GREEN}")
            i += 8
            
            # Now consume all consecutive [...] brackets until we hit whitespace or end
            while i < len(text) and text[i] == '[':
                # Find the closing ]
                j = i + 1
                bracket_depth = 1
                while j < len(text) and bracket_depth > 0:
                    if text[j] == '[':
                        bracket_depth += 1
                    elif text[j] == ']':
                        bracket_depth -= 1
                    j += 1
                
                if bracket_depth == 0:
                    # We found a complete bracket
                    content = text[i+1:j-1]  # Extract content between [ and ]
                    
                    # Colorize based on content, then return to light green
                    if content in ("Update", "Collapse", "Because", "If"):
                        result.append(f"[{ORANGE}{content}{RESET}{LIGHT_GREEN}]")
                    elif content == "Q" or content == "A" or content.startswith("Q:") or content.startswith("A:") or content == "X":
                        # Q, A, Q:single, Q:multiple, Q:open, A:ReadURL, A:Search, X → yellow
                        result.append(f"[{YELLOW}{content}{RESET}{LIGHT_GREEN}]")
                    elif content == "+" or content == "-":
                        # Vote markers: [+] upvote, [-] downvote → yellow
                        result.append(f"[{YELLOW}{content}{RESET}{LIGHT_GREEN}]")
                    else:
                        # Question text, answer text, comments → light blue
                        result.append(f"[{LIGHT_BLUE}{content}{RESET}{LIGHT_GREEN}]")
                    
                    i = j
                else:
                    # Malformed bracket, just output it as-is
                    result.append(text[i])
                    i += 1
            
            # Return to light green after the complete Graph mention
            result.append(f"{RESET}{LIGHT_GREEN}")
        else:
            # Not a Graph mention, just copy the character
            result.append(text[i])
            i += 1
    
    return ''.join(result)


def colorize_graph_mentions_rich(text: str) -> str:
    """Colorize @[Graph][...][...][...] mentions with Rich markup for TUI.
    
    Color scheme (Rich color codes):
    - @[Graph] → color(12) (light blue, tool mention same as @[Search])
    - [Update], [Collapse], [Because], [If] → color(208) (orange)
    - [Q:*], [A], [A:ReadURL], [A:Search], [+], [-], [X] → color(11) (yellow)
    - Question/answer text and comments → color(12) (light blue)
    
    Returns Rich markup with color tags.
    """
    # Simple state-machine approach: find @[Graph] then consume consecutive [...] brackets
    result = []
    i = 0
    
    while i < len(text):
        # Look for @[Graph]
        if text[i:i+8] == '@[Graph]':
            # Start with @[Graph] in light blue (tool mention, same as @[Search])
            result.append('[color(12)]@\\[Graph][/color(12)]')
            i += 8
            
            # Now consume all consecutive [...] brackets
            while i < len(text) and text[i] == '[':
                # Find the closing ]
                j = i + 1
                bracket_depth = 1
                while j < len(text) and bracket_depth > 0:
                    if text[j] == '[':
                        bracket_depth += 1
                    elif text[j] == ']':
                        bracket_depth -= 1
                    j += 1
                
                if bracket_depth == 0:
                    # We found a complete bracket
                    content = text[i+1:j-1]  # Extract content between [ and ]
                    
                    # Colorize based on content (use \\[ for opening bracket, plain ] for closing)
                    if content in ("Update", "Collapse", "Because", "If"):
                        result.append(f'\\[[color(208)]{content}[/color(208)]]')
                    elif content == "Q" or content == "A" or content.startswith("Q:") or content.startswith("A:") or content == "X":
                        # Q, A, Q:single, Q:multiple, Q:open, A:ReadURL, A:Search, X → yellow
                        result.append(f'\\[[color(11)]{content}[/color(11)]]')
                    elif content == "+" or content == "-":
                        # Vote markers → yellow
                        result.append(f'\\[[color(11)]{content}[/color(11)]]')
                    else:
                        # Question text, answer text, comments → light blue
                        result.append(f'\\[[color(12)]{content}[/color(12)]]')
                    
                    i = j
                else:
                    # Malformed bracket, just output it as-is
                    result.append(text[i])
                    i += 1
        else:
            # Not a Graph mention, just copy the character
            result.append(text[i])
            i += 1
    
    return ''.join(result)

