"""
Database handler for TaskTimer application.
Manages all SQLite database operations.
"""

import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from database.models import Task, AllowedApp, TimeLog, AppUsageLog, TaskSummary


class DatabaseHandler:
    """Thread-safe database handler for TaskTimer."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path: Optional[str] = None):
        """Singleton pattern to ensure single database connection."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: Optional[str] = None):
        """Initialize database handler."""
        if self._initialized:
            return

        if db_path is None:
            db_path = Path.home() / '.tasktimer' / 'tasktimer.db'
        else:
            db_path = Path(db_path)

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._initialized = True
        self._initialize_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(str(self.db_path))
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection

    def _initialize_database(self):
        """Create database tables if they don't exist."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Tasks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Allowed apps table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS allowed_apps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                app_name TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
        ''')

        # Time logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS time_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                duration REAL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'active',
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
        ''')

        # App usage logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                app_name TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                duration REAL DEFAULT 0,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
        ''')

        # Create indexes for better query performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_time_logs_task ON time_logs(task_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_time_logs_status ON time_logs(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_app_usage_task ON app_usage_logs(task_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_allowed_apps_task ON allowed_apps(task_id)')

        conn.commit()

    # Task operations
    def create_task(self, name: str, description: str = "") -> Task:
        """Create a new task."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            'INSERT INTO tasks (name, description, created_at) VALUES (?, ?, ?)',
            (name, description, datetime.now())
        )
        conn.commit()

        return Task(
            id=cursor.lastrowid,
            name=name,
            description=description,
            created_at=datetime.now()
        )

    def get_task(self, task_id: int) -> Optional[Task]:
        """Get a task by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
        row = cursor.fetchone()

        if row:
            return Task(
                id=row['id'],
                name=row['name'],
                description=row['description'],
                created_at=datetime.fromisoformat(row['created_at'])
            )
        return None

    def get_all_tasks(self) -> List[Task]:
        """Get all tasks."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM tasks ORDER BY created_at DESC')
        rows = cursor.fetchall()

        return [
            Task(
                id=row['id'],
                name=row['name'],
                description=row['description'],
                created_at=datetime.fromisoformat(row['created_at'])
            )
            for row in rows
        ]

    def update_task(self, task_id: int, name: Optional[str] = None,
                   description: Optional[str] = None) -> bool:
        """Update a task."""
        conn = self._get_connection()
        cursor = conn.cursor()

        updates = []
        params = []

        if name is not None:
            updates.append('name = ?')
            params.append(name)

        if description is not None:
            updates.append('description = ?')
            params.append(description)

        if not updates:
            return False

        params.append(task_id)
        cursor.execute(
            f'UPDATE tasks SET {", ".join(updates)} WHERE id = ?',
            params
        )
        conn.commit()

        return cursor.rowcount > 0

    def delete_task(self, task_id: int) -> bool:
        """Delete a task and all associated data."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        conn.commit()

        return cursor.rowcount > 0

    # Allowed apps operations
    def add_allowed_app(self, task_id: int, app_name: str) -> AllowedApp:
        """Add an allowed app for a task."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            'INSERT INTO allowed_apps (task_id, app_name) VALUES (?, ?)',
            (task_id, app_name)
        )
        conn.commit()

        return AllowedApp(
            id=cursor.lastrowid,
            task_id=task_id,
            app_name=app_name
        )

    def get_allowed_apps(self, task_id: int) -> List[AllowedApp]:
        """Get all allowed apps for a task."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM allowed_apps WHERE task_id = ?', (task_id,))
        rows = cursor.fetchall()

        return [
            AllowedApp(id=row['id'], task_id=row['task_id'], app_name=row['app_name'])
            for row in rows
        ]

    def remove_allowed_app(self, app_id: int) -> bool:
        """Remove an allowed app."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM allowed_apps WHERE id = ?', (app_id,))
        conn.commit()

        return cursor.rowcount > 0

    def clear_allowed_apps(self, task_id: int) -> bool:
        """Clear all allowed apps for a task."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM allowed_apps WHERE task_id = ?', (task_id,))
        conn.commit()

        return cursor.rowcount > 0

    # Time log operations
    def create_time_log(self, task_id: int, status: str = 'active') -> TimeLog:
        """Create a new time log entry."""
        conn = self._get_connection()
        cursor = conn.cursor()

        start_time = datetime.now()
        cursor.execute(
            'INSERT INTO time_logs (task_id, start_time, status) VALUES (?, ?, ?)',
            (task_id, start_time, status)
        )
        conn.commit()

        return TimeLog(
            id=cursor.lastrowid,
            task_id=task_id,
            start_time=start_time,
            end_time=None,
            duration=0.0,
            status=status
        )

    def update_time_log(self, log_id: int, end_time: Optional[datetime] = None,
                       duration: Optional[float] = None, status: Optional[str] = None) -> bool:
        """Update a time log entry."""
        conn = self._get_connection()
        cursor = conn.cursor()

        updates = []
        params = []

        if end_time is not None:
            updates.append('end_time = ?')
            params.append(end_time)

        if duration is not None:
            updates.append('duration = ?')
            params.append(duration)

        if status is not None:
            updates.append('status = ?')
            params.append(status)

        if not updates:
            return False

        params.append(log_id)
        cursor.execute(
            f'UPDATE time_logs SET {", ".join(updates)} WHERE id = ?',
            params
        )
        conn.commit()

        return cursor.rowcount > 0

    def get_active_time_log(self, task_id: int) -> Optional[TimeLog]:
        """Get the active time log for a task."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            'SELECT * FROM time_logs WHERE task_id = ? AND end_time IS NULL ORDER BY id DESC LIMIT 1',
            (task_id,)
        )
        row = cursor.fetchone()

        if row:
            return TimeLog(
                id=row['id'],
                task_id=row['task_id'],
                start_time=datetime.fromisoformat(row['start_time']),
                end_time=datetime.fromisoformat(row['end_time']) if row['end_time'] else None,
                duration=row['duration'],
                status=row['status']
            )
        return None

    def get_task_time_logs(self, task_id: int) -> List[TimeLog]:
        """Get all time logs for a task."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM time_logs WHERE task_id = ? ORDER BY start_time DESC', (task_id,))
        rows = cursor.fetchall()

        return [
            TimeLog(
                id=row['id'],
                task_id=row['task_id'],
                start_time=datetime.fromisoformat(row['start_time']),
                end_time=datetime.fromisoformat(row['end_time']) if row['end_time'] else None,
                duration=row['duration'],
                status=row['status']
            )
            for row in rows
        ]

    def get_total_task_duration(self, task_id: int) -> float:
        """Get total duration for a task."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            'SELECT SUM(duration) as total FROM time_logs WHERE task_id = ?',
            (task_id,)
        )
        row = cursor.fetchone()

        return row['total'] if row['total'] else 0.0

    # App usage log operations
    def log_app_usage(self, task_id: int, app_name: str, duration: float) -> AppUsageLog:
        """Log application usage."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            'INSERT INTO app_usage_logs (task_id, app_name, timestamp, duration) VALUES (?, ?, ?, ?)',
            (task_id, app_name, datetime.now(), duration)
        )
        conn.commit()

        return AppUsageLog(
            id=cursor.lastrowid,
            task_id=task_id,
            app_name=app_name,
            timestamp=datetime.now(),
            duration=duration
        )

    def get_task_app_usage(self, task_id: int) -> List[AppUsageLog]:
        """Get app usage logs for a task."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            'SELECT * FROM app_usage_logs WHERE task_id = ? ORDER BY timestamp DESC',
            (task_id,)
        )
        rows = cursor.fetchall()

        return [
            AppUsageLog(
                id=row['id'],
                task_id=row['task_id'],
                app_name=row['app_name'],
                timestamp=datetime.fromisoformat(row['timestamp']),
                duration=row['duration']
            )
            for row in rows
        ]

    def get_task_app_summary(self, task_id: int) -> List[dict]:
        """Get app usage summary for a task."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            '''SELECT app_name, SUM(duration) as total_duration, COUNT(*) as sessions
               FROM app_usage_logs
               WHERE task_id = ?
               GROUP BY app_name
               ORDER BY total_duration DESC''',
            (task_id,)
        )
        rows = cursor.fetchall()

        return [
            {
                'app_name': row['app_name'],
                'total_duration': row['total_duration'],
                'sessions': row['sessions']
            }
            for row in rows
        ]

    def get_task_summary(self, task_id: int) -> Optional[TaskSummary]:
        """Get complete summary for a task."""
        task = self.get_task(task_id)
        if not task:
            return None

        total_duration = self.get_total_task_duration(task_id)
        app_breakdown = self.get_task_app_summary(task_id)

        return TaskSummary(
            task_id=task_id,
            task_name=task.name,
            total_duration=total_duration,
            app_breakdown=app_breakdown
        )

    def close(self):
        """Close database connection."""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
