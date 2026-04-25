# TaskTimer Cloud - Real-Time Work Tracking Platform

A cloud-based real-time task tracking system with live employer viewing capabilities. Built with FastAPI, MongoDB, and PyQt5.

## 🌟 Features

### For Employees
- **Task Management**: Create, edit, and delete tasks with custom descriptions
- **Application Filtering**: Define which applications count toward each task
- **Intelligent Tracking**: Automatically pauses when:
  - User is idle (no keyboard/mouse activity)
  - User switches to a non-approved application
- **Real-time Monitoring**: See current status, timer, and active application
- **Live Sharing**: Generate shareable links for employers to view progress in real-time

### For Employers
- **Live Viewing**: Watch employee progress in real-time via shareable link
- **No Login Required**: View sessions without authentication
- **Real-time Updates**: WebSocket-powered live updates
- **Read-Only Access**: View-only access with no control capabilities
- **Session Details**: See task name, timer, active app, idle status, and app usage

## 🏗️ Architecture

```
TaskTimer Cloud/
├── backend/                 # FastAPI + MongoDB backend
│   ├── api/                # API endpoints
│   ├── models/            # MongoDB models & schemas
│   ├── services/          # Business logic & auth
│   ├── websocket/         # WebSocket connection manager
│   ├── templates/         # Web live dashboard
│   ├── main.py            # FastAPI application
│   └── requirements.txt   # Backend dependencies
├── desktop_client/         # PyQt5 desktop application
│   ├── api_client.py      # API client for backend communication
│   ├── cloud_tracking_engine.py  # Cloud-based tracking engine
│   ├── login_dialog.py    # Authentication dialog
│   ├── cloud_dashboard.py # Main dashboard UI
│   └── requirements.txt   # Desktop dependencies
├── core/                   # Shared core modules
│   ├── idle_detector.py   # Keyboard/mouse activity detection
│   └── app_monitor.py     # Active window monitoring
├── ui/                     # Shared UI components
│   ├── dashboard.py       # Original dashboard (local mode)
│   ├── task_dialog.py     # Task creation/editing dialog
│   └── compact_timer.py   # Compact overlay timer
└── main_cloud.py          # Cloud desktop app entry point
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- MongoDB 4.4+
- Operating System: Windows, macOS, or Linux

### 1. Install MongoDB

**Ubuntu/Debian:**
```bash
sudo apt-get install mongodb
sudo systemctl start mongodb
```

**macOS:**
```bash
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community
```

**Windows:**
Download and install from [MongoDB官网](https://www.mongodb.com/try/download/community)

### 2. Start Backend Server

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Start server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### 3. Run Desktop Client

```bash
# Install dependencies
pip install -r desktop_client/requirements.txt

# On Linux, also install:
sudo apt-get install xdotool wmctrl

# Run the application
python main_cloud.py
```

## 📡 API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `GET /api/auth/me` - Get current user info

### Tasks
- `POST /api/tasks` - Create task
- `GET /api/tasks` - Get all tasks
- `GET /api/tasks/{task_id}` - Get specific task
- `PUT /api/tasks/{task_id}` - Update task
- `DELETE /api/tasks/{task_id}` - Delete task

### Sessions
- `POST /api/sessions` - Create tracking session
- `GET /api/sessions` - Get all sessions
- `GET /api/sessions/{session_id}` - Get specific session
- `POST /api/sessions/{session_id}/start` - Start tracking
- `POST /api/sessions/{session_id}/stop` - Stop tracking
- `POST /api/sessions/{session_id}/update` - Update session data

### Live Viewing
- `GET /api/live/{share_token}` - Get live session data
- `WS /ws/live/{share_token}` - WebSocket for real-time updates

## 🔐 Security Features

- **JWT Authentication**: Secure token-based authentication
- **Expiring Links**: Shareable links expire after configurable time (default 24 hours)
- **Read-Only Access**: Employers can only view, not modify
- **Token Validation**: All API calls require valid authentication
- **Secure Passwords**: Passwords are hashed before storage

## 🗄️ MongoDB Collections

### users
```json
{
  "_id": ObjectId,
  "email": "user@example.com",
  "password_hash": "sha256_hash",
  "name": "User Name",
  "created_at": ISODate
}
```

### tasks
```json
{
  "_id": ObjectId,
  "user_id": ObjectId,
  "name": "Task Name",
  "description": "Task Description",
  "allowed_apps": ["app1", "app2"],
  "created_at": ISODate
}
```

### sessions
```json
{
  "_id": ObjectId,
  "task_id": ObjectId,
  "user_id": ObjectId,
  "share_token": "unique_token",
  "status": "active|idle|paused|stopped",
  "start_time": ISODate,
  "end_time": ISODate,
  "duration": 123.45,
  "expires_at": ISODate,
  "created_at": ISODate
}
```

### events
```json
{
  "_id": ObjectId,
  "session_id": ObjectId,
  "user_id": ObjectId,
  "event_type": "status|timer|app|idle",
  "data": {},
  "timestamp": ISODate
}
```

### app_usage_logs
```json
{
  "_id": ObjectId,
  "session_id": ObjectId,
  "task_id": ObjectId,
  "app_name": "Application Name",
  "duration": 123.45,
  "timestamp": ISODate
}
```

## 🎯 Usage Guide

### For Employees

1. **Register/Login**: Open the desktop app and create an account or login
2. **Create Task**: Click "+ New Task" and define your task
3. **Add Allowed Apps**: Select which applications count toward this task
4. **Start Tracking**: Select a task and click "Start Tracking"
5. **Generate Live Link**: Click "Generate Live Link" to share with employer
6. **Monitor Progress**: The timer only runs when you're actively working on allowed apps

### For Employers

1. **Receive Link**: Get the live link from the employee
2. **Open in Browser**: Navigate to the link (no login required)
3. **View Progress**: See real-time updates of:
   - Task name and duration
   - Current active application
   - Idle/active status
   - App usage breakdown

## 🔧 Configuration

### Backend Configuration

Edit `backend/main.py` to change:

```python
# MongoDB connection
DATABASE_URL = "mongodb://localhost:27017"

# JWT secret key
SECRET_KEY = "your-secret-key-change-in-production"

# Token expiration
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
```

### Desktop Client Configuration

Edit `main_cloud.py` to change:

```python
# API base URL
api = TaskTimerAPIClient(base_url="http://localhost:8000")
```

## 🌐 Live Dashboard

The live dashboard is accessible at:
```
http://localhost:8000/live/{share_token}
```

Features:
- Real-time timer updates
- Status indicators (Active/Idle/Paused/Stopped)
- Current application display
- App usage breakdown
- Viewer count
- Auto-reconnection on disconnect

## 📱 Platform-Specific Notes

### Windows
- Requires pywin32 for window detection
- May require administrator privileges

### Linux
- Requires xdotool and wmctrl for window detection
- Works best with X11-based desktop environments

### macOS
- Uses AppleScript for window detection
- Requires accessibility permissions

## 🔒 Privacy

TaskTimer Cloud is designed with privacy in mind:

- **No Keystroke Logging**: Only detects activity presence
- **No Screen Capture**: Never captures or records screen content
- **Secure Storage**: All data stored in MongoDB with proper authentication
- **Expiring Links**: Shareable links automatically expire
- **Read-Only Access**: Employers cannot modify any data

## 🐛 Troubleshooting

### Backend won't start
- Ensure MongoDB is running
- Check port 8000 is not in use
- Verify all dependencies are installed

### Desktop app can't connect
- Verify backend is running
- Check API base URL in `main_cloud.py`
- Ensure network connectivity

### Window detection not working
- **Linux**: Install xdotool and wmctrl
- **macOS**: Grant accessibility permissions
- **Windows**: Run as administrator if needed

### Live link not working
- Verify share token is valid
- Check if link has expired
- Ensure WebSocket connection is working

## 📝 Development

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Desktop client tests
pytest desktop_client/
```

### Building for Distribution

```bash
# Create executable with PyInstaller
pip install pyinstaller
pyinstaller --onefile --windowed main_cloud.py
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## 📄 License

This project is provided as-is for educational and personal use.

## 🆘 Support

For issues or questions, please check the troubleshooting section or create an issue in the project repository.
