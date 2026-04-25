"""
Cloud tracking engine for TaskTimer.
Uses API client instead of local database.
"""

import threading
import time
from datetime import datetime
from typing import Callable, List, Optional
from enum import Enum

from desktop_client.api_client import TaskTimerAPIClient
from core.idle_detector import IdleDetector
from core.app_monitor import AppMonitor, ActiveWindow


class TrackingStatus(Enum):
    """Status of time tracking."""
    STOPPED = "stopped"
    ACTIVE = "active"
    IDLE = "idle"
    PAUSED = "paused"


class CloudTrackingEngine:
    """
    Cloud-based tracking engine that communicates with FastAPI backend.

    Implements the strict tracking logic:
    IF task_active == TRUE
    AND current_app IN allowed_apps
    AND user_status == ACTIVE
    THEN increment timer
    ELSE pause timer
    """

    def __init__(self, api_client: TaskTimerAPIClient):
        """
        Initialize cloud tracking engine.

        Args:
            api_client: API client instance
        """
        self.api = api_client
        self.idle_detector = IdleDetector(idle_threshold=60.0)
        self.app_monitor = AppMonitor()

        self._current_task: Optional[dict] = None
        self._current_session: Optional[dict] = None
        self._allowed_apps: List[str] = []
        self._status = TrackingStatus.STOPPED
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Tracking state
        self._session_duration: float = 0.0
        self._last_app_check: Optional[float] = None
        self._current_window: Optional[ActiveWindow] = None
        self._last_sent_duration: float = 0.0  # Track last duration sent to server

        # Callbacks
        self._status_callbacks: List[Callable[[TrackingStatus], None]] = []
        self._time_callbacks: List[Callable[[float], None]] = []
        self._app_callbacks: List[Callable[[Optional[ActiveWindow]], None]] = []

        # Setup idle detector callback
        self.idle_detector.add_callback(self._on_idle_state_change)

    def add_status_callback(self, callback: Callable[[TrackingStatus], None]):
        """Add callback for status changes."""
        with self._lock:
            self._status_callbacks.append(callback)

    def add_time_callback(self, callback: Callable[[float], None]):
        """Add callback for time updates."""
        with self._lock:
            self._time_callbacks.append(callback)

    def add_app_callback(self, callback: Callable[[Optional[ActiveWindow]], None]):
        """Add callback for app changes."""
        with self._lock:
            self._app_callbacks.append(callback)

    def _notify_status(self, status: TrackingStatus):
        """Notify all status callbacks."""
        for callback in self._status_callbacks:
            try:
                callback(status)
            except Exception:
                pass

    def _notify_time(self, duration: float):
        """Notify all time callbacks."""
        for callback in self._time_callbacks:
            try:
                callback(duration)
            except Exception:
                pass

    def _notify_app(self, window: Optional[ActiveWindow]):
        """Notify all app callbacks."""
        for callback in self._app_callbacks:
            try:
                callback(window)
            except Exception:
                pass

    def _on_idle_state_change(self, is_idle: bool):
        """Handle idle state change from idle detector."""
        with self._lock:
            if self._status == TrackingStatus.STOPPED:
                return

            if is_idle and self._status == TrackingStatus.ACTIVE:
                self._status = TrackingStatus.IDLE
                self._notify_status(TrackingStatus.IDLE)
            elif not is_idle and self._status == TrackingStatus.IDLE:
                # Check if we should resume
                if self._current_window and self.app_monitor.is_app_allowed(
                    self._current_window.app_name, self._allowed_apps
                ):
                    self._status = TrackingStatus.ACTIVE
                    self._notify_status(TrackingStatus.ACTIVE)

    def _check_app_allowed(self) -> bool:
        """Check if current app is allowed."""
        window = self.app_monitor.get_active_window()
        self._current_window = window

        if not window:
            return False

        self._notify_app(window)
        return self.app_monitor.is_app_allowed(window.app_name, self._allowed_apps)

    def _tracking_loop(self):
        """Main tracking loop."""
        last_update = time.time()

        while self._running:
            time.sleep(0.1)  # 100ms update interval

            with self._lock:
                if not self._running or self._status == TrackingStatus.STOPPED:
                    continue

                current_time = time.time()
                elapsed = current_time - last_update
                last_update = current_time

                # Check app status every second
                if current_time - (self._last_app_check or 0) >= 1.0:
                    self._last_app_check = current_time
                    app_allowed = self._check_app_allowed()

                    if not app_allowed and self._status == TrackingStatus.ACTIVE:
                        self._status = TrackingStatus.PAUSED
                        self._notify_status(TrackingStatus.PAUSED)
                    elif app_allowed and self._status == TrackingStatus.PAUSED:
                        if not self.idle_detector.is_idle():
                            self._status = TrackingStatus.ACTIVE
                            self._notify_status(TrackingStatus.ACTIVE)

                # Only increment time if status is ACTIVE
                if self._status == TrackingStatus.ACTIVE:
                    self._session_duration += elapsed
                    self._notify_time(self._session_duration)

                    # Update server periodically (every 5 seconds)
                    if int(self._session_duration) % 5 == 0 and self._current_session:
                        try:
                            # Calculate delta (incremental time since last update)
                            delta = self._session_duration - self._last_sent_duration
                            if delta > 0:
                                self.api.update_session(
                                    self._current_session["id"],
                                    {
                                        "duration": self._session_duration,
                                        "delta": delta,  # Send incremental time
                                        "status": self._status.value,
                                        "current_app": self._current_window.app_name if self._current_window else None,
                                        "idle_time": self.idle_detector.get_idle_time()
                                    }
                                )
                                self._last_sent_duration = self._session_duration
                        except Exception:
                            pass

    def start_tracking(self, task_id: str) -> bool:
        """
        Start tracking for a task.

        Args:
            task_id: ID of task to track

        Returns:
            True if tracking started successfully, False otherwise
        """
        with self._lock:
            if self._running:
                return False

            # Get task
            try:
                task = self.api.get_task(task_id)
            except Exception:
                return False

            if not task:
                return False

            # Get allowed apps
            self._allowed_apps = task.get("allowed_apps", [])
            if not self._allowed_apps:
                return False

            self._current_task = task
            self._session_duration = 0.0
            self._last_sent_duration = 0.0
            self._last_app_check = None
            self._current_window = None

            # Create session
            try:
                session = self.api.create_session(task_id)
                self._current_session = session
            except Exception:
                return False

            # Start session on server
            try:
                self.api.start_session(session["id"])
            except Exception:
                pass

            # Start idle detector
            self.idle_detector.start()

            # Start tracking thread
            self._running = True
            self._thread = threading.Thread(target=self._tracking_loop, daemon=True)
            self._thread.start()

            # Set initial status
            self._status = TrackingStatus.ACTIVE
            self._notify_status(TrackingStatus.ACTIVE)

            return True

    def stop_tracking(self) -> bool:
        """
        Stop current tracking session.

        Returns:
            True if tracking stopped successfully, False otherwise
        """
        with self._lock:
            if not self._running:
                return False

            self._running = False

            # Stop idle detector
            self.idle_detector.stop()

            # Wait for thread to finish
            if self._thread:
                self._thread.join(timeout=2)
                self._thread = None

            # Stop session on server
            if self._current_session:
                try:
                    # Calculate final delta
                    final_delta = self._session_duration - self._last_sent_duration
                    self.api.update_session(
                        self._current_session["id"],
                        {
                            "duration": self._session_duration,
                            "delta": final_delta,
                            "status": "stopped"
                        }
                    )
                    self.api.stop_session(self._current_session["id"])
                except Exception:
                    pass

            # Reset state
            self._status = TrackingStatus.STOPPED
            self._notify_status(TrackingStatus.STOPPED)

            task = self._current_task
            session = self._current_session
            duration = self._session_duration

            self._current_task = None
            self._current_session = None
            self._allowed_apps = []
            self._session_duration = 0.0
            self._last_sent_duration = 0.0
            self._last_app_check = None
            self._current_window = None

            return True

    def get_status(self) -> TrackingStatus:
        """Get current tracking status."""
        with self._lock:
            return self._status

    def get_current_task(self) -> Optional[dict]:
        """Get currently tracked task."""
        with self._lock:
            return self._current_task

    def get_session_duration(self) -> float:
        """Get current session duration in seconds."""
        with self._lock:
            return self._session_duration

    def get_current_window(self) -> Optional[ActiveWindow]:
        """Get current active window."""
        with self._lock:
            return self._current_window

    def get_current_session(self) -> Optional[dict]:
        """Get current session."""
        with self._lock:
            return self._current_session

    def get_live_link(self) -> Optional[str]:
        """Get live viewing link for current session."""
        with self._lock:
            if self._current_session:
                return self.api.get_live_link(self._current_session["share_token"])
            return None

    def set_idle_threshold(self, threshold: float):
        """Set idle detection threshold in seconds."""
        self.idle_detector.set_idle_threshold(threshold)

    def get_idle_threshold(self) -> float:
        """Get idle detection threshold in seconds."""
        return self.idle_detector.idle_threshold

    def get_idle_time(self) -> float:
        """Get current idle time in seconds."""
        return self.idle_detector.get_idle_time()

    def is_running(self) -> bool:
        """Check if tracking is currently running."""
        with self._lock:
            return self._running

    def shutdown(self):
        """Shutdown tracking engine."""
        self.stop_tracking()
