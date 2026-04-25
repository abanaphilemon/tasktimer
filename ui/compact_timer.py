"""
Compact timer widget for TaskTimer.
Shows minimal timer display that stays on top of other windows.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame
)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette, QCursor


class CompactTimer(QWidget):
    """Compact timer widget that stays on top of other windows."""

    # Signals
    expand_requested = pyqtSignal()
    close_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._dragging = False
        self._drag_position = QPoint()

        self._setup_ui()
        self._setup_window_flags()

    def _setup_window_flags(self):
        """Setup window flags for always-on-top behavior."""
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool
        )

    def _setup_ui(self):
        """Setup compact timer UI."""
        self.setFixedSize(200, 80)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        # Status label
        self.status_label = QLabel("STOPPED")
        self.status_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.status_label.setAlignment(Qt.AlignCenter)
        self._update_status_color("STOPPED")
        layout.addWidget(self.status_label)

        # Timer label
        self.timer_label = QLabel("00:00:00")
        self.timer_label.setFont(QFont("Courier New", 20, QFont.Bold))
        self.timer_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.timer_label)

        # Buttons row
        buttons_layout = QHBoxLayout()

        self.expand_btn = QPushButton("⬆")
        self.expand_btn.setFixedSize(30, 25)
        self.expand_btn.clicked.connect(self.expand_requested.emit)
        buttons_layout.addWidget(self.expand_btn)

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(30, 25)
        self.close_btn.clicked.connect(self.close_requested.emit)
        buttons_layout.addWidget(self.close_btn)

        layout.addLayout(buttons_layout)

        # Style
        self.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
                color: #ffffff;
                border-radius: 10px;
            }
            QLabel {
                background-color: transparent;
            }
            QPushButton {
                background-color: #4a4a4a;
                color: #ffffff;
                border: none;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
        """)

    def _update_status_color(self, status: str):
        """Update status label color."""
        palette = self.status_label.palette()

        if status == "ACTIVE":
            palette.setColor(QPalette.WindowText, QColor(100, 200, 100))
        elif status == "IDLE":
            palette.setColor(QPalette.WindowText, QColor(200, 180, 100))
        elif status == "PAUSED":
            palette.setColor(QPalette.WindowText, QColor(200, 100, 100))
        else:  # STOPPED
            palette.setColor(QPalette.WindowText, QColor(150, 150, 150))

        self.status_label.setPalette(palette)

    def update_status(self, status: str):
        """Update status display."""
        self.status_label.setText(status)
        self._update_status_color(status)

    def update_timer(self, duration: float):
        """Update timer display."""
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        secs = int(duration % 60)
        self.timer_label.setText(f"{hours:02d}:{minutes:02d}:{secs:02d}")

    def mousePressEvent(self, event):
        """Handle mouse press for dragging."""
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging."""
        if event.buttons() == Qt.LeftButton and self._dragging:
            self.move(event.globalPos() - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        if event.button() == Qt.LeftButton:
            self._dragging = False
            event.accept()
