"""
Task dialog for creating and editing tasks.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QListWidget, QListWidgetItem,
    QDialogButtonBox, QSplitter, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from typing import List, Optional


class TaskDialog(QDialog):
    """Dialog for creating and editing tasks."""

    def __init__(self, task_name: str = "", task_description: str = "",
                 allowed_apps: Optional[List[str]] = None,
                 available_apps: Optional[List[str]] = None,
                 parent=None):
        super().__init__(parent)

        self.task_name = task_name
        self.task_description = task_description
        self.allowed_apps = allowed_apps or []
        self.available_apps = available_apps or []

        self._setup_ui()
        self._populate_lists()

    def _setup_ui(self):
        """Setup dialog UI."""
        self.setWindowTitle("Task Details")
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout(self)

        # Name field
        name_layout = QHBoxLayout()
        name_label = QLabel("Task Name:")
        name_label.setMinimumWidth(100)
        self.name_input = QLineEdit()
        self.name_input.setText(self.task_name)
        self.name_input.setPlaceholderText("Enter task name...")
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)

        # Description field
        desc_label = QLabel("Description:")
        self.desc_input = QTextEdit()
        self.desc_input.setText(self.task_description)
        self.desc_input.setPlaceholderText("Enter task description (optional)...")
        self.desc_input.setMaximumHeight(80)
        layout.addWidget(desc_label)
        layout.addWidget(self.desc_input)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        layout.addWidget(separator)

        # Apps section
        apps_label = QLabel("Allowed Applications:")
        layout.addWidget(apps_label)

        # Splitter for app lists
        splitter = QSplitter(Qt.Horizontal)

        # Available apps list
        available_frame = QFrame()
        available_layout = QVBoxLayout(available_frame)
        available_layout.addWidget(QLabel("Available Apps:"))
        self.available_list = QListWidget()
        self.available_list.setSelectionMode(QListWidget.SingleSelection)
        available_layout.addWidget(self.available_list)

        # Add button
        self.add_btn = QPushButton("Add →")
        self.add_btn.clicked.connect(self._add_app)
        available_layout.addWidget(self.add_btn)

        splitter.addWidget(available_frame)

        # Allowed apps list
        allowed_frame = QFrame()
        allowed_layout = QVBoxLayout(allowed_frame)
        allowed_layout.addWidget(QLabel("Allowed Apps:"))
        self.allowed_list = QListWidget()
        self.allowed_list.setSelectionMode(QListWidget.SingleSelection)
        allowed_layout.addWidget(self.allowed_list)

        # Remove button
        self.remove_btn = QPushButton("← Remove")
        self.remove_btn.clicked.connect(self._remove_app)
        allowed_layout.addWidget(self.remove_btn)

        splitter.addWidget(allowed_frame)

        layout.addWidget(splitter)

        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate_lists(self):
        """Populate app lists."""
        # Populate available apps
        for app in self.available_apps:
            if app not in self.allowed_apps:
                item = QListWidgetItem(app)
                self.available_list.addItem(item)

        # Populate allowed apps
        for app in self.allowed_apps:
            item = QListWidgetItem(app)
            self.allowed_list.addItem(item)

    def _add_app(self):
        """Add selected app to allowed list."""
        current_item = self.available_list.currentItem()
        if current_item:
            app_name = current_item.text()
            self.allowed_apps.append(app_name)
            self.allowed_list.addItem(QListWidgetItem(app_name))
            self.available_list.takeItem(self.available_list.row(current_item))

    def _remove_app(self):
        """Remove selected app from allowed list."""
        current_item = self.allowed_list.currentItem()
        if current_item:
            app_name = current_item.text()
            self.allowed_apps.remove(app_name)
            self.available_list.addItem(QListWidgetItem(app_name))
            self.allowed_list.takeItem(self.allowed_list.row(current_item))

    def get_data(self) -> dict:
        """Get dialog data."""
        return {
            'name': self.name_input.text().strip(),
            'description': self.desc_input.toPlainText().strip(),
            'allowed_apps': self.allowed_apps.copy()
        }

    def accept(self):
        """Validate and accept dialog."""
        if not self.name_input.text().strip():
            self.name_input.setFocus()
            return

        if not self.allowed_apps:
            self.allowed_list.setFocus()
            return

        super().accept()
