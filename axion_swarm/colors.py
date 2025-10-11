"""ANSI color codes for terminal output."""

# ANSI color codes
DARK_GREEN = '\033[32m'
LIGHT_GREEN = '\033[92m'
LIGHT_BLUE = '\033[94m'
CYAN = '\033[96m'
LIGHT_PURPLE = '\033[95m'
YELLOW = '\033[93m'
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

