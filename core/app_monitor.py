"""
App monitoring module for TaskTimer.
Detects active window and running processes.
"""

import platform
from dataclasses import dataclass
from typing import List, Optional

try:
    import psutil
except ImportError:
    raise ImportError(
        "psutil is required. Install it with: pip install psutil"
    )


@dataclass
class ActiveWindow:
    """Information about the currently active window."""
    title: str
    app_name: str
    process_id: int


class AppMonitor:
    """Monitors active window and running applications."""

    def __init__(self):
        """Initialize app monitor."""
        self._platform = platform.system()
        self._last_window: Optional[ActiveWindow] = None

    def get_active_window(self) -> Optional[ActiveWindow]:
        """
        Get information about the currently active window.

        Returns:
            ActiveWindow with title, app_name, and process_id, or None if detection fails
        """
        if self._platform == "Windows":
            return self._get_active_window_windows()
        elif self._platform == "Darwin":  # macOS
            return self._get_active_window_macos()
        elif self._platform == "Linux":
            return self._get_active_window_linux()
        else:
            return None

    def _get_active_window_windows(self) -> Optional[ActiveWindow]:
        """Get active window on Windows."""
        try:
            import win32gui
            import win32process

            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None

            title = win32gui.GetWindowText(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)

            try:
                process = psutil.Process(pid)
                app_name = process.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                app_name = "Unknown"

            return ActiveWindow(title=title, app_name=app_name, process_id=pid)
        except ImportError:
            raise ImportError(
                "pywin32 is required for Windows. Install it with: pip install pywin32"
            )
        except Exception:
            return None

    def _get_active_window_macos(self) -> Optional[ActiveWindow]:
        """Get active window on macOS."""
        try:
            import subprocess

            # Get frontmost app name
            result = subprocess.run(
                ['osascript', '-e', 'tell application "System Events" to get name of first application process whose frontmost is true'],
                capture_output=True,
                text=True
            )
            app_name = result.stdout.strip()

            # Get window title
            result = subprocess.run(
                ['osascript', '-e', 'tell application "System Events" to get name of front window of first application process whose frontmost is true'],
                capture_output=True,
                text=True
            )
            title = result.stdout.strip()

            # Get PID
            result = subprocess.run(
                ['osascript', '-e', 'tell application "System Events" to get unix id of first application process whose frontmost is true'],
                capture_output=True,
                text=True
            )
            try:
                pid = int(result.stdout.strip())
            except ValueError:
                pid = 0

            return ActiveWindow(title=title, app_name=app_name, process_id=pid)
        except Exception:
            return None

    def _get_active_window_linux(self) -> Optional[ActiveWindow]:
        """Get active window on Linux."""
        try:
            import subprocess

            # Try using xdotool first
            try:
                result = subprocess.run(
                    ['xdotool', 'getactivewindow', 'getwindowname', 'getwindowpid'],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) >= 2:
                        title = lines[0]
                        try:
                            pid = int(lines[1])
                        except ValueError:
                            pid = 0

                        # Get app name from process
                        app_name = "Unknown"
                        if pid > 0:
                            try:
                                process = psutil.Process(pid)
                                app_name = process.name()
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass

                        return ActiveWindow(title=title, app_name=app_name, process_id=pid)
            except FileNotFoundError:
                pass

            # Fallback: try wmctrl
            try:
                result = subprocess.run(
                    ['wmctrl', '-a', ':ACTIVE:', '-v'],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    # Parse output to get window info
                    for line in result.stdout.split('\n'):
                        if 'Active window' in line or '0x' in line:
                            parts = line.split()
                            if len(parts) >= 4:
                                title = ' '.join(parts[3:])
                                # Try to get PID from window
                                try:
                                    result = subprocess.run(
                                        ['xprop', '-id', parts[0], '_NET_WM_PID'],
                                        capture_output=True,
                                        text=True
                                    )
                                    if result.returncode == 0:
                                        pid_str = result.stdout.split('=')[-1].strip()
                                        pid = int(pid_str)
                                        process = psutil.Process(pid)
                                        app_name = process.name()
                                        return ActiveWindow(title=title, app_name=app_name, process_id=pid)
                                except Exception:
                                    pass
            except FileNotFoundError:
                pass

            return None
        except Exception:
            return None

    def get_running_processes(self) -> List[str]:
        """
        Get list of running process names.

        Returns:
            List of process names
        """
        process_names = set()

        for proc in psutil.process_iter(['name']):
            try:
                process_names.add(proc.info['name'])
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        return sorted(list(process_names))

    def is_app_allowed(self, current_app: str, allowed_apps: List[str]) -> bool:
        """
        Check if current app is in allowed list.

        Args:
            current_app: Name of current active app
            allowed_apps: List of allowed app names

        Returns:
            True if app is allowed, False otherwise
        """
        if not allowed_apps:
            return False

        current_lower = current_app.lower()

        for allowed in allowed_apps:
            # Case-insensitive match
            if allowed.lower() == current_lower:
                return True

            # Check if current app contains allowed name (for partial matches)
            if allowed.lower() in current_lower:
                return True

            # Check if allowed name contains current app
            if current_lower in allowed.lower():
                return True

        return False

    def get_last_window(self) -> Optional[ActiveWindow]:
        """Get the last detected active window."""
        return self._last_window

    def update_last_window(self, window: ActiveWindow):
        """Update the last detected window."""
        self._last_window = window
