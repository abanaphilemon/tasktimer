"""
MongoDB models for TaskTimer Cloud.
"""

from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema
from bson.objectid import ObjectId


class PyObjectId(str):
    """Pydantic ObjectId wrapper for Pydantic v2."""

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """Get Pydantic core schema."""
        return core_schema.no_info_after_validator_function(
            cls.validate,
            core_schema.str_schema(),
        )

    @classmethod
    def validate(cls, v: Any) -> "PyObjectId":
        """Validate ObjectId."""
        if isinstance(v, str):
            if not ObjectId.is_valid(v):
                raise ValueError("Invalid ObjectId")
            return cls(v)
        if isinstance(v, ObjectId):
            return cls(str(v))
        raise ValueError("Invalid ObjectId")


class User(BaseModel):
    """User model for authentication."""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    email: str = Field(..., unique=True)
    password_hash: str
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )


class Task(BaseModel):
    """Task model."""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    name: str
    description: Optional[str] = ""
    allowed_apps: List[str] = Field(default_factory=list)
    share_token: Optional[str] = None  # Permanent link for this task
    total_time: float = 0.0  # Total time worked on this task
    time_history: List[dict] = Field(default_factory=list)  # History of time logs
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )


class Session(BaseModel):
    """Tracking session model."""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    task_id: PyObjectId
    user_id: PyObjectId
    share_token: str
    status: str = "stopped"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: float = 0.0
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )


class TrackingEvent(BaseModel):
    """Real-time tracking event."""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    session_id: PyObjectId
    user_id: PyObjectId
    event_type: str
    data: dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )


class AppUsageLog(BaseModel):
    """Application usage log."""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    session_id: PyObjectId
    task_id: PyObjectId
    app_name: str
    duration: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )


# Request/Response Models
class UserCreate(BaseModel):
    email: str
    password: str
    name: str


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    created_at: datetime


class TaskCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    allowed_apps: List[str] = Field(default_factory=list)


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    allowed_apps: Optional[List[str]] = None


class SessionCreate(BaseModel):
    task_id: str
    expires_hours: Optional[int] = 24


class SessionResponse(BaseModel):
    id: str
    task_id: str
    share_token: str
    status: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    duration: float
    expires_at: Optional[datetime]
    live_link: str


class LiveSessionData(BaseModel):
    """Live session data for WebSocket."""
    session_id: str
    task_name: str
    status: str
    duration: float
    current_app: Optional[str] = None
    idle_time: float = 0.0
    last_update: datetime


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
