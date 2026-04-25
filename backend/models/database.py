"""
MongoDB database connection and operations.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from bson.objectid import ObjectId
import secrets
import hashlib

from .schemas import (
    User, Task, Session, TrackingEvent, AppUsageLog,
    UserCreate, TaskCreate, SessionCreate
)
from config import settings


class Database:
    """MongoDB database handler."""

    def __init__(self, connection_string: str = None):
        if connection_string is None:
            connection_string = settings.mongodb_url
        self.client = AsyncIOMotorClient(connection_string)
        self.db = self.client[settings.database_name]
        self.users = self.db.users
        self.tasks = self.db.tasks
        self.sessions = self.db.sessions
        self.events = self.db.events
        self.app_usage_logs = self.db.app_usage_logs

    async def create_indexes(self):
        """Create database indexes."""
        await self.users.create_index("email", unique=True)
        await self.tasks.create_index([("user_id", 1)])
        await self.sessions.create_index("share_token", unique=True)
        await self.sessions.create_index([("user_id", 1)])
        await self.events.create_index([("session_id", 1)])
        await self.app_usage_logs.create_index([("session_id", 1)])

    # User operations
    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        password_hash = self._hash_password(user_data.password)
        user_dict = user_data.dict()
        user_dict["password_hash"] = password_hash
        result = await self.users.insert_one(user_dict)
        user_dict["_id"] = str(result.inserted_id)
        return User(**user_dict)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        user_doc = await self.users.find_one({"email": email})
        if user_doc:
            user_doc["_id"] = str(user_doc["_id"])
            return User(**user_doc)
        return None

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        user_doc = await self.users.find_one({"_id": ObjectId(user_id)})
        if user_doc:
            user_doc["_id"] = str(user_doc["_id"])
            return User(**user_doc)
        return None

    async def verify_password(self, email: str, password: str) -> bool:
        """Verify user password."""
        user = await self.get_user_by_email(email)
        if not user:
            return False
        return user.password_hash == self._hash_password(password)

    def _hash_password(self, password: str) -> str:
        """Hash password."""
        return hashlib.sha256(password.encode()).hexdigest()

    # Task operations
    async def create_task(self, user_id: str, task_data: TaskCreate) -> Task:
        """Create a new task."""
        task_dict = task_data.dict()
        task_dict["user_id"] = ObjectId(user_id)
        # Generate permanent share token for this task
        task_dict["share_token"] = secrets.token_urlsafe(32)
        task_dict["total_time"] = 0.0
        task_dict["time_history"] = []
        result = await self.tasks.insert_one(task_dict)
        task_dict["_id"] = str(result.inserted_id)
        task_dict["user_id"] = str(task_dict["user_id"])
        return Task(**task_dict)

    async def get_tasks(self, user_id: str) -> List[Task]:
        """Get all tasks for a user."""
        cursor = self.tasks.find({"user_id": ObjectId(user_id)})
        tasks = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            doc["user_id"] = str(doc["user_id"])
            tasks.append(Task(**doc))
        return tasks

    async def get_task(self, task_id: str, user_id: str) -> Optional[Task]:
        """Get a task by ID."""
        task_doc = await self.tasks.find_one({
            "_id": ObjectId(task_id),
            "user_id": ObjectId(user_id)
        })
        if task_doc:
            task_doc["_id"] = str(task_doc["_id"])
            task_doc["user_id"] = str(task_doc["user_id"])
            return Task(**task_doc)
        return None

    async def update_task(self, task_id: str, user_id: str, task_data: dict) -> bool:
        """Update a task."""
        result = await self.tasks.update_one(
            {"_id": ObjectId(task_id), "user_id": ObjectId(user_id)},
            {"$set": task_data}
        )
        return result.modified_count > 0

    async def delete_task(self, task_id: str, user_id: str) -> bool:
        """Delete a task."""
        result = await self.tasks.delete_one({
            "_id": ObjectId(task_id),
            "user_id": ObjectId(user_id)
        })
        return result.deleted_count > 0

    async def update_task_time(self, task_id: str, duration: float, status: str = "active") -> bool:
        """Update task total time (without adding to history)."""
        # Update total time
        result = await self.tasks.update_one(
            {"_id": ObjectId(task_id)},
            {"$inc": {"total_time": duration}}
        )

        return result.modified_count > 0

    async def record_session(self, task_id: str, start_time: datetime, end_time: datetime, duration: float, status: str = "completed") -> bool:
        """Record a completed session to time history."""
        # Add to time history
        result = await self.tasks.update_one(
            {"_id": ObjectId(task_id)},
            {
                "$push": {
                    "time_history": {
                        "start_time": start_time,
                        "end_time": end_time,
                        "duration": duration,
                        "status": status
                    }
                }
            }
        )

        return result.modified_count > 0

    async def get_task_by_token(self, share_token: str) -> Optional[Task]:
        """Get task by share token (permanent link)."""
        task_doc = await self.tasks.find_one({
            "share_token": share_token
        })
        if task_doc:
            task_doc["_id"] = str(task_doc["_id"])
            task_doc["user_id"] = str(task_doc["user_id"])
            return Task(**task_doc)
        return None

    async def get_task_history(self, task_id: str, limit: int = 50) -> List[dict]:
        """Get time history for a task."""
        task = await self.tasks.find_one({"_id": ObjectId(task_id)})
        if not task:
            return []

        history = task.get("time_history", [])
        # Get the most recent entries
        history = sorted(history, key=lambda x: x.get("end_time", datetime.min) or x.get("timestamp", datetime.min), reverse=True)[:limit]

        return [
            {
                "start_time": entry.get("start_time").isoformat() if entry.get("start_time") else None,
                "end_time": entry.get("end_time").isoformat() if entry.get("end_time") else entry.get("timestamp"),
                "duration": entry.get("duration", 0),
                "status": entry.get("status", "unknown")
            }
            for entry in history
        ]

    # Session operations
    async def create_session(self, user_id: str, session_data: SessionCreate) -> Session:
        """Create a new tracking session."""
        share_token = secrets.token_urlsafe(32)
        # No expiration - permanent link for each task

        session_dict = {
            "task_id": ObjectId(session_data.task_id),
            "user_id": ObjectId(user_id),
            "share_token": share_token,
            "status": "stopped",
            "start_time": None,
            "end_time": None,
            "duration": 0.0,
            "expires_at": None  # Permanent link
        }

        result = await self.sessions.insert_one(session_dict)
        session_dict["_id"] = str(result.inserted_id)
        session_dict["task_id"] = str(session_dict["task_id"])
        session_dict["user_id"] = str(session_dict["user_id"])
        return Session(**session_dict)

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        session_doc = await self.sessions.find_one({"_id": ObjectId(session_id)})
        if session_doc:
            session_doc["_id"] = str(session_doc["_id"])
            session_doc["task_id"] = str(session_doc["task_id"])
            session_doc["user_id"] = str(session_doc["user_id"])
            return Session(**session_doc)
        return None

    async def get_session_by_token(self, share_token: str) -> Optional[Session]:
        """Get session by share token (permanent link)."""
        session_doc = await self.sessions.find_one({
            "share_token": share_token
        })
        if session_doc:
            session_doc["_id"] = str(session_doc["_id"])
            session_doc["task_id"] = str(session_doc["task_id"])
            session_doc["user_id"] = str(session_doc["user_id"])
            return Session(**session_doc)
        return None

    async def update_session(self, session_id: str, update_data: dict) -> bool:
        """Update session."""
        result = await self.sessions.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": update_data}
        )
        return result.modified_count > 0

    async def get_user_sessions(self, user_id: str) -> List[Session]:
        """Get all sessions for a user."""
        cursor = self.sessions.find({"user_id": ObjectId(user_id)})
        sessions = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            doc["task_id"] = str(doc["task_id"])
            doc["user_id"] = str(doc["user_id"])
            sessions.append(Session(**doc))
        return sessions

    # Event operations
    async def create_event(self, session_id: str, user_id: str, event_type: str, data: dict) -> TrackingEvent:
        """Create a tracking event."""
        event_dict = {
            "session_id": ObjectId(session_id),
            "user_id": ObjectId(user_id),
            "event_type": event_type,
            "data": data
        }
        result = await self.events.insert_one(event_dict)
        event_dict["_id"] = str(result.inserted_id)
        event_dict["session_id"] = str(event_dict["session_id"])
        event_dict["user_id"] = str(event_dict["user_id"])
        return TrackingEvent(**event_dict)

    async def get_session_events(self, session_id: str, limit: int = 100) -> List[TrackingEvent]:
        """Get recent events for a session."""
        cursor = self.events.find({"session_id": ObjectId(session_id)}).sort("timestamp", -1).limit(limit)
        events = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            doc["session_id"] = str(doc["session_id"])
            doc["user_id"] = str(doc["user_id"])
            events.append(TrackingEvent(**doc))
        return events

    # App usage operations
    async def log_app_usage(self, session_id: str, task_id: str, app_name: str, duration: float) -> AppUsageLog:
        """Log application usage."""
        log_dict = {
            "session_id": ObjectId(session_id),
            "task_id": ObjectId(task_id),
            "app_name": app_name,
            "duration": duration
        }
        result = await self.app_usage_logs.insert_one(log_dict)
        log_dict["_id"] = str(result.inserted_id)
        log_dict["session_id"] = str(log_dict["session_id"])
        log_dict["task_id"] = str(log_dict["task_id"])
        return AppUsageLog(**log_dict)

    async def get_session_app_usage(self, session_id: str) -> List[AppUsageLog]:
        """Get app usage for a session."""
        cursor = self.app_usage_logs.find({"session_id": ObjectId(session_id)})
        logs = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            doc["session_id"] = str(doc["session_id"])
            doc["task_id"] = str(doc["task_id"])
            logs.append(AppUsageLog(**doc))
        return logs

    async def get_task_app_summary(self, task_id: str) -> List[dict]:
        """Get app usage summary for a task."""
        pipeline = [
            {"$match": {"task_id": ObjectId(task_id)}},
            {"$group": {
                "_id": "$app_name",
                "total_duration": {"$sum": "$duration"},
                "sessions": {"$sum": 1}
            }},
            {"$sort": {"total_duration": -1}}
        ]
        cursor = self.app_usage_logs.aggregate(pipeline)
        return [
            {
                "app_name": doc["_id"],
                "total_duration": doc["total_duration"],
                "sessions": doc["sessions"]
            }
            async for doc in cursor
        ]

    async def close(self):
        """Close database connection."""
        self.client.close()


# Global database instance
db = Database()
