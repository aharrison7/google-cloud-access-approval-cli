#!/usr/bin/env python3

import curses
import curses.panel
from typing import List, Dict, Optional
from datetime import datetime

class RequestViewer:
    def __init__(self, requests: List[Dict]):
        self.requests = requests
        self.current_index = 0
        self.top_line = 0
        self.window = None
        self.detail_window = None
        self.status_window = None

    def create_windows(self, stdscr):
        """Initialize the curses windows."""
        height, width = curses.LINES, curses.COLS

        # Initialize color pairs
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Selected item
        curses.init_pair(2, curses.COLOR_WHITE, -1)  # Normal text
        curses.init_pair(3, curses.COLOR_BLUE, -1)   # Headers

        # Create main window for request list (1/3 of screen width)
        list_width = max(30, min(width // 3, 50))  # Increased minimum width
        self.window = curses.newwin(height - 2, list_width, 0, 0)
        if self.window:
            self.window.keypad(True)

        # Create detail window (remaining width)
        detail_width = width - list_width
        self.detail_window = curses.newwin(height - 2, detail_width, 0, list_width)

        # Create status window at bottom
        self.status_window = curses.newwin(2, width, height - 2, 0)

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

    def format_timestamp(self, timestamp: str) -> str:
        """Format API timestamp to human-readable format."""
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        except ValueError:
            return timestamp

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

        self.window.clear()
        self.window.box()
        height, width = self.window.getmaxyx()

        # Display header
        header = " Requests "
        self.safe_addstr(self.window, 0, (width - len(header)) // 2, header, 
                        curses.color_pair(3) | curses.A_BOLD)

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

    def display_request_details(self, request: Dict):
        """Display detailed information about the selected request."""
        if not self.detail_window:
            return

        self.detail_window.clear()
        self.detail_window.box()
        height, width = self.detail_window.getmaxyx()

        # Display header
        header = " Request Details "
        self.safe_addstr(self.detail_window, 0, (width - len(header)) // 2, header, 
                        curses.color_pair(3) | curses.A_BOLD)

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

    def display_status(self):
        """Display status and help information."""
        if not self.status_window:
            return

        self.status_window.clear()
        self.status_window.box()
        status_text = "↑/↓: Navigate | q: Quit | a: Approve | d: Dismiss | r: Revoke"
        self.safe_addstr(self.status_window, 0, 2, status_text, curses.A_BOLD)
        self.status_window.refresh()

    def run(self, stdscr) -> Optional[Dict]:
        """Run the interactive viewer."""
        try:
            curses.curs_set(0)  # Hide cursor
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
            curses.endwin()

def view_requests(requests: List[Dict]) -> Optional[Dict]:
    """
    Launch the interactive viewer for the requests.
    Returns a dict with 'action' and 'request' if user selects an action,
    or None if user quits.
    """
    viewer = RequestViewer(requests)
    return curses.wrapper(lambda stdscr: viewer.run(stdscr))