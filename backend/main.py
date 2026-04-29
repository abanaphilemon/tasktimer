"""
FastAPI backend for TaskTimer Cloud.
"""

from datetime import datetime, timedelta
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from models.database import db
from models.schemas import (
    UserCreate, UserLogin, UserResponse, AuthResponse,
    TaskCreate, TaskUpdate, SessionCreate, SessionResponse,
    LiveSessionData
)
from services.auth import (
    create_access_token, get_current_user, verify_share_token
)
from websocket.manager import manager
from config import settings

# Initialize templates
templates = Jinja2Templates(directory="templates")

# Initialize FastAPI app
app = FastAPI(
    title="TaskTimer Cloud API",
    description="Real-time task tracking with live viewing",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()


@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    await db.create_indexes()


@app.on_event("shutdown")
async def shutdown():
    """Close database connection on shutdown."""
    await db.close()


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow()}


# Authentication endpoints
@app.post("/api/auth/register", response_model=AuthResponse)
async def register(user_data: UserCreate):
    """Register a new user."""
    # Check if user already exists
    existing_user = await db.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create user
    user = await db.create_user(user_data)

    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})

    return AuthResponse(
        access_token=access_token,
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            name=user.name,
            created_at=user.created_at
        )
    )


@app.post("/api/auth/login", response_model=AuthResponse)
async def login(user_data: UserLogin):
    """Login user."""
    # Verify password
    if not await db.verify_password(user_data.email, user_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Get user
    user = await db.get_user_by_email(user_data.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})

    return AuthResponse(
        access_token=access_token,
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            name=user.name,
            created_at=user.created_at
        )
    )


@app.get("/api/auth/me", response_model=UserResponse)
async def get_me(current_user = Depends(get_current_user)):
    """Get current user info."""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        created_at=current_user.created_at
    )


# Task endpoints
@app.post("/api/tasks")
async def create_task(task_data: TaskCreate, current_user = Depends(get_current_user)):
    """Create a new task."""
    task = await db.create_task(str(current_user.id), task_data)
    return {
        "id": str(task.id),
        "name": task.name,
        "description": task.description,
        "allowed_apps": task.allowed_apps,
        "created_at": task.created_at,
        "total_time": task.total_time,
        "share_token": task.share_token
    }


@app.get("/api/tasks")
async def get_tasks(current_user = Depends(get_current_user)):
    """Get all tasks for current user."""
    tasks = await db.get_tasks(str(current_user.id))
    return [
        {
            "id": str(task.id),
            "name": task.name,
            "description": task.description,
            "allowed_apps": task.allowed_apps,
            "created_at": task.created_at,
            "total_time": task.total_time,
            "share_token": task.share_token
        }
        for task in tasks
    ]


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str, current_user = Depends(get_current_user)):
    """Get a specific task."""
    task = await db.get_task(task_id, str(current_user.id))
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return {
        "id": str(task.id),
        "name": task.name,
        "description": task.description,
        "allowed_apps": task.allowed_apps,
        "created_at": task.created_at,
        "total_time": task.total_time,
        "time_history": task.time_history,
        "share_token": task.share_token
    }


@app.put("/api/tasks/{task_id}")
async def update_task(task_id: str, task_data: TaskUpdate, current_user = Depends(get_current_user)):
    """Update a task."""
    update_dict = task_data.dict(exclude_unset=True)
    success = await db.update_task(task_id, str(current_user.id), update_dict)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return {"message": "Task updated successfully"}


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str, current_user = Depends(get_current_user)):
    """Delete a task."""
    success = await db.delete_task(task_id, str(current_user.id))
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return {"message": "Task deleted successfully"}

@app.get("/api/tasks/{task_id}/app-summary")
async def get_task_app_summary(task_id: str, current_user = Depends(get_current_user)):
    """Get app usage summary for a task."""
    app_summary = await db.get_task_app_summary(task_id)
    return app_summary


@app.get("/api/tasks/{task_id}/sessions")
async def get_task_sessions(task_id: str, current_user = Depends(get_current_user)):
    """Get completed sessions for a task."""
    sessions = await db.get_task_sessions(task_id)
    return sessions


@app.post("/api/tasks/{task_id}/generate-share-link")
async def generate_share_link(task_id: str, current_user = Depends(get_current_user)):
    """Generate a share link for an existing task."""
    task = await db.get_task(task_id, str(current_user.id))
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # If task already has a share token, return it
    if task.share_token:
        return {
            "share_token": task.share_token,
            "live_link": f"/live/{task.share_token}"
        }

    # Generate new share token
    import secrets
    share_token = secrets.token_urlsafe(32)
    success = await db.update_task(task_id, str(current_user.id), {"share_token": share_token})

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate share link"
        )

    return {
        "share_token": share_token,
        "live_link": f"/live/{share_token}"
    }


# Session endpoints
@app.post("/api/sessions", response_model=SessionResponse)
async def create_session(session_data: SessionCreate, current_user = Depends(get_current_user)):
    """Create a new tracking session (uses task's permanent link)."""
    # Get task to use its share_token
    task = await db.get_task(session_data.task_id, str(current_user.id))
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Create session without its own share_token (use task's)
    session = await db.create_session(str(current_user.id), session_data)

    return SessionResponse(
        id=str(session.id),
        task_id=str(session.task_id),
        share_token=task.share_token or "",  # Use task's share_token
        status=session.status,
        start_time=session.start_time,
        end_time=session.end_time,
        duration=session.duration,
        expires_at=None,  # Permanent
        live_link=f"/live/{task.share_token or ''}"
    )


@app.get("/api/sessions")
async def get_sessions(current_user = Depends(get_current_user)):
    """Get all sessions for current user."""
    sessions = await db.get_user_sessions(str(current_user.id))
    return [
        {
            "id": str(session.id),
            "task_id": str(session.task_id),
            "share_token": session.share_token,
            "status": session.status,
            "start_time": session.start_time,
            "end_time": session.end_time,
            "duration": session.duration,
            "expires_at": session.expires_at,
            "live_link": f"/live/{session.share_token}"
        }
        for session in sessions
    ]


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str, current_user = Depends(get_current_user)):
    """Get a specific session."""
    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    return {
        "id": str(session.id),
        "task_id": str(session.task_id),
        "share_token": session.share_token,
        "status": session.status,
        "start_time": session.start_time,
        "end_time": session.end_time,
        "duration": session.duration,
        "expires_at": session.expires_at,
        "live_link": f"/live/{session.share_token}"
    }


@app.post("/api/sessions/{session_id}/start")
async def start_session(session_id: str, current_user = Depends(get_current_user)):
    """Start tracking a session."""
    session = await db.get_session(session_id)
    if not session or str(session.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    await db.update_session(session_id, {
        "status": "active",
        "start_time": datetime.utcnow()
    })

    # Broadcast to viewers
    await manager.broadcast_to_session(session_id, {
        "type": "session_started",
        "session_id": session_id,
        "timestamp": datetime.utcnow().isoformat()
    })

    return {"message": "Session started"}


@app.post("/api/sessions/{session_id}/stop")
async def stop_session(session_id: str, current_user = Depends(get_current_user)):
    """Stop tracking a session."""
    session = await db.get_session(session_id)
    if not session or str(session.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    end_time = datetime.utcnow()
    start_time = session.start_time or end_time

    # Calculate duration if not already set
    duration = session.duration
    if duration == 0 and start_time:
        duration = (end_time - start_time).total_seconds()

    await db.update_session(session_id, {
        "status": "stopped",
        "end_time": end_time,
        "duration": duration
    })

    # Record session in task history
    if duration > 0:
        await db.record_session(str(session.task_id), start_time, end_time, duration, "completed")

    # Broadcast to viewers
    await manager.broadcast_to_session(session_id, {
        "type": "session_stopped",
        "session_id": session_id,
        "timestamp": end_time.isoformat()
    })

    return {"message": "Session stopped"}


@app.post("/api/sessions/{session_id}/update")
async def update_session_data(session_id: str, data: dict, current_user = Depends(get_current_user)):
    """Update session tracking data."""
    session = await db.get_session(session_id)
    if not session or str(session.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    task_id = str(session.task_id)

    # Update session
    update_dict = {}
    if "duration" in data:
        update_dict["duration"] = data["duration"]
    if "status" in data:
        update_dict["status"] = data["status"]

    if update_dict:
        await db.update_session(session_id, update_dict)

    # Log app usage and update total_time if status is active
    if "current_app" in data and data["current_app"] and data.get("status") == "active":
        # Use delta (incremental time) for accurate app usage tracking
        app_duration = data.get("delta", 5.0)
        await db.log_app_usage(session_id, task_id, data["current_app"], app_duration)
        # Update task total_time with the delta
        await db.update_task_time(task_id, app_duration, data.get("status", "active"))

    # Create event
    await db.create_event(session_id, str(current_user.id), data.get("event_type", "update"), data)

    # Get app usage summary for broadcast
    app_usage = await db.get_task_app_summary(task_id)

    # Get task data for broadcast
    task = await db.get_task(task_id, str(current_user.id))
    time_history = await db.get_task_history(task_id)

    # Broadcast to viewers (use task_id for live viewing)
    await manager.broadcast_to_session(task_id, {
        "type": "session_update",
        "session_id": session_id,
        "task_id": task_id,
        "data": {
            **data,
            "app_usage": app_usage,
            "total_time": task.total_time if task else 0,
            "time_history": time_history
        },
        "timestamp": datetime.utcnow().isoformat()
    })

    return {"message": "Session updated"}


# Live viewing page (no auth required)
@app.get("/live/{share_token}", response_class=HTMLResponse)
async def live_view_page(share_token: str, request: Request):
    """Serve the live viewing page."""
    try:
        return templates.TemplateResponse("live.html", {"request": request})
    except Exception as e:
        # Fallback: return HTML directly
        with open("templates/live.html", "r") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)


# Live viewing endpoint (no auth required)
@app.get("/api/live/{share_token}")
async def get_live_session(share_token: str):
    """Get live task data for viewing (no auth required)."""
    task_info = await verify_share_token(share_token)
    if not task_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid share token"
        )

    # Get task data
    task = await db.get_task(task_info["task_id"], task_info["user_id"])
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Get current active session for this task
    sessions = await db.get_user_sessions(task_info["user_id"])
    current_session = None
    for session in sessions:
        if str(session.task_id) == task_info["task_id"] and session.status in ["active", "idle", "paused"]:
            current_session = session
            break

    # Get time history
    time_history = await db.get_task_history(task_info["task_id"])

    # Get app usage for this task
    app_usage_summary = await db.get_task_app_summary(task_info["task_id"])

    return {
        "task_id": str(task.id),
        "task_name": task.name,
        "task_description": task.description or "",
        "total_time": task.total_time,
        "status": current_session.status if current_session else "stopped",
        "duration": current_session.duration if current_session else 0.0,
        "start_time": current_session.start_time if current_session else None,
        "end_time": current_session.end_time if current_session else None,
        "viewer_count": manager.get_viewer_count(task_info["task_id"]),
        "time_history": time_history,
        "app_usage": app_usage_summary,
        "allowed_apps": task.allowed_apps
    }


# WebSocket endpoint for live viewing
@app.websocket("/ws/live/{share_token}")
async def websocket_live_view(websocket: WebSocket, share_token: str):
    """WebSocket endpoint for live task viewing."""
    # Verify share token (task-based)
    task_info = await verify_share_token(share_token)
    if not task_info:
        await websocket.close(code=1008, reason="Invalid share token")
        return

    task_id = task_info["task_id"]

    # Get task data
    task = await db.get_task(task_id, task_info["user_id"])
    if not task:
        await websocket.close(code=1008, reason="Task not found")
        return

    # Get current active session for this task
    sessions = await db.get_user_sessions(task_info["user_id"])
    current_session = None
    for session in sessions:
        if str(session.task_id) == task_id and session.status in ["active", "idle", "paused"]:
            current_session = session
            break

    # Connect viewer to task
    await manager.connect(task_id, websocket)

    # Get app usage summary
    app_usage = await db.get_task_app_summary(task_id)

    # Get time history
    time_history = await db.get_task_history(task_id)

    try:
        # Send initial data
        await websocket.send_json({
            "type": "connected",
            "task_id": task_id,
            "task_name": task.name,
            "status": current_session.status if current_session else "stopped",
            "duration": current_session.duration if current_session else 0.0,
            "total_time": task.total_time,
            "viewer_count": manager.get_viewer_count(task_id),
            "app_usage": app_usage,
            "time_history": time_history,
            "start_time": current_session.start_time.isoformat() if current_session and current_session.start_time else None
        })

        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_json()

            # Viewers can only send ping/pong
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(task_id, websocket)
