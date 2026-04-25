"""
Idle detection module for TaskTimer.
Detects keyboard and mouse activity to determine user presence.
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Callable, Optional

try:
    from pynput import keyboard, mouse
except ImportError:
    raise ImportError(
        "pynput is required. Install it with: pip install pynput"
    )


class IdleDetector:
    """Detects user activity and idle state."""

    def __init__(self, idle_threshold: float = 60.0):
        """
        Initialize idle detector.

        Args:
            idle_threshold: Seconds of inactivity before considering user idle (default: 60)
        """
        self.idle_threshold = idle_threshold
        self._last_activity = datetime.now()
        self._is_idle = False
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._callbacks: list[Callable[[bool], None]] = []

        # Activity listeners
        self._keyboard_listener: Optional[keyboard.Listener] = None
        self._mouse_listener: Optional[mouse.Listener] = None

    def add_callback(self, callback: Callable[[bool], None]):
        """
        Add a callback to be called when idle state changes.

        Args:
            callback: Function that receives True when idle, False when active
        """
        with self._lock:
            self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[bool], None]):
        """Remove a callback."""
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    def _on_activity(self):
        """Handle any user activity."""
        with self._lock:
            was_idle = self._is_idle
            self._last_activity = datetime.now()
            self._is_idle = False

            if was_idle:
                # Notify callbacks that user is no longer idle
                for callback in self._callbacks:
                    try:
                        callback(False)
                    except Exception:
                        pass

    def _on_key_press(self, key):
        """Handle keyboard activity."""
        self._on_activity()

    def _on_mouse_move(self, x, y):
        """Handle mouse movement."""
        self._on_activity()

    def _on_mouse_click(self, x, y, button, pressed):
        """Handle mouse click."""
        if pressed:
            self._on_activity()

    def _on_mouse_scroll(self, x, y, dx, dy):
        """Handle mouse scroll."""
        self._on_activity()

    def _monitor_idle(self):
        """Background thread to monitor idle state."""
        while self._running:
            time.sleep(1)  # Check every second

            with self._lock:
                idle_time = (datetime.now() - self._last_activity).total_seconds()
                is_now_idle = idle_time >= self.idle_threshold

                if is_now_idle and not self._is_idle:
                    self._is_idle = True
                    # Notify callbacks that user is now idle
                    for callback in self._callbacks:
                        try:
                            callback(True)
                        except Exception:
                            pass

    def start(self):
        """Start idle detection."""
        with self._lock:
            if self._running:
                return

            self._running = True
            self._last_activity = datetime.now()
            self._is_idle = False

        # Start activity listeners
        self._keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press
        )
        self._mouse_listener = mouse.Listener(
            on_move=self._on_mouse_move,
            on_click=self._on_mouse_click,
            on_scroll=self._on_mouse_scroll
        )

        self._keyboard_listener.start()
        self._mouse_listener.start()

        # Start idle monitoring thread
        self._thread = threading.Thread(target=self._monitor_idle, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop idle detection."""
        with self._lock:
            if not self._running:
                return

            self._running = False

        # Stop listeners
        if self._keyboard_listener:
            self._keyboard_listener.stop()
            self._keyboard_listener = None

        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None

        # Wait for thread to finish
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    def is_idle(self) -> bool:
        """Check if user is currently idle."""
        with self._lock:
            return self._is_idle

    def get_idle_time(self) -> float:
        """Get current idle time in seconds."""
        with self._lock:
            return (datetime.now() - self._last_activity).total_seconds()

    def get_last_activity(self) -> datetime:
        """Get timestamp of last activity."""
        with self._lock:
            return self._last_activity

    def set_idle_threshold(self, threshold: float):
        """
        Update idle threshold.

        Args:
            threshold: New idle threshold in seconds
        """
        with self._lock:
            self.idle_threshold = threshold
