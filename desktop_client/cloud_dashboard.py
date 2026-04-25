"""
Cloud dashboard for TaskTimer.
Uses API client and cloud tracking engine.
"""

from datetime import datetime
from typing import Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QMessageBox, QDialog,
    QScrollArea, QSplitter
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt5.QtGui import QFont, QColor, QPalette, QDesktopServices
from PyQt5.QtCore import QUrl

from desktop_client.api_client import TaskTimerAPIClient
from desktop_client.cloud_tracking_engine import CloudTrackingEngine, TrackingStatus, NetworkStatus
from desktop_client.login_dialog import LoginDialog
from core.app_monitor import AppMonitor
from ui.task_dialog import TaskDialog
from ui.compact_timer import CompactTimer


class CloudDashboard(QWidget):
    """Cloud-based dashboard for TaskTimer."""

    # Signals
    task_selected = pyqtSignal(str)  # task_id
    task_started = pyqtSignal(str)   # task_id
    task_stopped = pyqtSignal()

    def __init__(self, api_client: TaskTimerAPIClient):
        super().__init__()

        self.api = api_client
        self.tracker = CloudTrackingEngine(api_client)
        self.app_monitor = AppMonitor()

        self._current_task: Optional[dict] = None
        self._selected_task_id: Optional[str] = None
        self._user_data: Optional[dict] = None

        self._setup_ui()
        self._connect_signals()
        self._refresh_task_list()

        # Update timer
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._update_display)
        self._update_timer.start(100)  # 100ms update

        # Create compact timer widget
        self._compact_timer = CompactTimer()
        self._compact_timer.expand_requested.connect(self._expand_to_full)
        self._compact_timer.close_requested.connect(self.close)

    def _setup_ui(self):
        """Setup dashboard UI."""
        self.setWindowTitle("TaskTimer Cloud - Intelligent Time Tracking")
        self.setMinimumSize(900, 600)

        main_layout = QHBoxLayout(self)

        # Left panel - Task list
        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)

        # User info header
        user_header = QHBoxLayout()
        self.user_label = QLabel("Not logged in")
        self.user_label.setFont(QFont("Arial", 12, QFont.Bold))
        user_header.addWidget(self.user_label)

        self.logout_btn = QPushButton("Logout")
        self.logout_btn.clicked.connect(self._handle_logout)
        user_header.addWidget(self.logout_btn)

        left_layout.addLayout(user_header)

        # Task list header
        header_layout = QHBoxLayout()
        header_label = QLabel("Tasks")
        header_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_layout.addWidget(header_label)

        self.add_task_btn = QPushButton("+ New Task")
        self.add_task_btn.clicked.connect(self._create_task)
        header_layout.addWidget(self.add_task_btn)

        # Compact mode toggle button
        self.compact_btn = QPushButton("⬇ Compact")
        self.compact_btn.setToolTip("Switch to compact overlay mode")
        self.compact_btn.clicked.connect(self._switch_to_compact)
        header_layout.addWidget(self.compact_btn)

        left_layout.addLayout(header_layout)

        # Task list
        self.task_list = QListWidget()
        self.task_list.itemClicked.connect(self._on_task_selected)
        left_layout.addWidget(self.task_list)

        # Task actions
        actions_layout = QHBoxLayout()
        self.edit_task_btn = QPushButton("Edit")
        self.edit_task_btn.clicked.connect(self._edit_task)
        self.edit_task_btn.setEnabled(False)
        actions_layout.addWidget(self.edit_task_btn)

        self.delete_task_btn = QPushButton("Delete")
        self.delete_task_btn.clicked.connect(self._delete_task)
        self.delete_task_btn.setEnabled(False)
        actions_layout.addWidget(self.delete_task_btn)

        left_layout.addLayout(actions_layout)

        main_layout.addWidget(left_panel, stretch=1)

        # Right panel - Active task view
        right_panel = QFrame()
        right_panel.setFrameShape(QFrame.StyledPanel)
        right_layout = QVBoxLayout(right_panel)

        # Status section
        self.status_label = QLabel("Status: STOPPED")
        self.status_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.status_label.setAlignment(Qt.AlignCenter)
        self._update_status_color(TrackingStatus.STOPPED)
        right_layout.addWidget(self.status_label)

        # Network status section
        self.network_status_label = QLabel("Network: Online")
        self.network_status_label.setFont(QFont("Arial", 10))
        self.network_status_label.setAlignment(Qt.AlignCenter)
        self.network_status_label.setStyleSheet("color: #006600;")
        right_layout.addWidget(self.network_status_label)

        # Current task section
        self.current_task_label = QLabel("No task selected")
        self.current_task_label.setFont(QFont("Arial", 11))
        self.current_task_label.setAlignment(Qt.AlignCenter)
        self.current_task_label.setWordWrap(True)
        right_layout.addWidget(self.current_task_label)

        # Timer display
        self.timer_label = QLabel("00:00:00")
        self.timer_label.setFont(QFont("Courier New", 36, QFont.Bold))
        self.timer_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.timer_label)

        # Current app section
        self.current_app_label = QLabel("Current App: --")
        self.current_app_label.setFont(QFont("Arial", 10))
        self.current_app_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.current_app_label)

        # Idle time section
        self.idle_time_label = QLabel("Idle Time: 0s")
        self.idle_time_label.setFont(QFont("Arial", 10))
        self.idle_time_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.idle_time_label)

        # Start/Stop button
        self.start_stop_btn = QPushButton("Start Tracking")
        self.start_stop_btn.setMinimumHeight(50)
        self.start_stop_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.start_stop_btn.clicked.connect(self._toggle_tracking)
        self.start_stop_btn.setEnabled(False)
        right_layout.addWidget(self.start_stop_btn)

        # Live link section
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        right_layout.addWidget(separator)

        self.live_link_label = QLabel("Share Live Link:")
        self.live_link_label.setFont(QFont("Arial", 12, QFont.Bold))
        right_layout.addWidget(self.live_link_label)

        self.live_link_btn = QPushButton("Generate Live Link")
        self.live_link_btn.clicked.connect(self._generate_live_link)
        self.live_link_btn.setEnabled(False)
        right_layout.addWidget(self.live_link_btn)

        self.live_link_display = QLabel("")
        self.live_link_display.setAlignment(Qt.AlignCenter)
        self.live_link_display.setWordWrap(True)
        self.live_link_display.setStyleSheet("color: #666; font-size: 11px;")
        right_layout.addWidget(self.live_link_display)

        # Task summary section
        summary_separator = QFrame()
        summary_separator.setFrameShape(QFrame.HLine)
        right_layout.addWidget(summary_separator)

        self.summary_text = QLabel("Select a task to view summary")
        self.summary_text.setAlignment(Qt.AlignLeft)
        self.summary_text.setWordWrap(True)
        self.summary_text.setStyleSheet("color: #333; font-size: 11px;")
        right_layout.addWidget(self.summary_text)

        right_layout.addStretch()

        main_layout.addWidget(right_panel, stretch=2)

    def _connect_signals(self):
        """Connect signals."""
        self.tracker.add_status_callback(self._on_status_changed)
        self.tracker.add_time_callback(self._on_time_updated)
        self.tracker.add_app_callback(self._on_app_changed)
        self.tracker.add_network_callback(self._on_network_changed)

    def _update_status_color(self, status: TrackingStatus):
        """Update status label color."""
        palette = self.status_label.palette()

        if status == TrackingStatus.ACTIVE:
            palette.setColor(QPalette.WindowText, QColor(0, 150, 0))
        elif status == TrackingStatus.IDLE:
            palette.setColor(QPalette.WindowText, QColor(200, 150, 0))
        elif status == TrackingStatus.PAUSED:
            palette.setColor(QPalette.WindowText, QColor(200, 50, 0))
        else:  # STOPPED
            palette.setColor(QPalette.WindowText, QColor(100, 100, 100))

        self.status_label.setPalette(palette)

    def _on_status_changed(self, status: TrackingStatus):
        """Handle tracking status change."""
        status_text = {
            TrackingStatus.STOPPED: "STOPPED",
            TrackingStatus.ACTIVE: "ACTIVE",
            TrackingStatus.IDLE: "IDLE",
            TrackingStatus.PAUSED: "PAUSED"
        }.get(status, "UNKNOWN")

        self.status_label.setText(f"Status: {status_text}")
        self._update_status_color(status)

        # Update compact timer
        self._compact_timer.update_status(status_text)

        # Update button
        if status == TrackingStatus.STOPPED:
            self.start_stop_btn.setText("Start Tracking")
            self.start_stop_btn.setEnabled(self._selected_task_id is not None)
        else:
            self.start_stop_btn.setText("Stop Tracking")

    def _on_network_changed(self, status: NetworkStatus):
        """Handle network status change."""
        if status == NetworkStatus.ONLINE:
            self.network_status_label.setText("Network: Online")
            self.network_status_label.setStyleSheet("color: #006600;")
        else:
            self.network_status_label.setText("Network: Offline (Tracking Paused)")
            self.network_status_label.setStyleSheet("color: #990000;")

    def _on_time_updated(self, duration: float):
        """Handle time update."""
        self.timer_label.setText(self._format_duration(duration))
        self._compact_timer.update_timer(duration)

    def _on_app_changed(self, window):
        """Handle app change."""
        if window:
            self.current_app_label.setText(f"Current App: {window.app_name}")
        else:
            self.current_app_label.setText("Current App: --")

    def _format_duration(self, seconds: float) -> str:
        """Format duration as HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _update_display(self):
        """Update display periodically."""
        # Update idle time
        if self.tracker.is_running():
            idle_time = self.tracker.get_idle_time()
            self.idle_time_label.setText(f"Idle Time: {int(idle_time)}s")

            # Show pending updates if offline
            pending_count = self.tracker.get_pending_updates_count()
            if pending_count > 0:
                self.network_status_label.setText(f"Network: Offline ({pending_count} updates pending)")
                self.network_status_label.setStyleSheet("color: #990000;")

            # Refresh task summary every 5 seconds
            if self._selected_task_id and int(self.tracker.get_session_duration()) % 5 == 0:
                try:
                    task = self.api.get_task(self._selected_task_id)
                    if task:
                        self._update_task_summary(self._selected_task_id, task.get("total_time", 0.0))
                except Exception:
                    pass
        else:
            self.idle_time_label.setText("Idle Time: 0s")

    def _refresh_task_list(self):
        """Refresh task list."""
        self.task_list.clear()

        try:
            tasks = self.api.get_tasks()
            for task in tasks:
                item = QListWidgetItem(task["name"])
                item.setData(Qt.UserRole, task["id"])
                self.task_list.addItem(item)
        except Exception as e:
            print(f"Error loading tasks: {e}")

    def _on_task_selected(self, item: QListWidgetItem):
        """Handle task selection."""
        task_id = item.data(Qt.UserRole)
        self._selected_task_id = task_id

        # Enable buttons
        self.edit_task_btn.setEnabled(True)
        self.delete_task_btn.setEnabled(True)

        # Enable start button if not tracking
        if not self.tracker.is_running():
            self.start_stop_btn.setEnabled(True)

        # Get task details and show permanent link
        try:
            task = self.api.get_task(task_id)
            if task:
                self.current_task_label.setText(task["name"])

                # Show permanent live link
                if task.get("share_token"):
                    live_link = self.api.get_live_link(task["share_token"])
                    self.live_link_display.setText(live_link)
                    self.live_link_display.setTextInteractionFlags(Qt.TextSelectableByMouse)
                    self.live_link_btn.setEnabled(True)
                else:
                    self.live_link_display.setText("No link generated yet")
                    self.live_link_btn.setEnabled(False)

                # Show total time
                total_time = task.get("total_time", 0.0)
                self._update_task_summary(task_id, total_time)
        except Exception:
            pass

    def _create_task(self):
        """Create new task."""
        available_apps = self.app_monitor.get_running_processes()

        dialog = TaskDialog(
            available_apps=available_apps,
            parent=self
        )

        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()

            try:
                # Create task via API
                self.api.create_task(
                    data['name'],
                    data['description'],
                    data['allowed_apps']
                )
                self._refresh_task_list()
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Failed to create task: {str(e)}"
                )

    def _edit_task(self):
        """Edit selected task."""
        if not self._selected_task_id:
            return

        try:
            task = self.api.get_task(self._selected_task_id)
            if not task:
                return

            allowed_apps = task.get("allowed_apps", [])
            available_apps = self.app_monitor.get_running_processes()

            dialog = TaskDialog(
                task_name=task["name"],
                task_description=task.get("description", ""),
                allowed_apps=allowed_apps,
                available_apps=available_apps,
                parent=self
            )

            if dialog.exec_() == QDialog.Accepted:
                data = dialog.get_data()

                # Update task via API
                self.api.update_task(
                    self._selected_task_id,
                    data['name'],
                    data['description'],
                    data['allowed_apps']
                )
                self._refresh_task_list()
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to update task: {str(e)}"
            )

    def _delete_task(self):
        """Delete selected task."""
        if not self._selected_task_id:
            return

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Delete Task",
            "Are you sure you want to delete this task?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                self.api.delete_task(self._selected_task_id)
                self._selected_task_id = None
                self.edit_task_btn.setEnabled(False)
                self.delete_task_btn.setEnabled(False)
                self.start_stop_btn.setEnabled(False)
                self.current_task_label.setText("No task selected")
                self._refresh_task_list()
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Failed to delete task: {str(e)}"
                )

    def _update_task_summary(self, task_id: str, total_time: float = 0.0):
        """Update task summary display with time history."""
        try:
            # Get task details
            task = self.api.get_task(task_id)
            if not task:
                self.summary_text.setText("Select a task to view summary")
                return

            total_time_str = self._format_duration(total_time)

            text = f"<b>Task:</b> {task['name']}<br><br>"
            text += f"<b>Total Time:</b> {total_time_str}<br><br>"

            # Get time history
            time_history = task.get("time_history", [])
            if time_history:
                text += "<b>Recent Sessions:</b><br>"
                for entry in time_history[:5]:  # Show last 5 entries
                    timestamp = entry.get("timestamp", "")
                    duration = self._format_duration(entry.get("duration", 0))
                    status = entry.get("status", "unknown").upper()
                    text += f"• {timestamp}: {duration} ({status})<br>"
            else:
                text += "No time history yet<br>"

            # Get app usage summary
            app_usage = self.api.get_task_app_summary(task_id)
            if app_usage:
                text += "<br><b>App Usage:</b><br>"
                for app in app_usage[:5]:  # Top 5 apps
                    app_time = self._format_duration(app.get("total_duration", 0))
                    text += f"• {app['app_name']}: {app_time}<br>"
            else:
                text += "<br><b>App Usage:</b> No data yet"

            self.summary_text.setText(text)
        except Exception as e:
            print(f"Error updating task summary: {e}")
            self.summary_text.setText("Error loading summary")

    def _toggle_tracking(self):
        """Toggle tracking on/off."""
        if self.tracker.is_running():
            # Stop tracking
            self.tracker.stop_tracking()
            self.task_stopped.emit()
            self.live_link_btn.setEnabled(False)
            self.live_link_display.setText("")
        else:
            # Start tracking
            if self._selected_task_id:
                success = self.tracker.start_tracking(self._selected_task_id)
                if success:
                    self.task_started.emit(self._selected_task_id)
                    self.live_link_btn.setEnabled(True)
                else:
                    QMessageBox.warning(
                        self,
                        "Error",
                        "Failed to start tracking. Make sure the task has allowed apps."
                    )

    def _generate_live_link(self):
        """Generate and display permanent live link for task."""
        if not self._selected_task_id:
            return

        try:
            task = self.api.get_task(self._selected_task_id)
            if task and task.get("share_token"):
                live_link = self.api.get_live_link(task["share_token"])
                self.live_link_display.setText(live_link)
                self.live_link_display.setTextInteractionFlags(Qt.TextSelectableByMouse)

                # Ask if user wants to open it
                reply = QMessageBox.question(
                    self,
                    "Open Live Link",
                    f"Permanent live link for task '{task['name']}':\n\n{live_link}\n\nOpen in browser?",
                    QMessageBox.Yes | QMessageBox.No
                )

                if reply == QMessageBox.Yes:
                    QDesktopServices.openUrl(QUrl(live_link))
            else:
                # Generate share link for existing task
                result = self.api.generate_share_link(self._selected_task_id)
                live_link = self.api.get_live_link(result["share_token"])
                self.live_link_display.setText(live_link)
                self.live_link_display.setTextInteractionFlags(Qt.TextSelectableByMouse)

                # Ask if user wants to open it
                reply = QMessageBox.question(
                    self,
                    "Open Live Link",
                    f"Permanent live link generated for task '{task['name']}':\n\n{live_link}\n\nOpen in browser?",
                    QMessageBox.Yes | QMessageBox.No
                )

                if reply == QMessageBox.Yes:
                    QDesktopServices.openUrl(QUrl(live_link))
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to get live link: {str(e)}"
            )

    def _handle_logout(self):
        """Handle logout."""
        self.api.access_token = None
        self.api.user_id = None
        self.close()

    def _switch_to_compact(self):
        """Switch to compact overlay mode."""
        self._is_compact_mode = True

        # Save current position
        self._full_window_pos = self.pos()

        # Hide main window
        self.hide()

        # Show compact timer
        self._compact_timer.show()

        # Position compact timer near the main window
        compact_pos = self._full_window_pos + QPoint(100, 100)
        self._compact_timer.move(compact_pos)

    def _expand_to_full(self):
        """Expand back to full dashboard mode."""
        self._is_compact_mode = False

        # Hide compact timer
        self._compact_timer.hide()

        # Show main window at saved position
        self.move(self._full_window_pos)
        self.show()

    def closeEvent(self, event):
        """Handle close event."""
        # Also close compact timer if open
        self._compact_timer.close()
        super().closeEvent(event)
