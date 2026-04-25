#!/usr/bin/env python3
"""
TaskTimer Cloud - Task-Based Intelligent Time Tracking Desktop Application

Main entry point for the cloud-based application.
"""

import sys
import os
import signal
from PyQt5.QtWidgets import QApplication, QMessageBox, QDialog
from PyQt5.QtCore import Qt

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from desktop_client.api_client import TaskTimerAPIClient
from desktop_client.cloud_dashboard import CloudDashboard
from desktop_client.login_dialog import LoginDialog


def handle_signal(signum, frame):
    """Handle shutdown signals gracefully."""
    QApplication.quit()


def main():
    """Main application entry point."""
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Enable high DPI scaling (must be set before QApplication is created)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("TaskTimer Cloud")
    app.setOrganizationName("TaskTimer")

    # Initialize API client
    api = TaskTimerAPIClient(base_url="http://localhost:8000")

    # Show login dialog
    login_dialog = LoginDialog(api)

    while True:
        if login_dialog.exec_() == QDialog.Accepted:
            user_data = login_dialog.get_user_data()
            if user_data:
                break
        else:
            # User cancelled login
            sys.exit(0)

    # Create and show main window
    window = CloudDashboard(api)
    window.setWindowTitle(f"TaskTimer Cloud - {user_data['user']['name']}")
    window.show()

    # Run application
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
