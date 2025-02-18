#!/usr/bin/env python3

import curses
import curses.panel
from typing import List, Dict, Optional
from datetime import datetime
import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RequestViewer:
    def __init__(self, requests: List[Dict]):
        self.requests = requests
        self.current_index = 0
        self.top_line = 0
        self.window = None
        self.detail_window = None
        self.status_window = None
        self.min_terminal_height = 10
        self.min_terminal_width = 80

    def check_terminal_size(self):
        """Check if terminal meets minimum size requirements."""
        height, width = curses.LINES, curses.COLS
        if height < self.min_terminal_height or width < self.min_terminal_width:
            raise Exception(
                f"Terminal too small. Minimum size: {self.min_terminal_width}x{self.min_terminal_height}, "
                f"Current size: {width}x{height}"
            )

    def create_windows(self, stdscr):
        """Initialize the curses windows."""
        try:
            # Set up terminal
            os.environ.setdefault('ESCDELAY', '25')  # Reduce escape key delay
            curses.noecho()  # Don't echo keystrokes
            curses.cbreak()  # React to keys instantly

            # Enable terminal cursor visibility control
            try:
                curses.curs_set(0)  # Hide cursor
            except Exception:
                logger.debug("Terminal doesn't support cursor visibility control")

            # Check terminal capabilities
            if not curses.has_colors():
                logger.warning("Terminal does not support colors, using fallback mode")

            # Check terminal size
            self.check_terminal_size()

            height, width = curses.LINES, curses.COLS
            logger.debug(f"Terminal size: {width}x{height}")

            # Initialize color pairs if supported
            if curses.has_colors():
                try:
                    curses.start_color()
                    curses.use_default_colors()
                    for i in range(1, 4):
                        curses.init_pair(i, i, -1)
                except Exception as e:
                    logger.warning(f"Failed to initialize colors: {e}")

            # Create main window for request list (1/3 of screen width)
            list_width = max(30, min(width // 3, 50))
            self.window = curses.newwin(height - 2, list_width, 0, 0)
            if not self.window:
                raise Exception("Failed to create main window")
            self.window.keypad(True)

            # Create detail window (remaining width)
            detail_width = width - list_width
            self.detail_window = curses.newwin(height - 2, detail_width, 0, list_width)
            if not self.detail_window:
                raise Exception("Failed to create detail window")

            # Create status window at bottom
            self.status_window = curses.newwin(2, width, height - 2, 0)
            if not self.status_window:
                raise Exception("Failed to create status window")

            # Initial refresh of all windows
            stdscr.clear()
            stdscr.refresh()
            self.window.refresh()
            self.detail_window.refresh()
            self.status_window.refresh()

        except Exception as e:
            logger.error(f"Failed to initialize windows: {e}")
            self.clean_up()
            raise

    def clean_up(self):
        """Clean up curses windows and restore terminal state."""
        try:
            if self.window:
                self.window.keypad(False)
                self.window.clear()
                self.window.refresh()
            if self.detail_window:
                self.detail_window.clear()
                self.detail_window.refresh()
            if self.status_window:
                self.status_window.clear()
                self.status_window.refresh()

            # Reset terminal settings
            try:
                curses.nocbreak()
                curses.echo()
                curses.endwin()
            except Exception as e:
                logger.debug(f"Error during terminal cleanup: {e}")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def format_timestamp(self, timestamp: str) -> str:
        """Format API timestamp to human-readable format."""
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        except ValueError:
            return timestamp

    def safe_addstr(self, window, y: int, x: int, text: str, attr=0):
        """Safely add a string to a window, handling boundaries and errors."""
        if not window:
            return

        try:
            height, width = window.getmaxyx()
            if y < 0 or x < 0 or y >= height or x >= width:
                return

            # Truncate text if it would exceed window width
            max_len = width - x
            if len(text) > max_len:
                text = text[:max_len-3] + "..."

            window.addstr(y, x, text, attr)
        except curses.error:
            pass

    def wrap_text(self, text: str, width: int) -> List[str]:
        """Wrap text to fit within specified width."""
        if not text:
            return []

        lines = []
        while text:
            if len(text) <= width:
                lines.append(text)
                break
            split_point = text.rfind(' ', 0, width)
            if split_point == -1:
                split_point = width
            lines.append(text[:split_point])
            text = text[split_point:].lstrip()
        return lines

    def display_request_list(self):
        """Display the list of requests in the main window."""
        if not self.window:
            return

        try:
            self.window.clear()
            self.window.box()
            height, width = self.window.getmaxyx()

            # Display header
            header = " Requests "
            self.safe_addstr(self.window, 0, (width - len(header)) // 2, header, 
                            curses.color_pair(3) | curses.A_BOLD)

            # If no requests, display message
            if not self.requests:
                message = "No requests found"
                y_pos = height // 2
                x_pos = (width - len(message)) // 2
                self.safe_addstr(self.window, y_pos, x_pos, message)
                self.window.refresh()
                return

            # Calculate available space for list items
            list_height = height - 2  # Account for borders
            list_width = width - 4    # Account for borders and padding

            # Display requests
            for i in range(min(list_height, len(self.requests))):
                idx = i + self.top_line
                if idx >= len(self.requests):
                    break

                request = self.requests[idx]
                # Get the request ID (last part of the name)
                name = request.get('name', 'N/A').split('/')[-1]

                # Format display text
                display_text = f" {name} "
                if len(display_text) > list_width:
                    display_text = display_text[:list_width-3] + "..."

                # Clear line first
                self.window.move(i + 1, 1)
                self.window.clrtoeol()

                # Highlight selected item
                attr = curses.color_pair(1) if idx == self.current_index else curses.color_pair(2)

                # Fill entire line width for better highlighting
                padding = " " * (list_width - len(display_text))
                self.safe_addstr(self.window, i + 1, 1, display_text + padding, attr)

            self.window.refresh()
        except curses.error:
            pass

    def display_request_details(self, request: Dict):
        """Display detailed information about the selected request."""
        if not self.detail_window:
            return

        try:
            self.detail_window.clear()
            self.detail_window.box()
            height, width = self.detail_window.getmaxyx()

            # Display header
            header = " Request Details "
            self.safe_addstr(self.detail_window, 0, (width - len(header)) // 2, header, 
                            curses.color_pair(3) | curses.A_BOLD)

            # If no request, display message
            if not request:
                message = "No request selected"
                y_pos = height // 2
                x_pos = (width - len(message)) // 2
                self.safe_addstr(self.detail_window, y_pos, x_pos, message)
                self.detail_window.refresh()
                return

            y = 1
            indent = 2
            content_width = width - 2 * indent  # Double indent for better readability

            # Define sections with their content
            sections = [
                ("Basic Information", [
                    ("Name", request.get('name', 'N/A')),
                    ("State", request.get('state', 'N/A')),
                    ("Request Time", self.format_timestamp(request.get('requestTime', 'N/A')))
                ]),
                ("Resource Details", [
                    ("Resource", request.get('requestedResourceName', 'N/A'))
                ]),
                ("Request Context", [
                    ("Type", request.get('requestedReason', {}).get('type', 'N/A')),
                    ("Detail", request.get('requestedReason', {}).get('detail', 'N/A'))
                ])
            ]

            # Add locations if present
            locations = request.get('requestedLocations', {})
            if locations:
                location_items = []
                for key, value in locations.items():
                    formatted_key = key.replace('principal', 'Principal ').replace('Country', ' Country')
                    location_items.append((formatted_key, value))
                if location_items:
                    sections.append(("Locations", location_items))

            # Display each section
            for section_title, items in sections:
                if y >= height - 2:
                    break

                # Display section header
                self.safe_addstr(self.detail_window, y, indent, section_title + ":", 
                            curses.color_pair(3) | curses.A_BOLD)
                y += 1

                # Display items in section
                for label, value in items:
                    if y >= height - 2:
                        break

                    # Format the label
                    label_text = f"{label}: "
                    self.safe_addstr(self.detail_window, y, indent + 2, label_text)

                    # Handle multiline values
                    value_indent = indent + 2 + len(label_text)
                    available_width = content_width - len(label_text)
                    wrapped_lines = self.wrap_text(str(value), available_width)

                    for i, line in enumerate(wrapped_lines):
                        if y >= height - 2:
                            break
                        if i == 0:
                            self.safe_addstr(self.detail_window, y, value_indent, line)
                        else:
                            self.safe_addstr(self.detail_window, y, value_indent, line)
                        y += 1

                    if not wrapped_lines:  # If value was empty
                        y += 1

                y += 1  # Add space between sections

            self.detail_window.refresh()
        except curses.error:
            pass

    def display_status(self):
        """Display status and help information."""
        if not self.status_window:
            return

        try:
            self.status_window.clear()
            self.status_window.box()
            status_text = "↑/↓: Navigate | q: Quit | a: Approve | d: Dismiss | r: Revoke"
            self.safe_addstr(self.status_window, 0, 2, status_text, curses.A_BOLD)
            self.status_window.refresh()
        except curses.error:
            pass

    def run(self, stdscr) -> Optional[Dict]:
        """Run the interactive viewer."""
        try:
            self.create_windows(stdscr)

            while True:
                try:
                    if self.window:
                        self.display_request_list()
                        if self.requests:
                            self.display_request_details(self.requests[self.current_index])
                        self.display_status()

                        # Handle key input
                        key = self.window.getch()
                        if key == ord('q'):
                            return None
                        elif key == curses.KEY_UP and self.current_index > 0:
                            self.current_index -= 1
                            if self.current_index < self.top_line:
                                self.top_line = self.current_index
                        elif key == curses.KEY_DOWN and self.current_index < len(self.requests) - 1:
                            self.current_index += 1
                            if self.current_index >= self.top_line + (curses.LINES - 4):
                                self.top_line += 1
                        elif key in [ord('a'), ord('d'), ord('r')] and self.requests:
                            action = {
                                ord('a'): 'approve',
                                ord('d'): 'dismiss',
                                ord('r'): 'revoke'
                            }[key]
                            return {
                                'action': action,
                                'request': self.requests[self.current_index]
                            }

                except curses.error:
                    continue

        except KeyboardInterrupt:
            return None
        finally:
            self.clean_up()

    def update_requests(self, new_requests: List[Dict]):
        """Update the request list and reset indexes if necessary."""
        self.requests = new_requests
        # Reset indexes if they're now out of bounds
        if self.current_index >= len(new_requests):
            self.current_index = max(0, len(new_requests) - 1)
        if self.top_line >= len(new_requests):
            self.top_line = max(0, len(new_requests) - 1)

def view_requests(requests: List[Dict]) -> Optional[Dict]:
    """
    Launch the interactive viewer for the requests.
    Returns a dict with 'action' and 'request' if user selects an action,
    or None if user quits.
    """
    try:
        logger.debug("Initializing interactive viewer")
        viewer = RequestViewer(requests)
        return curses.wrapper(lambda stdscr: viewer.run(stdscr))
    except Exception as e:
        logger.error(f"Error in interactive viewer: {e}")
        return None