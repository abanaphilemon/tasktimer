"""
Tracking engine for TaskTimer.
Core logic for time tracking with auto-pause/resume.
"""

import threading
import time
from datetime import datetime
from enum import Enum
from typing import Callable, List, Optional

from database import DatabaseHandler, Task
from core.idle_detector import IdleDetector
from core.app_monitor import AppMonitor, ActiveWindow


class TrackingStatus(Enum):
    """Status of time tracking."""
    STOPPED = "stopped"
    ACTIVE = "active"
    IDLE = "idle"
    PAUSED = "paused"


class TrackingEngine:
    """
    Core tracking engine that manages time tracking logic.

    Implements the strict tracking logic:
    IF task_active == TRUE
    AND current_app IN allowed_apps
    AND user_status == ACTIVE
    THEN increment timer
    ELSE pause timer
    """

    def __init__(self, db_handler: Optional[DatabaseHandler] = None):
        """
        Initialize tracking engine.

        Args:
            db_handler: Database handler instance (creates new if None)
        """
        self.db = db_handler or DatabaseHandler()
        self.idle_detector = IdleDetector(idle_threshold=60.0)
        self.app_monitor = AppMonitor()

        self._current_task: Optional[Task] = None
        self._allowed_apps: List[str] = []
        self._status = TrackingStatus.STOPPED
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Tracking state
        self._current_log_id: Optional[int] = None
        self._session_start: Optional[datetime] = None
        self._session_duration: float = 0.0
        self._last_app_check: Optional[float] = None
        self._current_window: Optional[ActiveWindow] = None
        self._app_durations: dict = {}  # Track time spent on each app
        self._last_app_log_time: Optional[float] = None  # Track last time we logged app usage

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

                    # Track time spent on current app
                    if self._current_window:
                        app_name = self._current_window.app_name
                        if app_name not in self._app_durations:
                            self._app_durations[app_name] = 0.0
                        self._app_durations[app_name] += elapsed

                    # Update database periodically (every 5 seconds)
                    if int(self._session_duration) % 5 == 0 and self._current_log_id:
                        try:
                            self.db.update_time_log(
                                self._current_log_id,
                                duration=self._session_duration
                            )
                        except Exception:
                            pass

                    # Log app usage periodically (every 5 seconds)
                    if int(self._session_duration) % 5 == 0 and self._current_window and self._current_task:
                        try:
                            # Log time for current app
                            app_name = self._current_window.app_name
                            if app_name in self._app_durations and self._app_durations[app_name] > 0:
                                # Log the accumulated time for this app
                                self.db.log_app_usage(
                                    self._current_task.id,
                                    app_name,
                                    self._app_durations[app_name]
                                )
                                # Reset the counter for this app
                                self._app_durations[app_name] = 0.0
                        except Exception:
                            pass

    def start_tracking(self, task_id: int) -> bool:
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
            task = self.db.get_task(task_id)
            if not task:
                return False

            # Get allowed apps
            self._allowed_apps = [app.app_name for app in self.db.get_allowed_apps(task_id)]
            if not self._allowed_apps:
                return False

            self._current_task = task
            self._session_start = datetime.now()
            self._session_duration = 0.0
            self._last_app_check = None
            self._current_window = None
            self._app_durations = {}  # Reset app durations
            self._last_app_log_time = None

            # Create time log
            log = self.db.create_time_log(task_id, status='active')
            self._current_log_id = log.id

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

            # Finalize time log
            if self._current_log_id:
                try:
                    self.db.update_time_log(
                        self._current_log_id,
                        end_time=datetime.now(),
                        duration=self._session_duration,
                        status='completed'
                    )
                except Exception:
                    pass

            # Log remaining app usage for all apps
            if self._app_durations and self._current_task:
                try:
                    for app_name, app_duration in self._app_durations.items():
                        if app_duration > 0:
                            self.db.log_app_usage(
                                self._current_task.id,
                                app_name,
                                app_duration
                            )
                except Exception:
                    pass

            # Reset state
            self._status = TrackingStatus.STOPPED
            self._notify_status(TrackingStatus.STOPPED)

            task = self._current_task
            duration = self._session_duration

            self._current_task = None
            self._allowed_apps = []
            self._current_log_id = None
            self._session_start = None
            self._session_duration = 0.0
            self._last_app_check = None
            self._current_window = None

            return True

    def get_status(self) -> TrackingStatus:
        """Get current tracking status."""
        with self._lock:
            return self._status

    def get_current_task(self) -> Optional[Task]:
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
