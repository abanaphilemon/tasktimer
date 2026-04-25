"""
Login dialog for TaskTimer Cloud.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTabWidget, QWidget, QMessageBox
)
from PyQt5.QtCore import Qt
from typing import Optional

from desktop_client.api_client import TaskTimerAPIClient


class LoginDialog(QDialog):
    """Dialog for user authentication."""

    def __init__(self, api_client: TaskTimerAPIClient, parent=None):
        super().__init__(parent)

        self.api = api_client
        self.user_data: Optional[dict] = None

        self._setup_ui()

    def _setup_ui(self):
        """Setup dialog UI."""
        self.setWindowTitle("TaskTimer Cloud - Login")
        self.setMinimumSize(400, 350)

        layout = QVBoxLayout(self)

        # Header
        header = QLabel("🎯 TaskTimer Cloud")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header)

        subtitle = QLabel("Real-time work tracking")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #666; margin-bottom: 20px;")
        layout.addWidget(subtitle)

        # Tab widget for login/register
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Login tab
        login_tab = QWidget()
        login_layout = QVBoxLayout(login_tab)

        login_layout.addWidget(QLabel("Email:"))
        self.login_email = QLineEdit()
        self.login_email.setPlaceholderText("your@email.com")
        login_layout.addWidget(self.login_email)

        login_layout.addWidget(QLabel("Password:"))
        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("••••••••")
        self.login_password.setEchoMode(QLineEdit.Password)
        login_layout.addWidget(self.login_password)

        self.login_btn = QPushButton("Login")
        self.login_btn.setMinimumHeight(40)
        self.login_btn.clicked.connect(self._handle_login)
        login_layout.addWidget(self.login_btn)

        login_layout.addStretch()
        self.tabs.addTab(login_tab, "Login")

        # Register tab
        register_tab = QWidget()
        register_layout = QVBoxLayout(register_tab)

        register_layout.addWidget(QLabel("Name:"))
        self.register_name = QLineEdit()
        self.register_name.setPlaceholderText("Your Name")
        register_layout.addWidget(self.register_name)

        register_layout.addWidget(QLabel("Email:"))
        self.register_email = QLineEdit()
        self.register_email.setPlaceholderText("your@email.com")
        register_layout.addWidget(self.register_email)

        register_layout.addWidget(QLabel("Password:"))
        self.register_password = QLineEdit()
        self.register_password.setPlaceholderText("••••••••")
        self.register_password.setEchoMode(QLineEdit.Password)
        register_layout.addWidget(self.register_password)

        register_layout.addWidget(QLabel("Confirm Password:"))
        self.register_confirm = QLineEdit()
        self.register_confirm.setPlaceholderText("••••••••")
        self.register_confirm.setEchoMode(QLineEdit.Password)
        register_layout.addWidget(self.register_confirm)

        self.register_btn = QPushButton("Register")
        self.register_btn.setMinimumHeight(40)
        self.register_btn.clicked.connect(self._handle_register)
        register_layout.addWidget(self.register_btn)

        register_layout.addStretch()
        self.tabs.addTab(register_tab, "Register")

        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #ef4444; margin-top: 10px;")
        layout.addWidget(self.status_label)

    def _handle_login(self):
        """Handle login."""
        email = self.login_email.text().strip()
        password = self.login_password.text()

        if not email or not password:
            self.status_label.setText("Please fill in all fields")
            return

        try:
            self.status_label.setText("Logging in...")
            self.user_data = self.api.login(email, password)
            self.accept()
        except Exception as e:
            self.status_label.setText(f"Login failed: {str(e)}")

    def _handle_register(self):
        """Handle registration."""
        name = self.register_name.text().strip()
        email = self.register_email.text().strip()
        password = self.register_password.text()
        confirm = self.register_confirm.text()

        if not name or not email or not password:
            self.status_label.setText("Please fill in all fields")
            return

        if password != confirm:
            self.status_label.setText("Passwords do not match")
            return

        if len(password) < 6:
            self.status_label.setText("Password must be at least 6 characters")
            return

        try:
            self.status_label.setText("Creating account...")
            self.user_data = self.api.register(email, password, name)
            self.accept()
        except Exception as e:
            self.status_label.setText(f"Registration failed: {str(e)}")

    def get_user_data(self) -> Optional[dict]:
        """Get authenticated user data."""
        return self.user_data
