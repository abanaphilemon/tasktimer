"""
Database models for TaskTimer application.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class Task:
    """Represents a task that can be tracked."""
    id: Optional[int]
    name: str
    description: str
    created_at: datetime

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


@dataclass
class AllowedApp:
    """Represents an application allowed for a task."""
    id: Optional[int]
    task_id: int
    app_name: str

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'task_id': self.task_id,
            'app_name': self.app_name
        }


@dataclass
class TimeLog:
    """Represents a time tracking log entry."""
    id: Optional[int]
    task_id: int
    start_time: datetime
    end_time: Optional[datetime]
    duration: float
    status: str  # 'active', 'idle', 'paused'

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'task_id': self.task_id,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration': self.duration,
            'status': self.status
        }


@dataclass
class AppUsageLog:
    """Represents application usage tracking."""
    id: Optional[int]
    task_id: int
    app_name: str
    timestamp: datetime
    duration: float

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'task_id': self.task_id,
            'app_name': self.app_name,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'duration': self.duration
        }


@dataclass
class TaskSummary:
    """Summary statistics for a task."""
    task_id: int
    task_name: str
    total_duration: float
    app_breakdown: List[dict]
