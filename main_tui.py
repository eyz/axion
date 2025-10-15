#!/usr/bin/env python3
"""Textual TUI interface for Axion Swarm - Interactive chat-like interface."""

import asyncio
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, RichLog, Input, Label, Static, ListView, ListItem, Button
from textual.containers import VerticalScroll, Horizontal, Vertical, Container
from textual.reactive import reactive
from textual.screen import ModalScreen

from axion_swarm import create_swarm_graph, OverallState
from axion_swarm.checkpoint import load_checkpoint, delete_checkpoint, checkpoint_exists
from axion_swarm.config import initialize_specialist_presence

load_dotenv()

# Setup logging to discussion.log (file only - no console output to avoid interfering with TUI)
log_file = Path("discussion.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='a', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


# Global queue for web UI commands
web_ui_commands = []
web_ui_commands_lock = threading.Lock()
stop_file_watcher = threading.Event()


def watch_user_input_file(filepath='user_input.txt'):
    """Background thread that watches user_input.txt for web UI submissions using inotify."""
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    
    file_path = Path(filepath)
    last_position = 0
    
    class UserInputHandler(FileSystemEventHandler):
        def __init__(self):
            self.last_position = 0
        
        def on_modified(self, event):
            if event.src_path.endswith(filepath):
                self.process_file()
        
        def on_created(self, event):
            if event.src_path.endswith(filepath):
                self.last_position = 0
                self.process_file()
        
        def process_file(self):
            try:
                if not file_path.exists():
                    return
                
                current_size = file_path.stat().st_size
                
                # If file grew, read new content
                if current_size > self.last_position:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        f.seek(self.last_position)
                        new_lines = f.readlines()
                        self.last_position = f.tell()
                    
                    # Process new lines
                    for line in new_lines:
                        line = line.strip()
                        # Skip empty lines and comments
                        if line and not line.startswith('#'):
                            with web_ui_commands_lock:
                                web_ui_commands.append(line)
                            
                            # Also append to graph.log
                            try:
                                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                                with open('graph.log', 'a', encoding='utf-8') as f:
                                    f.write(f"[{timestamp}] User (Web UI) | {line}\n")
                            except Exception as e:
                                logger.warning(f"Could not append to graph.log: {e}")
                            
                            logger.info(f"Queued command from web UI: {line[:80]}...")
                
                # If file shrunk (was cleared), reset position
                elif current_size < self.last_position:
                    self.last_position = 0
            except Exception as e:
                logger.error(f"Error processing {filepath}: {e}")
    
    logger.info(f"[FileWatcher] Started watching {filepath} for web UI submissions (inotify)")
    
    event_handler = UserInputHandler()
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=False)
    observer.start()
    
    try:
        while not stop_file_watcher.is_set():
            time.sleep(0.1)
    finally:
        observer.stop()
        observer.join()
    
    logger.info(f"Stopped watching {filepath}")


def get_pending_web_commands():
    """Get and clear all pending web UI commands."""
    with web_ui_commands_lock:
        commands = web_ui_commands.copy()
        web_ui_commands.clear()
    return commands


# Stderr capture for library messages ([CHAIR], [DEBUG], checkpoints)
import sys
import re

class StderrCapture:
    """Capture stderr messages and forward them to TUI display."""
    
    def __init__(self, original_stderr, tui_app=None):
        self.original_stderr = original_stderr
        self.tui_app = tui_app
        self.buffer = []
    
    def write(self, text):
        """Capture stderr writes and display in TUI."""
        if not text or text.isspace():
            return
        
        # Always write to original stderr (for debugging outside TUI if needed)
        # self.original_stderr.write(text)
        
        # Format and display in TUI if available
        if self.tui_app:
            self.tui_app.display_stderr_message(text)
    
    def flush(self):
        """Flush the stderr stream."""
        self.original_stderr.flush()


def highlight_mentions(text: str, state: dict = None) -> tuple:
    """Highlight @[...] mentions and XML with colors (ANSI version for log, Rich version for TUI).
    
    EXACT port from original main.py highlight_mentions():
    - Base text: light green (ANSI 92, Rich color(10))
    - @[User]: light blue (ANSI 94, Rich color(12))
    - @[Specialists in room]: light purple (ANSI 95, Rich color(13))
    - @[Specialists available]: red (ANSI 91, Rich color(9))
    - @[Search][query]: @[Search] light blue, [query] white
    - XML attributes:
      - query="value" → value white (ANSI 97, Rich color(15))
      - url/title/requester="value" → value dark grey (ANSI 90, Rich color(8))
    - <answer>content</answer> → content white
    - <result>content</result> → content light grey (ANSI 37, Rich color(7))
    
    Returns tuple: (ansi_colored_text, rich_markup_text)
    """
    import re
    import html
    
    # ANSI color codes (matching original colors.py exactly)
    DARK_GREEN = '\033[32m'
    LIGHT_GREEN = '\033[92m'
    LIGHT_BLUE = '\033[94m'
    CYAN = '\033[96m'
    LIGHT_PURPLE = '\033[95m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    WHITE = '\033[97m'
    DARK_GREY = '\033[90m'
    LIGHT_GREY = '\033[37m'
    RESET = '\033[0m'
    
    # Process ANSI version
    text_ansi = text
    text_rich = text
    
    # 1. Handle XML attribute values - color them based on attribute name
    # Pattern matches: attr_name="attr_value" (including XML entities in value)
    def replace_attribute_ansi(match):
        attr_name = match.group(1)
        attr_value = match.group(2)
        # Different colors for different attribute types
        if attr_name == 'query':
            color = WHITE  # Query in white for emphasis
        elif attr_name == 'requester':
            # Color based on who the requester is
            if attr_value == 'User':
                color = LIGHT_BLUE  # User in light blue
            else:
                color = LIGHT_PURPLE  # Specialists/tools in light purple
        else:
            color = DARK_GREY  # Other attributes (url, title) in dark grey (metadata)
        # Attribute name and equals in light green, value in specified color, then back to light green
        return f'{LIGHT_GREEN}{attr_name}="{RESET}{color}{attr_value}{RESET}{LIGHT_GREEN}"'
    
    def replace_attribute_rich(match):
        attr_name = match.group(1)
        attr_value = match.group(2)
        if attr_name == 'query':
            return f'{attr_name}="[color(15)]{attr_value}[/color(15)]"'  # WHITE
        elif attr_name == 'requester':
            # Color based on who the requester is
            if attr_value == 'User':
                return f'{attr_name}="[color(12)]{attr_value}[/color(12)]"'  # LIGHT_BLUE
            else:
                return f'{attr_name}="[color(13)]{attr_value}[/color(13)]"'  # LIGHT_PURPLE
        else:
            return f'{attr_name}="[color(8)]{attr_value}[/color(8)]"'  # DARK_GREY
    
    # Apply attribute replacements
    text_ansi = re.sub(r'(\w+)="((?:[^"&]|&(?:quot|amp|lt|gt);)*)"', replace_attribute_ansi, text_ansi)
    text_rich = re.sub(r'(\w+)="((?:[^"&]|&(?:quot|amp|lt|gt);)*)"', replace_attribute_rich, text_rich)
    
    # 2. Handle <answer>...</answer> tags - color content light grey, tags stay light green
    def replace_answer_ansi(match):
        content = match.group(1)
        return f'{LIGHT_GREEN}<answer>{LIGHT_GREY}{content}{RESET}{LIGHT_GREEN}</answer>'
    
    def replace_answer_rich(match):
        content = match.group(1)
        return f'<answer>[color(7)]{content}[/color(7)]</answer>'  # LIGHT_GREY
    
    text_ansi = re.sub(r'<answer>(.*?)</answer>', replace_answer_ansi, text_ansi, flags=re.DOTALL)
    text_rich = re.sub(r'<answer>(.*?)</answer>', replace_answer_rich, text_rich, flags=re.DOTALL)
    
    # 3. Handle <result>...</result> tags - color content light grey (supporting evidence)
    def replace_result_ansi(match):
        attributes = match.group(1)
        content = match.group(2)
        # Note: attributes already colored, ending with LIGHT_GREEN
        return f'{LIGHT_GREEN}<result{attributes}>{LIGHT_GREY}{content}{RESET}{LIGHT_GREEN}</result>'
    
    def replace_result_rich(match):
        attributes = match.group(1)
        content = match.group(2)
        return f'<result{attributes}>[color(7)]{content}[/color(7)]</result>'  # LIGHT_GREY
    
    text_ansi = re.sub(r'<result([^>]*)>(.*?)</result>', replace_result_ansi, text_ansi, flags=re.DOTALL)
    text_rich = re.sub(r'<result([^>]*)>(.*?)</result>', replace_result_rich, text_rich, flags=re.DOTALL)
    
    # 4. Handle @[Search][query] pattern specially
    def replace_search_ansi(match):
        query = match.group(1)
        # @[Search] in light blue, query in white (brackets stay light green)
        return f'{LIGHT_BLUE}@[Search]{RESET}{LIGHT_GREEN}[{WHITE}{query}{RESET}{LIGHT_GREEN}]'
    
    def replace_search_rich(match):
        query = match.group(1)
        # @[Search] in light blue (color 12), query in white (color 15)
        return f'[color(12)]@\\[Search][/color(12)]\\[[color(15)]{query}[/color(15)]]'
    
    text_ansi = re.sub(r'@\[Search\]\[([^\]]+)\]', replace_search_ansi, text_ansi, flags=re.IGNORECASE)
    text_rich = re.sub(r'@\[Search\]\[([^\]]+)\]', replace_search_rich, text_rich, flags=re.IGNORECASE)
    
    # 4.5. Handle @[Graph][...][...][...] patterns with colorization
    from axion_swarm.colors import colorize_graph_mentions, colorize_graph_mentions_rich
    text_ansi = colorize_graph_mentions(text_ansi)
    text_rich = colorize_graph_mentions_rich(text_rich)
    
    # 5. Handle regular @[...] mentions
    def replace_mention_ansi(match):
        mention = match.group(0)
        name = mention[2:-1]  # Remove @[ and ]
        decoded_name = html.unescape(name)
        
        # Special cases: User, tool references
        if decoded_name == 'User':
            return f'{LIGHT_BLUE}{mention}{RESET}{LIGHT_GREEN}'
        elif decoded_name in ['Search tool', 'ReadURL tool', 'Search', 'ReadURL']:
            return f'{LIGHT_BLUE}{mention}{RESET}{LIGHT_GREEN}'
        
        # All other mentions (specialists like "Context specialist", "Research specialist", etc.)
        # are colored light purple to distinguish them from User (light blue)
        return f'{LIGHT_PURPLE}{mention}{RESET}{LIGHT_GREEN}'
    
    def replace_mention_rich(match):
        mention = match.group(0)
        name = mention[2:-1]
        decoded_name = html.unescape(name)
        
        if decoded_name == 'User':
            return f'[color(12)]{mention}[/color(12)]'  # LIGHT_BLUE
        elif decoded_name in ['Search tool', 'ReadURL tool', 'Search', 'ReadURL']:
            return f'[color(12)]{mention}[/color(12)]'  # LIGHT_BLUE
        
        # All other mentions (specialists) in light purple
        return f'[color(13)]{mention}[/color(13)]'  # LIGHT_PURPLE
    
    # Apply mention replacements
    # Use negative lookahead to skip @[Graph] patterns (already handled by colorize_graph_mentions)
    text_ansi = re.sub(r'@\[(?!Graph\])[^\]]+\]', replace_mention_ansi, text_ansi)
    text_rich = re.sub(r'@\[(?!Graph\])[^\]]+\]', replace_mention_rich, text_rich)
    
    return (text_ansi, text_rich)


class MentionDetailModal(ModalScreen):
    """Modal screen to show full message context for a @[User] mention."""
    
    CSS = """
    MentionDetailModal {
        align: center middle;
    }
    
    #modal-container {
        width: 80%;
        height: 80%;
        background: $surface;
        border: thick $primary;
        padding: 1;
    }
    
    #modal-header {
        dock: top;
        height: 3;
        background: $boost;
        color: $text;
        content-align: center middle;
    }
    
    #modal-content {
        height: 1fr;
        border: solid $accent;
        background: $surface;
    }
    
    #modal-buttons {
        dock: bottom;
        height: 3;
        align: center middle;
    }
    
    #modal-buttons Button {
        margin: 0 1;
    }
    """
    
    def __init__(self, mention: dict, mention_index: int, on_remove_callback, app_ref):
        super().__init__()
        self.mention = mention
        self.mention_index = mention_index
        self.on_remove_callback = on_remove_callback
        self.app_ref = app_ref
    
    def compose(self) -> ComposeResult:
        """Create the modal layout with conditional Reply button."""
        with Container(id="modal-container"):
            yield Label(f"Message from {self.mention['speaker']}", id="modal-header")
            with VerticalScroll(id="modal-content"):
                yield RichLog(highlight=False, markup=True, wrap=True)
            with Horizontal(id="modal-buttons"):
                yield Button("Close (ESC)", variant="primary", id="close-btn")
                # Only show Reply button for questions
                if self.mention.get('is_question', False):
                    yield Button("Reply", variant="success", id="reply-btn")
                # Different label for questions vs statements
                remove_label = "Remove from To-Do" if self.mention.get('is_question', False) else "Acknowledge / Dismiss"
                yield Button(remove_label, variant="error", id="remove-btn")
    
    def on_mount(self) -> None:
        """Display the full message when mounted."""
        log = self.query_one("#modal-content RichLog")
        log.write(self.mention['original_message_full'])
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        if event.button.id == "close-btn":
            self.dismiss()
        elif event.button.id == "reply-btn":
            # Pre-populate input with specialist mention and dismiss
            speaker = self.mention['speaker']
            # Track that we're replying to this mention for auto-dismiss
            self.app_ref.pending_reply_to_mention = self.mention_index
            # Dismiss first, then set input value after modal is gone
            self.dismiss()
            # Use async approach to ensure proper timing
            async def set_input():
                await asyncio.sleep(0.05)  # Small delay to ensure modal is fully dismissed
                input_widget = self.app_ref.query_one("#input", Input)
                input_widget.focus()
                await asyncio.sleep(0.01)  # Tiny delay after focus
                input_widget.value = f"@[{speaker}], "
                input_widget.cursor_position = len(input_widget.value)  # Move cursor to end
            asyncio.create_task(set_input())
        elif event.button.id == "remove-btn":
            # Call the remove callback (async) and dismiss
            asyncio.create_task(self.on_remove_callback(self.mention_index))
            self.dismiss()
    
    def on_key(self, event) -> None:
        """Handle ESC key to close."""
        if event.key == "escape":
            self.dismiss()


class AxionSwarmTUI(App):
    """Interactive TUI for Axion Swarm with scrolling messages and bottom input."""
    
    CSS = """
    Horizontal {
        height: 1fr;
    }
    
    #sidebar {
        width: 30;
        border-right: solid $accent;
        background: $surface;
    }
    
    #sidebar.collapsed {
        width: 25;
    }
    
    #sidebar.expanded {
        width: 50%;
    }
    
    #sidebar-header {
        background: $boost;
        color: $text;
        padding: 0 1;
        text-align: center;
        dock: top;
    }
    
    #mentions-list {
        height: 1fr;
        border: none;
        background: $surface;
    }
    
    #mentions-list > ListItem {
        padding: 0 1;
    }
    
    #mentions-list > ListItem:hover {
        background: $boost;
    }
    
    #mentions-list > ListItem.--highlight {
        background: $primary;
    }
    
    #main-content {
        width: 1fr;
    }
    
    #messages-container {
        height: 1fr;
        border: solid $primary;
        background: $surface;
    }
    
    RichLog {
        height: 100%;
    }
    
    Input {
        border: solid $accent;
        height: 3;
        padding: 0 1;
    }
    
    #status {
        color: $warning;
        padding: 0 1;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("ctrl+d", "quit", "Quit", priority=True),
        ("f2", "toggle_sidebar", "Expand/Collapse To-Do"),
        ("pageup", "scroll_up", "Page Up"),
        ("pagedown", "scroll_down", "Page Down"),
        ("home", "scroll_home", "Top"),
        ("end", "scroll_end", "Bottom"),
    ]
    
    # Reactive property for sidebar state
    sidebar_expanded = reactive(False)
    
    def __init__(self, initial_state: OverallState):
        super().__init__()
        self.state = initial_state
        self.graph = None
        self.graph_task = None
        self.waiting_for_input = False
        self.need_graph_restart = False  # Flag for deferred graph restart after unblocking
        self.discussion_ended = False  # Track if graph has ended
        self.processing_phase = False  # Track if specialists are currently processing
        self.queued_messages = []  # Queue for messages sent during parallel processing
        self.user_mentions = []  # Track all @[User] mentions
        self.mention_count = 0  # Counter for mentions
        self.message_index = 0  # Track message order in main log
        self.message_positions = {}  # Map message_index -> approximate line count for scrolling
        self.pending_reply_to_mention = None  # Track which mention index we're replying to
        
        # Message length statistics for auto-collapse
        self.message_lengths = []  # Track ALL message lengths (very lightweight - just integers)
        self.collapsed_messages = {}  # Track collapsed state: {message_id: (full_tui, full_log, collapsed_tui, collapsed_log)}
        self.expanded_messages = set()  # Set of msg_ids that are currently expanded
        self.message_id_counter = 0  # Unique ID for each message
        self.displayed_message_count = 0  # Track how many messages from state we've already displayed
        
        # Capture stderr to display library messages in TUI
        self.original_stderr = sys.stderr
        self.stderr_capture = StderrCapture(self.original_stderr, tui_app=self)
        sys.stderr = self.stderr_capture
    
    def action_scroll_up(self) -> None:
        """Scroll the messages panel up by one page."""
        container = self.query_one("#messages-container", VerticalScroll)
        container.scroll_page_up()
    
    def action_scroll_down(self) -> None:
        """Scroll the messages panel down by one page."""
        container = self.query_one("#messages-container", VerticalScroll)
        container.scroll_page_down()
    
    def action_scroll_home(self) -> None:
        """Scroll to the top of messages."""
        container = self.query_one("#messages-container", VerticalScroll)
        container.scroll_home()
    
    def action_scroll_end(self) -> None:
        """Scroll to the bottom of messages."""
        container = self.query_one("#messages-container", VerticalScroll)
        container.scroll_end()
    
    def action_toggle_sidebar(self) -> None:
        """Toggle the @[User] mentions sidebar between collapsed and expanded."""
        self.sidebar_expanded = not self.sidebar_expanded
    
    async def remove_mention_by_index(self, index: int, auto_restart: bool = True) -> None:
        """Remove a @[User] mention from the sidebar by index.
        
        Args:
            index: Index of mention to remove
            auto_restart: If True, restart graph when unblocking. Set to False when called from reply context.
        """
        from langchain_core.messages import SystemMessage
        
        try:
            if index < len(self.user_mentions):
                removed_mention = self.user_mentions.pop(index)
                self.mention_count -= 1
                logger.info(f"Removed mention at index {index}: {removed_mention['content'][:50]}...")
                
                # Sort and re-render (no need to re-sort since we just removed, but re-render)
                self.sort_and_render_mentions()
                
                # Check if we should unblock discussion now that we removed this mention
                if self.waiting_for_input:
                    question_count = sum(1 for m in self.user_mentions if m.get('is_question', False))
                    
                    if question_count == 0:
                        # All questions cleared
                        current_phase = self.state.get("phase_number", 0)
                        next_phase = current_phase + 1
                        
                        # Unblock and restart based on context
                        if auto_restart:
                            # Direct dismissal - show debug message and notice now
                            messages_log = self.query_one("#messages", RichLog)
                            debug_msg = f"⚙️ [dim green]System state: UNBLOCKED | All questions resolved | Advancing: Phase {current_phase} → {next_phase}[/dim green]\n"
                            messages_log.write(debug_msg)
                            logger.info(f"[STATE] UNBLOCKED after manual dismiss - proceeding to Phase {next_phase}")
                            # Direct dismissal (not in reply context) - add notice, then unblock old graph
                            notice_msg = SystemMessage(
                                content=f"Notice: Discussion resuming. All questions addressed. Starting Phase {next_phase}.",
                                name="Notice",
                                additional_kwargs={
                                    "timestamp": datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
                                    "phase": current_phase
                                }
                            )
                            self.state["messages"].append(notice_msg)
                            await self.display_message(notice_msg)
                            # Update displayed_message_count since we displayed outside streaming context
                            self.displayed_message_count = len(self.state.get("messages", []))
                            
                            # The old graph is waiting at lines 882-883, it will continue when we unblock
                            self.waiting_for_input = False
                            logger.info(f"[GRAPH] Unblocking old graph to continue to Phase {next_phase}")
                        else:
                            # Reply context - DON'T add notice here (inject_user_message will add it AFTER user message)
                            # DON'T unblock old graph, just flag for new one
                            # The inject_user_message will handle the restart after adding user message
                            self.need_graph_restart = True
                            logger.info(f"[GRAPH] Flagged for restart after user message processed (keeping old graph blocked)")
        except Exception as e:
            logger.error(f"Error removing mention: {e}")
    
    def watch_sidebar_expanded(self, expanded: bool) -> None:
        """React to sidebar state changes and re-render all mentions."""
        try:
            sidebar = self.query_one("#sidebar", Vertical)
            
            logger.info(f"Sidebar state change: expanded={expanded}, mentions={len(self.user_mentions)}")
            
            if expanded:
                sidebar.remove_class("collapsed")
                sidebar.add_class("expanded")
            else:
                sidebar.remove_class("expanded")
                sidebar.add_class("collapsed")
            
            # Re-render all mentions with the new format (full or preview)
            # This also updates the header and maintains sorting
            self.sort_and_render_mentions()
        except Exception as e:
            logger.error(f"Error in watch_sidebar_expanded: {e}")
    
    def should_collapse_message(self, content: str, speaker: str) -> bool:
        """Determine if message should be auto-collapsed based on +2 sigma rule.
        
        Returns True if message length exceeds mean + 2*sigma of all messages.
        Tracks ALL messages (not just recent window) for accurate statistics.
        """
        import statistics
        
        content_length = len(content.encode('utf-8'))  # Byte length
        
        # Add to all-time tracking (very lightweight - just integers)
        self.message_lengths.append(content_length)
        
        # Need at least 10 messages to establish baseline
        if len(self.message_lengths) < 10:
            return False
        
        # Calculate statistics across ALL messages
        mean_length = statistics.mean(self.message_lengths)
        
        # Handle case where all messages are the same length (sigma = 0)
        try:
            sigma = statistics.stdev(self.message_lengths)
        except statistics.StatisticsError:
            sigma = 0
        
        # Collapse if > mean + 2*sigma
        threshold = mean_length + (2 * sigma)
        
        should_collapse = content_length > threshold
        
        # Log decision for debugging
        if should_collapse:
            logger.info(f"Auto-collapse: {speaker} message ({content_length} bytes) > threshold ({threshold:.0f} bytes, mean={mean_length:.0f}, sigma={sigma:.0f}, n={len(self.message_lengths)} messages)")
        
        return should_collapse
    
    def format_collapsed_message(self, content: str, speaker: str, timestamp_str: str, full_formatted_tui: str, full_formatted_log: str) -> tuple:
        """Format a message for collapsed display.
        
        Shows the full speaker line and first 2 lines of content, then collapse notice.
        
        Returns: (collapsed_tui, collapsed_log, message_id)
        """
        self.message_id_counter += 1
        msg_id = self.message_id_counter
        
        # Get first 2 lines of content for preview
        content_lines = content.split('\n')
        preview_lines = content_lines[:2]
        preview = '\n'.join(preview_lines)
        if len(content_lines) > 2:
            preview += "..."
        
        # Calculate stats
        content_bytes = len(content.encode('utf-8'))
        total_lines = len(content_lines)
        
        # Apply highlighting to preview
        preview_ansi, preview_rich = highlight_mentions(preview, self.state)
        
        # Format collapsed version with expand button
        # Keep the FULL speaker line (timestamp + emoji + speaker + "said:")
        # Then show first 2 lines of content
        collapsed_tui = (
            f"{full_formatted_tui.split('[/color(10)]')[0].split('[color(10)]')[0]}"  # Everything before content
            f"[color(10)]{preview_rich}[/color(10)]\n"
            f"[dim cyan]→ [{content_bytes} bytes, {total_lines} lines - collapsed] Type /expand {msg_id} to expand[/dim cyan]\n"
        )
        
        collapsed_log = (
            f"{full_formatted_log.split(content)[0]}"  # Everything before content (timestamp + speaker)
            f"{preview_ansi}\n"
            f"→ [{content_bytes} bytes, {total_lines} lines - collapsed] Message #{msg_id}\n"
        )
        
        # Store ALL versions for later expansion/collapse
        self.collapsed_messages[msg_id] = (full_formatted_tui, full_formatted_log, collapsed_tui, collapsed_log)
        
        return (collapsed_tui, collapsed_log, msg_id)
    
    def extract_user_mention_sentences(self, content: str) -> list:
        """Extract ALL sentences containing @[User] from content.
        
        Returns list of tuples: (sentence_text, is_question)
        where is_question=True if sentence contains '?'
        """
        import re
        
        # Split into sentences using sentence-ending punctuation only
        # Match sentence endings: . ? ! followed by space or end of string
        # DO NOT split on : or ; as they're internal punctuation (e.g., "@[User], question: details?")
        sentence_pattern = r'[^.!?]+[.!?]+\s*'
        sentences = re.findall(sentence_pattern, content)
        
        # If no sentences found with punctuation, treat whole content as one sentence
        if not sentences:
            sentences = [content]
        
        # Filter to only sentences containing @[User], and mark if they're questions
        user_mentions = [
            (s.strip(), '?' in s) for s in sentences 
            if '@[User]' in s
        ]
        
        return user_mentions
    
    def sort_and_render_mentions(self) -> None:
        """Sort mentions (questions first, then statements) and re-render the list."""
        # Sort: questions first (is_question=True), then statements (is_question=False)
        # Within each group, maintain insertion order (stable sort)
        self.user_mentions.sort(key=lambda m: (not m['is_question'], m['message_index']))
        
        # Re-render the list
        mentions_list = self.query_one("#mentions-list", ListView)
        mentions_list.clear()
        
        for mention in self.user_mentions:
            emoji = "❓" if mention['is_question'] else "❗"
            speaker = mention['speaker']
            content = mention['content']
            
            if self.sidebar_expanded:
                # Show full sentence when expanded
                item_content = Static(f"{emoji} {speaker}: {content}", markup=False)
                mentions_list.append(ListItem(item_content))
            else:
                # Show truncated preview when collapsed (first 20 chars)
                preview = content[:20] + "..." if len(content) > 20 else content
                item_content = Static(f"{emoji} {speaker}: {preview}", markup=False)
                mentions_list.append(ListItem(item_content))
        
        # Update header count
        header = self.query_one("#sidebar-header", Label)
        if self.sidebar_expanded:
            header.update(f"👤 @[User] Mentions ({self.mention_count})")
        else:
            header.update(f"👤 {self.mention_count}")
    
    def add_user_mention(self, speaker: str, content: str, timestamp_str: str, formatted_full: str, message_index: int) -> None:
        """Add message containing @[User] to the sidebar (one item per message)."""
        # Check if message contains @[User]
        if '@[User]' not in content:
            return  # No @[User] mentions found
        
        # Check if we've already added mentions from this message_index (prevent duplicates)
        if any(m['message_index'] == message_index for m in self.user_mentions):
            logger.info(f"Skipping duplicate @[User] mention from message_index {message_index}")
            return
        
        # Check if there's a '?' AFTER the @[User] mention
        # Question (❓) if '?' appears after @[User], otherwise statement (❗)
        user_mention_pos = content.find('@[User]')
        text_after_user = content[user_mention_pos:]
        has_question_mark = '?' in text_after_user
        
        # Add ONE entry per message (not per sentence)
        self.mention_count += 1
        
        # Use the full message content (no sentence splitting)
        content_ansi, content_rich = highlight_mentions(content, self.state)
        
        # Store for re-rendering when toggling sidebar
        self.user_mentions.append({
            'speaker': speaker,
            'content': content,  # Full message content
            'timestamp': timestamp_str,
            'formatted_full': formatted_full,  # Full formatted message (for modal)
            'original_message_full': formatted_full,  # ENTIRE original message (for click handler)
            'message_index': message_index,  # Track which message this came from
            'is_question': has_question_mark  # True if message contains '?' anywhere
        })
        
        # Sort and re-render the entire list (questions first, then statements)
        self.sort_and_render_mentions()
    
    def display_stderr_message(self, text: str) -> None:
        """Display a captured stderr message with appropriate colors.
        
        Handles:
        - [CHAIR] messages → yellow
        - [DEBUG] messages → no color (plain)
        - Checkpoint messages (💾, ✅, 🗑️, ⚠️) → no color (plain)
        - Error messages → yellow
        """
        import re
        
        # ANSI color codes
        YELLOW = '\033[93m'
        RESET = '\033[0m'
        
        # Strip any existing ANSI codes from library (if yellow() was already applied)
        text_clean = re.sub(r'\033\[[0-9;]+m', '', text)
        text_clean = text_clean.rstrip()
        
        if not text_clean:
            return
        
        # Check message type and format accordingly
        if '[CHAIR]' in text_clean:
            # Yellow for CHAIR messages (internal system)
            tui_formatted = f"⚙️  [color(11)]{text_clean}[/color(11)]"  # YELLOW with gear
            log_formatted = f"⚙️  {YELLOW}{text_clean}{RESET}\n"
        elif '[DEBUG]' in text_clean:
            # Plain text for DEBUG (internal system)
            tui_formatted = f"⚙️  {text_clean}"
            log_formatted = f"⚙️  {text_clean}\n"
        elif any(emoji in text_clean for emoji in ['💾', '✅', '🗑️', '⚠️', '❌']):
            # Plain text for checkpoint/status messages (internal system)
            tui_formatted = f"⚙️  {text_clean}"
            log_formatted = f"⚙️  {text_clean}\n"
        elif '## ❌ Error' in text_clean or 'Error:' in text_clean:
            # Yellow for errors (matches original)
            tui_formatted = f"⚙️ [color(11)]{text_clean}[/color(11)]"  # YELLOW with gear emoji
            log_formatted = f"⚙️ {YELLOW}{text_clean}{RESET}\n"
        elif text_clean.startswith('=') or text_clean.startswith('─'):
            # Plain text for separators/borders
            tui_formatted = f"⚙️ {text_clean}"
            log_formatted = f"⚙️ {text_clean}\n"
        else:
            # Default: plain text
            tui_formatted = f"⚙️ {text_clean}"
            log_formatted = f"⚙️ {text_clean}\n"
        
        # Display in TUI
        try:
            messages_log = self.query_one("#messages", RichLog)
            messages_log.write(tui_formatted)
        except:
            pass  # TUI not ready yet
        
        # Log to file
        logger.info(log_formatted)
    
    def compose(self) -> ComposeResult:
        """Create the UI layout with collapsible sidebar."""
        yield Header(show_clock=True)
        
        with Horizontal():
            # Left sidebar: @[User] mentions (collapsible, clickable)
            with Vertical(id="sidebar", classes="collapsed"):
                yield Label("👤 0", id="sidebar-header")
                yield ListView(id="mentions-list")
            
            # Main content area: full conversation
            with Vertical(id="main-content"):
                with VerticalScroll(id="messages-container"):
                    yield RichLog(id="messages", wrap=True, highlight=False, markup=True)
        
        # Custom Input that allows Ctrl+C and Ctrl+D to bubble up for quit
        input_widget = Input(
            placeholder="Type your message here...",
            id="input"
        )
        yield input_widget
        yield Footer()
    
    def on_key(self, event) -> None:
        """Handle key events to allow Ctrl+C and Ctrl+D to quit from any focused widget."""
        if event.key in ("ctrl+c", "ctrl+d"):
            # Quit immediately - don't let Input or other widgets capture these
            self.action_quit()
            event.stop()  # Prevent further processing
    
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle mention selection - show modal with full message."""
        # Get the selected item's index
        mentions_list = self.query_one("#mentions-list", ListView)
        selected_index = mentions_list.index
        
        if selected_index is not None and selected_index < len(self.user_mentions):
            mention = self.user_mentions[selected_index]
            
            logger.info(f"Mention selected: index={selected_index}, speaker={mention.get('speaker')}")
            
            # Show modal with full message (Reply button will handle input pre-population)
            self.push_screen(MentionDetailModal(mention, selected_index, self.remove_mention_by_index, self))
    
    async def on_mount(self) -> None:
        """Initialize when app starts."""
        logger.info("=== TUI Starting ===")
        self.graph = create_swarm_graph()
        messages_log = self.query_one("#messages", RichLog)
        welcome_msg = "[bold cyan]🤖 Axion Swarm - Interactive Discussion[/bold cyan]\n"
        messages_log.write(welcome_msg)
        logger.info(welcome_msg)
        
        # Start periodic check for web UI commands (every 200ms)
        self.set_interval(0.2, self.check_web_commands)
        
        # Start graph execution
        self.graph_task = asyncio.create_task(self.run_graph())
    
    def check_web_commands(self) -> None:
        """Periodically check for and display pending web UI commands."""
        web_commands = get_pending_web_commands()
        if web_commands:
            from langchain_core.messages import AIMessage
            from datetime import datetime
            
            messages_log = self.query_one("#messages", RichLog)
            current_phase = self.state.get("phase_number", 1)
            
            for cmd in web_commands:
                # Check for special system commands
                if cmd == "@[System][ContinuePhase]":
                    # User clicked "Continue to Next Phase" in web UI
                    logger.info(f"[Web UI] User clicked Continue Phase - unblocking phase progression")
                    messages_log.write(f"[bold blue][Web UI][/bold blue] [green]User clicked Continue to Next Phase[/green]\n")
                    
                    # Unblock phase progression
                    if self.waiting_for_input:
                        self.waiting_for_input = False
                        logger.info(f"[STATE] UNBLOCKED - continuing to next phase")
                        
                        # Update phase status file
                        import json
                        try:
                            is_final = self.state.get("final_phase_needed") or self.state.get("final_phase_done")
                            with open('phase_status.json', 'w') as f:
                                json.dump({
                                    'waiting': False,
                                    'phase': current_phase,
                                    'is_final': is_final
                                }, f)
                        except Exception as e:
                            logger.warning(f"Could not update phase_status.json: {e}")
                    
                    continue  # Don't add this to state messages
                
                # Regular graph command - add as proper User message to state (so specialists see it)
                user_timestamp = datetime.now().astimezone().isoformat(timespec='milliseconds')
                user_msg = AIMessage(
                    content=cmd,
                    name="User",
                    additional_kwargs={"phase": current_phase, "timestamp": user_timestamp}
                )
                
                # Append to state messages
                existing_messages = self.state.get("messages", [])
                self.state["messages"] = existing_messages + [user_msg]
                
                # Display in TUI
                messages_log.write(f"[bold blue][Web UI][/bold blue] [green]{cmd}[/green]\n")
                logger.info(f"[Web UI] {cmd}")
                
                # Update displayed message count so we don't re-display this message
                self.displayed_message_count = len(self.state.get("messages", []))
    
    def on_unmount(self) -> None:
        """Cleanup when app exits."""
        # Stop file watcher thread
        stop_file_watcher.set()
        # Restore original stderr
        sys.stderr = self.original_stderr
        logger.info("=== TUI Exiting ===")
    
    async def run_graph(self) -> None:
        """Run the LangGraph and stream outputs to the UI."""
        try:
            logger.info(f"Starting graph execution for user_goal: {self.state.get('user_goal', 'N/A')}")
            config = {"recursion_limit": 10000}
            
            messages_log = self.query_one("#messages", RichLog)
            
            # Show initial processing notice
            start_msg = "⚙️ [dim italic]Starting discussion processing...[/dim italic]\n"
            messages_log.write(start_msg)
            logger.info("⚙️ Starting discussion processing...")
            
            # FIX: Use .astream() instead of .stream() to avoid asyncio.run() error
            async for output in self.graph.astream(self.state, config):
                # Update state from graph output
                for node_name, node_output in output.items():
                    logger.info(f"[STREAM] Node '{node_name}' yielded output with keys: {list(node_output.keys()) if node_output else 'None'}")
                    if node_output and "messages" in node_output:
                        num_msgs_in_output = len(node_output["messages"])
                        logger.info(f"[STREAM] Node '{node_name}' returned {num_msgs_in_output} message(s)")
                        
                        # Track state changes
                        old_phase = self.state.get("phase_number", 0)
                        
                        # CRITICAL FIX: Properly merge messages using add_messages semantics
                        # node_output["messages"] contains only NEW messages from this node
                        # We need to APPEND them to existing messages, not replace
                        new_state = dict(self.state)
                        if "messages" in node_output:
                            # Append new messages to existing messages
                            existing_messages = self.state.get("messages", [])
                            new_state["messages"] = existing_messages + node_output["messages"]
                        # Update other fields
                        for key, value in node_output.items():
                            if key != "messages":
                                new_state[key] = value
                        self.state = new_state
                        
                        new_phase = self.state.get("phase_number", 0)
                        
                        # Only display NEW messages (ones we haven't shown yet)
                        all_messages = self.state.get("messages", [])
                        new_messages = all_messages[self.displayed_message_count:]
                        logger.info(f"[STREAM] Total messages in state: {len(all_messages)}, New messages to display: {len(new_messages)}, displayed_message_count was: {self.displayed_message_count}")
                        self.displayed_message_count = len(all_messages)
                        
                        for msg in new_messages:
                            msg_speaker = msg.name if hasattr(msg, 'name') else "Unknown"
                            logger.info(f"[STREAM] Displaying message from: {msg_speaker}")
                            await self.display_message(msg)
                        
                        # Update phase status when phase number changes
                        if node_name == "start_phase":
                            import json
                            phase = self.state.get("phase_number", 0)
                            is_final = self.state.get("final_phase_needed") or self.state.get("final_phase_done")
                            
                            try:
                                with open('phase_status.json', 'w') as f:
                                    json.dump({
                                        'waiting': False,
                                        'phase': phase,
                                        'is_final': is_final
                                    }, f)
                                logger.info(f"[STATE] Updated phase status: Phase {phase} started (final={is_final})")
                            except Exception as e:
                                logger.warning(f"Could not update phase_status.json: {e}")
                        
                        # Check if we should pause IMMEDIATELY after execute_phase (before next phase starts)
                        if node_name == "execute_phase":
                            phase = self.state.get("phase_number", 0)
                            is_final = self.state.get("final_phase_needed") or self.state.get("final_phase_done")
                            
                            # Pause after every phase (except final) for user to review and continue via web UI
                            if not is_final:
                                logger.info(f"[STATE] Phase {phase} complete - pausing for user to review (continue via web UI)")
                                if not self.waiting_for_input:
                                    await self.pause_for_input()
                                # Wait until user continues (via web UI "Continue" button or TUI input)
                                while self.waiting_for_input:
                                    await asyncio.sleep(0.1)
                                logger.info(f"[STATE] User signaled continue - advancing to next phase")
            
            # Graph ended naturally
            is_final = self.state.get("final_phase_done", False)
            
            if is_final:
                # Final phase complete and no pending questions - show completion message
                messages_log = self.query_one("#messages", RichLog)
                completion_msg = "[yellow]Type a message to continue discussion, or /quit to exit[/yellow]"
                messages_log.write(completion_msg)
                logger.info(completion_msg)
                self.discussion_ended = True
            else:
                # Not final phase and no questions - graph stopped early (shouldn't happen normally)
                # Just silently wait for optional user input
                logger.info(f"[STATE] Discussion ended before final phase. No pending questions. Waiting for optional user input.")
                self.discussion_ended = True
            
        except Exception as e:
            messages_log = self.query_one("#messages", RichLog)
            error_msg = f"\n[bold red]❌ Error: {e}[/bold red]"
            messages_log.write(error_msg)
            logger.error(error_msg)
            
            import traceback
            tb = traceback.format_exc()
            tb_formatted = f"[red]{tb}[/red]"
            messages_log.write(tb_formatted)
            logger.error(tb_formatted)
    
    async def display_message(self, msg) -> None:
        """Display a message in the scrolling log.
        
        Uses EXACT same color scheme as original main.py:
        - Timestamp: white
        - Labels: cyan
        - Content: LIGHT_GREEN (base color) with @mentions highlighted
        - Search tool label: bright_blue
        """
        messages_log = self.query_one("#messages", RichLog)
        
        # ANSI color codes (matching original colors.py exactly)
        LIGHT_GREEN = '\033[92m'
        CYAN = '\033[96m'
        LIGHT_BLUE = '\033[94m'
        WHITE = '\033[97m'
        RESET = '\033[0m'
        
        speaker = msg.name if hasattr(msg, 'name') else "System"
        
        # Get timestamp (format: YYYY-MM-DD HH:MM:SS.mmm TZ like original)
        if hasattr(msg, 'additional_kwargs') and 'timestamp' in msg.additional_kwargs:
            timestamp_iso = msg.additional_kwargs['timestamp']
            dt = datetime.fromisoformat(timestamp_iso)
            # Match original format EXACTLY: YYYY-MM-DD HH:MM:SS.mmm TZ
            timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " " + dt.astimezone().strftime("%Z")
        else:
            now = datetime.now().astimezone()
            timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " " + now.strftime("%Z")
        
        # Format content (collapse whitespace for display, but preserve newlines inside ``` blocks)
        import re
        
        # Preserve content inside ``` blocks by temporarily replacing with placeholders
        backtick_blocks = []
        def save_backtick_block(match):
            backtick_blocks.append(match.group(0))
            return f"___BACKTICK_BLOCK_{len(backtick_blocks)-1}___"
        
        # Extract all ``` blocks (including the backticks themselves)
        content = msg.content
        content = re.sub(r'```.*?```', save_backtick_block, content, flags=re.DOTALL)
        
        # Now collapse whitespace in the non-backtick parts
        content = content.replace('\n', ' ').replace('\r', ' ')
        content = re.sub(r'\s+', ' ', content).strip()
        
        # Restore the ``` blocks with their original formatting
        for i, block in enumerate(backtick_blocks):
            content = content.replace(f"___BACKTICK_BLOCK_{i}___", block)
        
        # Apply highlight_mentions to color @mentions
        content_ansi, content_rich = highlight_mentions(content, self.state)
        
        # Build TWO versions:
        # 1. Rich markup for TUI display
        # 2. ANSI codes for log file (matches original main.py output exactly)
        
        # Use numeric color codes to match ANSI exactly:
        # color(10) = ANSI 92 (bright green/light green)
        # color(14) = ANSI 96 (cyan) 
        # color(15) = ANSI 97 (white/bright white)
        # color(12) = ANSI 94 (bright blue)
        
        if speaker == "Notice":
            # Extract "Notice:" prefix if present (like original)
            if content.startswith("Notice:"):
                notice_content = content[7:].strip()
                notice_content_ansi, notice_content_rich = highlight_mentions(notice_content, self.state)
                # TUI version - add newline at end to match original spacing
                formatted_tui = f"[color(15)]\\[{timestamp_str}][/color(15)] 📢 [color(14)]Notice:[/color(14)] [color(10)]{notice_content_rich}[/color(10)]\n"
                # Log version (ANSI codes - content in LIGHT_GREEN with highlights)
                formatted_log = f"{WHITE}[{timestamp_str}]{RESET} 📢 {CYAN}Notice:{RESET} {LIGHT_GREEN}{notice_content_ansi}{RESET}\n"
            else:
                formatted_tui = f"[color(15)]\\[{timestamp_str}][/color(15)] 📢 [color(10)]{content_rich}[/color(10)]\n"
                formatted_log = f"{WHITE}[{timestamp_str}]{RESET} 📢 {LIGHT_GREEN}{content_ansi}{RESET}\n"
        elif speaker == "User":
            formatted_tui = f"[color(15)]\\[{timestamp_str}][/color(15)] 💬 [color(14)]User:[/color(14)] [color(10)]{content_rich}[/color(10)]\n"
            formatted_log = f"{WHITE}[{timestamp_str}]{RESET} 💬 {CYAN}User:{RESET} {LIGHT_GREEN}{content_ansi}{RESET}\n"
        elif speaker == "Search tool":
            # Original: light_blue label, light_green content with highlights
            formatted_tui = f"[color(15)]\\[{timestamp_str}][/color(15)] 🔍 [color(12)]Search tool:[/color(12)] [color(10)]{content_rich}[/color(10)]\n"
            formatted_log = f"{WHITE}[{timestamp_str}]{RESET} 🔍 {LIGHT_BLUE}Search tool:{RESET} {LIGHT_GREEN}{content_ansi}{RESET}\n"
        elif speaker == "ReadURL tool":
            # Newspaper emoji for reading/fetching content
            formatted_tui = f"[color(15)]\\[{timestamp_str}][/color(15)] 📰 [color(12)]ReadURL tool:[/color(12)] [color(10)]{content_rich}[/color(10)]\n"
            formatted_log = f"{WHITE}[{timestamp_str}]{RESET} 📰 {LIGHT_BLUE}ReadURL tool:{RESET} {LIGHT_GREEN}{content_ansi}{RESET}\n"
        elif speaker == "Chair":
            # Original: cyan label with "said:", light_green content with highlights
            formatted_tui = f"[color(15)]\\[{timestamp_str}][/color(15)] ⚖️ [color(14)]Chair said:[/color(14)] [color(10)]{content_rich}[/color(10)]\n"
            formatted_log = f"{WHITE}[{timestamp_str}]{RESET} ⚖️ {CYAN}Chair said:{RESET} {LIGHT_GREEN}{content_ansi}{RESET}\n"
        else:
            # All other specialists: robot emoji + cyan label with "said:", light_green content with highlights
            formatted_tui = f"[color(15)]\\[{timestamp_str}][/color(15)] 🤖 [color(14)]{speaker} said:[/color(14)] [color(10)]{content_rich}[/color(10)]\n"
            formatted_log = f"{WHITE}[{timestamp_str}]{RESET} 🤖 {CYAN}{speaker} said:{RESET} {LIGHT_GREEN}{content_ansi}{RESET}\n"
        
        # Track message index for mention references
        current_msg_index = self.message_index
        self.message_index += 1
        
        # Check if message should be auto-collapsed (based on +2 sigma rule)
        if self.should_collapse_message(content, speaker):
            formatted_tui_collapsed, formatted_log_collapsed, msg_id = self.format_collapsed_message(
                content, speaker, timestamp_str, formatted_tui, formatted_log
            )
            # Write collapsed version
            messages_log.write(formatted_tui_collapsed)
            logger.info(formatted_log_collapsed)
        else:
            # Write full message
            messages_log.write(formatted_tui)
            logger.info(formatted_log)
        
        # Check if message contains @[User] mention - add to sidebar
        if '@[User]' in content:
            self.add_user_mention(speaker, content, timestamp_str, formatted_tui, current_msg_index)
    
    async def pause_for_input(self) -> None:
        """Show pause message and wait for user."""
        from langchain_core.messages import SystemMessage
        import json
        
        messages_log = self.query_one("#messages", RichLog)
        current_phase = self.state.get("phase_number", 0)
        
        # Only show notice if we're transitioning from unblocked → blocked
        if not self.waiting_for_input:
            # Show Notice about waiting for user to continue via web UI
            debug_msg = f"⚙️ [dim green]System state: WAITING_FOR_USER | Phase: {current_phase}[/dim green]\n"
            messages_log.write(debug_msg)
            logger.info(f"[STATE] WAITING_FOR_USER - Phase {current_phase} complete, waiting for user to continue")
            
            notice_msg = SystemMessage(
                content=f"Notice: Phase {current_phase} complete. Review decisions in the web UI and click 'Continue to Next Phase' to proceed.",
                name="Notice",
                additional_kwargs={
                    "timestamp": datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
                    "phase": current_phase
                }
            )
            self.state["messages"].append(notice_msg)
            await self.display_message(notice_msg)
            # Update displayed_message_count since we displayed outside streaming context
            self.displayed_message_count = len(self.state.get("messages", []))
        
        self.waiting_for_input = True
        
        # Update phase status file for web UI
        try:
            is_final = self.state.get("final_phase_needed") or self.state.get("final_phase_done")
            with open('phase_status.json', 'w') as f:
                json.dump({
                    'waiting': True,
                    'phase': current_phase,
                    'is_final': is_final
                }, f)
        except Exception as e:
            logger.warning(f"Could not update phase_status.json: {e}")
        
        # Focus the input
        input_widget = self.query_one("#input", Input)
        input_widget.focus()
    
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input from the bottom panel."""
        text = event.value.strip()
        
        # Clear the input field
        event.input.value = ""
        
        if not text:
            return
        
        logger.info(f"User input received: {text}")
        messages_log = self.query_one("#messages", RichLog)
        
        # Check if this was a reply to a mention - auto-dismiss it
        if self.pending_reply_to_mention is not None:
            logger.info(f"Auto-dismissing mention at index {self.pending_reply_to_mention}")
            await self.remove_mention_by_index(self.pending_reply_to_mention, auto_restart=False)
            self.pending_reply_to_mention = None
            
            # Log remaining questions
            question_count = sum(1 for m in self.user_mentions if m.get('is_question', False))
            logger.info(f"Remaining questions after auto-dismiss: {question_count}")
        
        # Handle commands
        if text.startswith("/"):
            await self.handle_command(text)
        else:
            # Regular message - inject as User message (will handle continue logic)
            await self.inject_user_message(text)
    
    async def handle_command(self, command: str) -> None:
        """Handle slash commands."""
        logger.info(f"Command executed: {command}")
        messages_log = self.query_one("#messages", RichLog)
        
        if command == "/continue":
            if self.waiting_for_input:
                self.waiting_for_input = False
                msg = "[green]▶️  Continuing to next phase...[/green]\n"
                messages_log.write(msg)
                logger.info(msg)
            else:
                msg = "[yellow]⚠️  Not waiting for input (discussion is ongoing)[/yellow]"
                messages_log.write(msg)
                logger.info(msg)
        
        elif command == "/quit":
            msg = "[yellow]👋 Goodbye![/yellow]"
            messages_log.write(msg)
            logger.info(msg)
            await asyncio.sleep(0.5)
            self.exit()
        
        elif command == "/status":
            phase = self.state.get("phase_number", 0)
            presence = self.state.get("specialist_presence", {})
            in_room = [k.title() for k, v in presence.items() if v == "in"]
            
            status_lines = [
                "[bold]Status:[/bold]",
                f"  Phase: {phase}",
                f"  Specialists in room: {', '.join(in_room) if in_room else 'None'}",
                f"  Total messages: {len(self.message_lengths)}",
                f"  Collapsed messages: {len(self.collapsed_messages)}",
                f"  @[User] mentions: {self.mention_count}"
            ]
            for line in status_lines:
                messages_log.write(line)
                logger.info(line)
        
        elif command.startswith("/expand"):
            # Handle /expand <message_id>
            parts = command.split()
            if len(parts) == 2 and parts[1].isdigit():
                msg_id = int(parts[1])
                if msg_id in self.collapsed_messages:
                    full_tui, full_log, collapsed_tui, collapsed_log = self.collapsed_messages[msg_id]
                    messages_log.write(f"\n[bold cyan]📖 Expanding message #{msg_id}:[/bold cyan]\n")
                    messages_log.write(full_tui)
                    messages_log.write(f"[dim cyan]→ Type /collapse {msg_id} to re-collapse this message[/dim cyan]\n")
                    logger.info(f"\n📖 Expanding message #{msg_id}:\n")
                    logger.info(full_log)
                    # Mark as expanded
                    self.expanded_messages.add(msg_id)
                else:
                    error_msg = f"[red]❌ Message #{msg_id} not found or not collapsed[/red]"
                    messages_log.write(error_msg)
                    logger.info(error_msg)
            else:
                error_msg = "[red]Usage: /expand <message_id>[/red]"
                messages_log.write(error_msg)
                logger.info(error_msg)
        
        elif command.startswith("/collapse"):
            # Handle /collapse <message_id>
            parts = command.split()
            if len(parts) == 2 and parts[1].isdigit():
                msg_id = int(parts[1])
                if msg_id in self.collapsed_messages:
                    full_tui, full_log, collapsed_tui, collapsed_log = self.collapsed_messages[msg_id]
                    messages_log.write(f"\n[bold cyan]📕 Collapsing message #{msg_id}:[/bold cyan]\n")
                    messages_log.write(collapsed_tui)
                    logger.info(f"\n📕 Collapsing message #{msg_id}:\n")
                    logger.info(collapsed_log)
                    # Mark as collapsed (remove from expanded set)
                    self.expanded_messages.discard(msg_id)
                else:
                    error_msg = f"[red]❌ Message #{msg_id} not found[/red]"
                    messages_log.write(error_msg)
                    logger.info(error_msg)
            else:
                error_msg = "[red]Usage: /collapse <message_id>[/red]"
                messages_log.write(error_msg)
                logger.info(error_msg)
        
        elif command == "/help":
            help_lines = [
                "[bold]Available Commands:[/bold]",
                "  [cyan]/continue[/cyan] - Proceed to next phase",
                "  [cyan]/status[/cyan] - Show current phase and specialists",
                "  [cyan]/expand <id>[/cyan] - Expand a collapsed message",
                "  [cyan]/collapse <id>[/cyan] - Re-collapse an expanded message",
                "  [cyan]/quit[/cyan] - Exit the discussion",
                "  [cyan]/help[/cyan] - Show this help",
                "",
                "[bold]Keybindings:[/bold]",
                "  [cyan]F2[/cyan] - Expand/Collapse User To-Do sidebar",
                "  [cyan]Page Up/Down[/cyan] - Scroll by page",
                "  [cyan]Home/End[/cyan] - Jump to top/bottom",
                "",
                "[bold]Features:[/bold]",
                "  • Messages >2σ from mean are auto-collapsed",
                "  • @[User] mentions shown in left sidebar (F2)",
                "  • Click mention to view full context in modal",
                "  • Modal buttons: Reply (questions), Acknowledge/Dismiss (statements)",
                "  • All messages and errors logged to discussion.log",
                "",
                "Or type any message to send to the team"
            ]
            for line in help_lines:
                messages_log.write(line)
                logger.info(line)
        
        else:
            error_lines = [
                f"[red]❌ Unknown command: {command}[/red]",
                "[dim]Type /help for available commands[/dim]"
            ]
            for line in error_lines:
                messages_log.write(line)
                logger.info(line)
    
    async def inject_user_message(self, text: str) -> None:
        """Inject a user message into the discussion."""
        from langchain_core.messages import SystemMessage
        
        logger.info(f"Injecting user message: {text}")
        messages_log = self.query_one("#messages", RichLog)
        current_phase = self.state.get("phase_number", 0)
        
        # Create user message
        user_msg = HumanMessage(
            content=text,
            name="User",
            additional_kwargs={
                "timestamp": datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
                "phase": current_phase
            }
        )
        
        # Add to state
        self.state["messages"].append(user_msg)
        
        # Display immediately - NEVER block user feedback
        await self.display_message(user_msg)
        # Update displayed_message_count since we displayed outside streaming context
        self.displayed_message_count = len(self.state.get("messages", []))
        
        # Check if we need to invalidate final phase and add Notice
        if self.state.get("final_phase_needed") or self.state.get("final_phase_done"):
            # RESET TO PHASE 3: Phase number represents "transition to resolution"
            # Phase 1-2 = far from resolution, Phase 3+ = moving toward resolution
            # User input after final phase means NOT at resolution anymore → back to Phase 3
            reset_phase = 3
            
            # Step 1: Force Chair to synthesize the entire conversation so far
            # This creates a compression point for the new Phase 3
            logger.info("[PHASE RESET] Requesting Chair synthesis before reset...")
            synthesis_request_msg = SystemMessage(
                content=f"Notice: User has provided additional input after final phase. @[Chair], please provide a COMPREHENSIVE SYNTHESIS of the entire conversation so far (all phases) before we reset to Phase {reset_phase}. Include: all key points from all specialists, important questions raised, areas of agreement/disagreement, critical concerns and recommendations. Your synthesis will serve as the compressed summary for the new discussion phase.",
                name="Notice",
                additional_kwargs={
                    "timestamp": datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
                    "phase": current_phase
                }
            )
            self.state["messages"].append(synthesis_request_msg)
            await self.display_message(synthesis_request_msg)
            
            # Step 2: Invoke Chair to create the synthesis
            # Import here to avoid circular dependency
            from axion_swarm.agents import chair_agent
            chair_result = await asyncio.get_event_loop().run_in_executor(
                None, chair_agent, self.state
            )
            
            # Add Chair's synthesis to messages
            if "messages" in chair_result and chair_result["messages"]:
                for msg in chair_result["messages"]:
                    self.state["messages"].append(msg)
                    await self.display_message(msg)
                
                # Set compression point to the last Chair message
                self.state["last_compression_message_index"] = len(self.state["messages"]) - 1
                logger.info(f"[PHASE RESET] Compression point set to message index {self.state['last_compression_message_index']}")
            
            # Step 3: Add reset notice and clear final phase flags
            notice_msg = SystemMessage(
                content=f"Notice: Resetting to Phase {reset_phase} (iterative discussion mode). Prior conversation compressed to Chair's synthesis above.",
                name="Notice",
                additional_kwargs={
                    "timestamp": datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
                    "phase": current_phase
                }
            )
            self.state["messages"].append(notice_msg)
            await self.display_message(notice_msg)
            # Update displayed_message_count since we displayed outside streaming context
            self.displayed_message_count = len(self.state.get("messages", []))
            
            # Clear final phase flags and reset phase number
            self.state["final_phase_needed"] = False
            self.state["final_phase_done"] = False
            self.state["phase_number"] = reset_phase - 1  # Will be incremented to 3 by start_phase
        
        # If discussion ended, restart it
        if self.discussion_ended:
            self.discussion_ended = False
            self.state["continue_discussion"] = True
            msg = "[green]▶️  Restarting discussion with your input...[/green]\n"
            messages_log.write(msg)
            logger.info(msg)
            # Restart graph with updated state
            self.graph_task = asyncio.create_task(self.run_graph())
        # Check if we need deferred graph restart (from auto-dismiss unblock in reply context)
        # This takes priority over waiting_for_input check to avoid double restart
        elif self.need_graph_restart:
            # Deferred restart was flagged by remove_mention_by_index in reply context
            # User message was already added above - now add the resuming notice AFTER it
            self.need_graph_restart = False
            
            # Add resuming notice (after user message)
            next_phase = current_phase + 1
            debug_msg = f"⚙️ [dim green]System state: UNBLOCKED | All questions resolved | Advancing: Phase {current_phase} → {next_phase}[/dim green]\n"
            messages_log.write(debug_msg)
            logger.info(f"[STATE] UNBLOCKED after user reply - proceeding to Phase {next_phase}")
            
            notice_msg = SystemMessage(
                content=f"Notice: Discussion resuming. All questions addressed. Starting Phase {next_phase}.",
                name="Notice",
                additional_kwargs={
                    "timestamp": datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
                    "phase": current_phase
                }
            )
            self.state["messages"].append(notice_msg)
            await self.display_message(notice_msg)
            # Update displayed_message_count since we displayed outside streaming context
            self.displayed_message_count = len(self.state.get("messages", []))
            
            # Cancel the old graph task cleanly before starting new one
            if self.graph_task and not self.graph_task.done():
                logger.info(f"[GRAPH] Cancelling old graph task before starting new one")
                self.graph_task.cancel()
                try:
                    await self.graph_task
                except asyncio.CancelledError:
                    pass  # Expected
            self.waiting_for_input = False  # Clear the flag
            logger.info(f"[GRAPH] Starting new graph after user reply")
            self.graph_task = asyncio.create_task(self.run_graph())
        # If we were waiting, check if we should continue now
        elif self.waiting_for_input:
            # Check if there are still pending questions
            question_count = sum(1 for m in self.user_mentions if m.get('is_question', False))
            
            if question_count > 0:
                # Still have questions - stay in waiting state (no notice, user already knows)
                logger.info(f"[STATE] WAITING_FOR_USER - {question_count} questions remain after user message")
            else:
                # All questions resolved - continue to next phase
                self.waiting_for_input = False
                next_phase = current_phase + 1
                
                # Debug output for internal state change
                debug_msg = f"⚙️  [dim green]System state: UNBLOCKED | All questions resolved | Advancing: Phase {current_phase} → {next_phase}[/dim green]\n"
                messages_log.write(debug_msg)
                logger.info(f"[STATE] UNBLOCKED - proceeding to Phase {next_phase}")
                
                notice_msg = SystemMessage(
                    content=f"Notice: Discussion resuming. All questions addressed. Starting Phase {next_phase}.",
                    name="Notice",
                    additional_kwargs={
                        "timestamp": datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
                        "phase": current_phase
                    }
                )
                self.state["messages"].append(notice_msg)
                await self.display_message(notice_msg)
                # Update displayed_message_count since we displayed outside streaming context
                self.displayed_message_count = len(self.state.get("messages", []))
                
                # CRITICAL: Restart the graph to actually move to the next phase
                logger.info(f"[GRAPH] Restarting graph to continue to Phase {next_phase}")
                self.graph_task = asyncio.create_task(self.run_graph())
        
        # Always re-focus input after sending message
        input_widget = self.query_one("#input", Input)
        input_widget.focus()


def create_initial_state(user_goal: str) -> OverallState:
    """Create initial state for new discussion."""
    user_goal = user_goal.strip().strip('"').strip("'")
    
    return {
        "messages": [],
        "user_goal": user_goal,
        "phase_number": 0,
        "agents_remaining": [],
        "continue_discussion": True,
        "final_phase_needed": False,
        "final_phase_done": False,
        "specialist_presence": initialize_specialist_presence(),
        "last_compression_message_index": -1,
        "rate_limit_compression_pending": False,
        "interactive_mode": True,  # Interactive TUI mode - User can send messages at any phase
    }


def main():
    """Entry point for TUI."""
    import sys
    
    # Start file watcher thread for web UI submissions
    watcher_thread = threading.Thread(target=watch_user_input_file, daemon=True)
    watcher_thread.start()
    
    print("=" * 80)
    print("# 🤖 Axion Swarm - Interactive TUI")
    print("=" * 80)
    print(f"📝 Logging transcript and errors to: {log_file.absolute()}")
    print()
    
    # Check for checkpoint
    if checkpoint_exists():
        print("📂 Checkpoint file found!")
        resume = input("Resume from checkpoint? (y/n): ").strip().lower()
        
        if resume in ('y', 'yes'):
            checkpoint_state = load_checkpoint()
            if checkpoint_state:
                print(f"✅ Resuming from Phase {checkpoint_state['phase_number']}")
                print("=" * 80)
                app = AxionSwarmTUI(checkpoint_state)
                app.run()
                return
            else:
                print("❌ Checkpoint is incompatible with current code.")
                delete_checkpoint()
                print("   Starting fresh conversation\n")
        else:
            delete_checkpoint()
            print("🗑️  Starting fresh conversation\n")
    
    # Check for any pending web UI commands before starting
    web_commands = get_pending_web_commands()
    if web_commands:
        print(f"[Web UI] Found {len(web_commands)} pending command(s):")
        for cmd in web_commands:
            print(f"  {cmd[:100]}...")
        print()
    
    # Get user goal
    user_goal = input("Enter your discussion topic: ").strip()
    
    if not user_goal:
        print("No goal provided. Exiting.")
        return
    
    print()
    
    # Create state and run
    initial_state = create_initial_state(user_goal)
    app = AxionSwarmTUI(initial_state)
    app.run()


if __name__ == "__main__":
    main()

