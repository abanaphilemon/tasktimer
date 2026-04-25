# TaskTimer Cloud - Quick Start Guide

## 🚀 Quick Start

### 1. Start MongoDB

```bash
# Linux
sudo systemctl start mongodb

# macOS
brew services start mongodb-community

# Windows
# MongoDB service starts automatically after installation
```

### 2. Start Backend Server

```bash
cd /home/abanaphilemon/TaskTimer/backend

# Option 1: Use startup script
./start.sh

# Option 2: Manual start
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: `http://localhost:8000`

### 3. Start Desktop Client

```bash
cd /home/abanaphilemon/TaskTimer

# Option 1: Use startup script
./start_cloud.sh

# Option 2: Manual start
python3 main_cloud.py
```

## 📡 API Documentation

Once the backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔗 Live Viewing

1. Login to desktop app
2. Create a task with allowed apps
3. Start tracking
4. Click "Generate Live Link"
5. Share the link with your employer

Employer opens link and sees real-time updates!

## 🗂️ Project Structure

```
TaskTimer/
├── backend/                    # FastAPI + MongoDB
│   ├── main.py               # API endpoints
│   ├── models/               # MongoDB models
│   ├── services/             # Auth & business logic
│   ├── websocket/            # Real-time updates
│   ├── templates/            # Web live dashboard
│   ├── requirements.txt      # Backend deps
│   └── start.sh             # Startup script
├── desktop_client/            # PyQt5 app
│   ├── api_client.py        # API communication
│   ├── cloud_tracking_engine.py  # Cloud tracking
│   ├── login_dialog.py      # Authentication
│   ├── cloud_dashboard.py   # Main UI
│   └── requirements.txt     # Desktop deps
├── core/                      # Shared modules
│   ├── idle_detector.py     # Activity detection
│   └── app_monitor.py       # Window monitoring
├── ui/                        # Shared UI components
│   ├── task_dialog.py       # Task dialog
│   └── compact_timer.py     # Overlay timer
├── main_cloud.py            # Desktop app entry
├── start_cloud.sh           # Desktop startup script
└── README_CLOUD.md          # Full documentation
```

## 🔐 Default Configuration

- **MongoDB**: `mongodb://localhost:27017`
- **API URL**: `http://localhost:8000`
- **JWT Secret**: `your-secret-key-change-in-production`
- **Token Expiry**: 7 days
- **Link Expiry**: 24 hours

## 🛠️ Troubleshooting

### MongoDB won't start
```bash
# Check status
sudo systemctl status mongodb

# Start manually
mongod --dbpath /var/lib/mongodb --logpath /var/log/mongodb.log
```

### Backend won't start
```bash
# Check if port 8000 is in use
lsof -i :8000

# Kill process
kill -9 <PID>
```

### Desktop app can't connect
- Verify backend is running
- Check API URL in `main_cloud.py`
- Ensure network connectivity

## 📱 Platform-Specific Setup

### Linux
```bash
sudo apt-get install xdotool wmctrl
```

### macOS
```bash
# Grant accessibility permissions in System Preferences
```

### Windows
```bash
pip install pywin32
```

## 🎯 Next Steps

1. Change the JWT secret in `backend/services/auth.py`
2. Configure MongoDB connection if needed
3. Deploy backend to a cloud server
4. Build desktop app executable with PyInstaller
5. Set up reverse proxy with nginx

## 📚 Full Documentation

See [README_CLOUD.md](README_CLOUD.md) for complete documentation.
