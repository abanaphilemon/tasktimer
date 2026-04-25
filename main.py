#!/usr/bin/env python3
"""
TaskTimer - Task-Based Intelligent Time Tracking Desktop Application

Main entry point for the application.
"""

import sys
import os
import signal
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseHandler
from core import TrackingEngine
from ui import Dashboard


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
    app.setApplicationName("TaskTimer")
    app.setOrganizationName("TaskTimer")

    # Initialize database
    db = DatabaseHandler()

    # Initialize tracking engine
    tracker = TrackingEngine(db)

    # Create and show main window
    window = Dashboard(db, tracker)
    window.setWindowTitle("TaskTimer - Intelligent Time Tracking")
    window.show()

    # Clean up on exit
    def cleanup():
        tracker.shutdown()
        db.close()

    app.aboutToQuit.connect(cleanup)

    # Run application
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
