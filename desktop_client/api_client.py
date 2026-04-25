"""
API client for TaskTimer Cloud.
Handles all communication with the FastAPI backend.
"""

import requests
import websockets
import json
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime


class TaskTimerAPIClient:
    """Client for TaskTimer Cloud API."""

    def __init__(self, base_url: str = "https://tasktimer-rg7b.onrender.com"):
        self.base_url = base_url.rstrip('/')
        self.access_token: Optional[str] = None
        self.user_id: Optional[str] = None

    def set_token(self, token: str):
        """Set authentication token."""
        self.access_token = token

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    # Authentication
    def register(self, email: str, password: str, name: str) -> Dict[str, Any]:
        """Register a new user."""
        response = requests.post(
            f"{self.base_url}/api/auth/register",
            json={"email": email, "password": password, "name": name}
        )
        response.raise_for_status()
        data = response.json()
        self.access_token = data["access_token"]
        self.user_id = data["user"]["id"]
        return data

    def login(self, email: str, password: str) -> Dict[str, Any]:
        """Login user."""
        response = requests.post(
            f"{self.base_url}/api/auth/login",
            json={"email": email, "password": password}
        )
        response.raise_for_status()
        data = response.json()
        self.access_token = data["access_token"]
        self.user_id = data["user"]["id"]
        return data

    def get_me(self) -> Dict[str, Any]:
        """Get current user info."""
        response = requests.get(
            f"{self.base_url}/api/auth/me",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    # Tasks
    def create_task(self, name: str, description: str = "", allowed_apps: List[str] = None) -> Dict[str, Any]:
        """Create a new task."""
        response = requests.post(
            f"{self.base_url}/api/tasks",
            json={"name": name, "description": description, "allowed_apps": allowed_apps or []},
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def get_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks."""
        response = requests.get(
            f"{self.base_url}/api/tasks",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def get_task(self, task_id: str) -> Dict[str, Any]:
        """Get a specific task."""
        response = requests.get(
            f"{self.base_url}/api/tasks/{task_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def update_task(self, task_id: str, name: str = None, description: str = None, allowed_apps: List[str] = None) -> Dict[str, Any]:
        """Update a task."""
        data = {}
        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description
        if allowed_apps is not None:
            data["allowed_apps"] = allowed_apps

        response = requests.put(
            f"{self.base_url}/api/tasks/{task_id}",
            json=data,
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def delete_task(self, task_id: str) -> Dict[str, Any]:
        """Delete a task."""
        response = requests.delete(
            f"{self.base_url}/api/tasks/{task_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def get_task_app_summary(self, task_id: str) -> List[Dict[str, Any]]:
        """Get app usage summary for a task."""
        response = requests.get(
            f"{self.base_url}/api/tasks/{task_id}/app-summary",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def generate_share_link(self, task_id: str) -> Dict[str, Any]:
        """Generate a share link for an existing task."""
        response = requests.post(
            f"{self.base_url}/api/tasks/{task_id}/generate-share-link",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    # Sessions
    def create_session(self, task_id: str, expires_hours: int = 24) -> Dict[str, Any]:
        """Create a new tracking session."""
        response = requests.post(
            f"{self.base_url}/api/sessions",
            json={"task_id": task_id, "expires_hours": expires_hours},
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def get_sessions(self) -> List[Dict[str, Any]]:
        """Get all sessions."""
        response = requests.get(
            f"{self.base_url}/api/sessions",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get a specific session."""
        response = requests.get(
            f"{self.base_url}/api/sessions/{session_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def start_session(self, session_id: str) -> Dict[str, Any]:
        """Start tracking a session."""
        response = requests.post(
            f"{self.base_url}/api/sessions/{session_id}/start",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def stop_session(self, session_id: str) -> Dict[str, Any]:
        """Stop tracking a session."""
        response = requests.post(
            f"{self.base_url}/api/sessions/{session_id}/stop",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def update_session(self, session_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update session tracking data."""
        response = requests.post(
            f"{self.base_url}/api/sessions/{session_id}/update",
            json=data,
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def get_live_session(self, share_token: str) -> Dict[str, Any]:
        """Get live session data (no auth required)."""
        response = requests.get(
            f"{self.base_url}/api/live/{share_token}"
        )
        response.raise_for_status()
        return response.json()

    def get_live_link(self, share_token: str) -> str:
        """Get live viewing link."""
        return f"{self.base_url}/live/{share_token}"

    # Health check
    def health_check(self) -> Dict[str, Any]:
        """Check API health."""
        response = requests.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()


class TaskTimerWebSocketClient:
    """WebSocket client for real-time updates."""

    def __init__(self, base_url: str = "ws://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.callbacks: Dict[str, List[callable]] = {}

    def on(self, event_type: str, callback: callable):
        """Register callback for event type."""
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        self.callbacks[event_type].append(callback)

    async def connect(self, share_token: str):
        """Connect to live session WebSocket."""
        ws_url = f"{self.base_url}/ws/live/{share_token}"
        self.websocket = await websockets.connect(ws_url)

    async def disconnect(self):
        """Disconnect from WebSocket."""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None

    async def listen(self):
        """Listen for messages."""
        if not self.websocket:
            raise RuntimeError("Not connected")

        async for message in self.websocket:
            data = json.loads(message)
            event_type = data.get("type")

            # Call registered callbacks
            if event_type in self.callbacks:
                for callback in self.callbacks[event_type]:
                    await callback(data)

    async def send(self, data: Dict[str, Any]):
        """Send message to server."""
        if not self.websocket:
            raise RuntimeError("Not connected")
        await self.websocket.send(json.dumps(data))
