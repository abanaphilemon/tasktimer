# TaskTimer Deployment Guide

This guide explains how to deploy TaskTimer to production.

---

## What is TaskTimer?

TaskTimer is a **desktop application** (PyQt5) that connects to a **cloud backend** (FastAPI + MongoDB).

**Architecture:**
- **Desktop Client**: PyQt5 application that runs on user's computer
- **Backend API**: FastAPI server deployed to cloud
- **Database**: MongoDB Atlas for storing data
- **Live View**: Web page for real-time tracking viewing

---

## Deployment Overview

You need to deploy TWO things:

1. **Backend API** - Deploy to Render.com (or similar)
2. **Desktop Application** - Distribute as executable (.exe, .app, or .bin)

The database (MongoDB) is hosted on MongoDB Atlas.

---

## Part 1: Deploy Backend API

### Step 1: Set Up MongoDB Atlas

1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Click "Try Free" and create an account
3. Click "Build a Database"
4. Choose "M0 Sandbox" (Free) and click "Create"
5. Choose AWS and a region near you
6. Set cluster name to `tasktimer` and click "Create"
7. Create a database user:
   - Username: `tasktimer`
   - Password: Generate a strong password (SAVE THIS!)
   - Click "Create User"
8. Add IP Access:
   - Choose "Allow Access from Anywhere" (0.0.0.0/0)
   - Click "Finish and Close"
9. Click "Connect" → "Drivers"
10. Copy your connection string

**Your connection string will look like:**
```
mongodb+srv://tasktimer:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/tasktimer
```

### Step 2: Prepare Backend Code

#### 2.1 Update `backend/config.py`

Open `backend/config.py` and change:

```python
# BEFORE
mongodb_url: str = "mongodb://localhost:27017"
secret_key: str = "your-secret-key-change-in-production"

# AFTER
mongodb_url: str = ""  # Will come from environment variable
secret_key: str = ""  # Will come from environment variable
```

#### 2.2 Create `backend/.env` file

Create a new file `backend/.env`:

```env
MONGODB_URL=mongodb+srv://tasktimer:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/tasktimer
SECRET_KEY=your-random-secret-key-here
CORS_ORIGINS=*
```

**Generate a secret key:**
```bash
openssl rand -hex 32
```

#### 2.3 Create `backend/.gitignore`

Create `backend/.gitignore`:

```
__pycache__/
*.pyc
venv/
.venv/
.env
*.log
```

### Step 3: Push Code to GitHub

1. Go to [GitHub.com](https://github.com) and create a new repository
2. Name it `tasktimer`
3. Open terminal in your project folder:

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/tasktimer.git
git push -u origin main
```

### Step 4: Deploy to Render.com

1. Go to [Render.com](https://render.com) and create an account
2. Click "New +" → "Web Service"
3. Connect your GitHub account
4. Select your `tasktimer` repository
5. Configure:

   **Name**: `tasktimer-backend`

   **Root Directory**: `backend`

   **Build Command**:
   ```
   pip install -r requirements.txt
   ```

   **Start Command**:
   ```
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

6. Click "Advanced" → "Add Environment Variable":

   | Key | Value |
   |-----|-------|
   | `MONGODB_URL` | Your MongoDB connection string |
   | `SECRET_KEY` | Your generated secret key |
   | `CORS_ORIGINS` | `*` |

7. Click "Create Web Service"
8. Wait for deployment (2-5 minutes)
9. Copy your backend URL (e.g., `https://tasktimer-backend.onrender.com`)

---

## Part 2: Update Desktop Client

### Step 1: Update API URL

Open `main_cloud.py` and change:

```python
# BEFORE
api = TaskTimerAPIClient(base_url="http://localhost:8000")

# AFTER
api = TaskTimerAPIClient(base_url="https://tasktimer-backend.onrender.com")
```

Also update `desktop_client/api_client.py`:

```python
# BEFORE
def __init__(self, base_url: str = "http://localhost:8000"):

# AFTER
def __init__(self, base_url: str = "https://tasktimer-backend.onrender.com"):
```

### Step 2: Update WebSocket URL

Open `backend/templates/live.html` and find:

```javascript
// BEFORE
const wsUrl = `ws://${window.location.host}/ws/live/${shareToken}`;

// AFTER
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${protocol}//${window.location.host}/ws/live/${shareToken}`;
```

---

## Part 3: Distribute Desktop Application

### Option 1: PyInstaller (Recommended)

#### 3.1 Install PyInstaller

```bash
pip install pyinstaller
```

#### 3.2 Create Executable

**For Windows:**
```bash
pyinstaller --onefile --windowed --name=TaskTimer main_cloud.py
```

**For macOS:**
```bash
pyinstaller --onefile --windowed --name=TaskTimer main_cloud.py
```

**For Linux:**
```bash
pyinstaller --onefile --name=TaskTimer main_cloud.py
```

The executable will be in the `dist/` folder.

#### 3.3 Add Icon (Optional)

Create a `TaskTimer.spec` file:

```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main_cloud.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('ui', 'ui'),
        ('core', 'core'),
        ('desktop_client', 'desktop_client'),
        ('utils', 'utils'),
    ],
    hiddenimports=[
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtWidgets',
        'PyQt5.QtGui',
        'psutil',
        'pynput',
        'requests',
        'websockets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TaskTimer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico'  # Add your icon file
)
```

Then run:
```bash
pyinstaller TaskTimer.spec
```

### Option 2: PyInstaller with All Dependencies

If you get import errors, use this command:

```bash
pyinstaller --onefile --windowed --name=TaskTimer \
    --add-data "assets:assets" \
    --add-data "ui:ui" \
    --add-data "core:core" \
    --add-data "desktop_client:desktop_client" \
    --add-data "utils:utils" \
    --hidden-import PyQt5 \
    --hidden-import PyQt5.QtCore \
    --hidden-import PyQt5.QtWidgets \
    --hidden-import PyQt5.QtGui \
    --hidden-import psutil \
    --hidden-import pynput \
    --hidden-import requests \
    --hidden-import websockets \
    main_cloud.py
```

---

## Part 4: Test Deployment

### Test Backend API

Open your browser and visit:

```
https://tasktimer-backend.onrender.com/health
```

You should see:
```json
{"status": "healthy", "timestamp": "..."}
```

### Test Desktop App

1. Run the executable you created
2. Try to register/login
3. Create a task
4. Start tracking
5. Generate a live link
6. Open the live link in a browser

---

## Part 5: Distribute to Users

### For Windows Users

1. Upload `TaskTimer.exe` to a file sharing service
2. Create a download page with instructions
3. Users just need to double-click the .exe file

### For macOS Users

1. Upload `TaskTimer.app` to a file sharing service
2. Users may need to right-click and "Open" to bypass Gatekeeper

### For Linux Users

1. Upload `TaskTimer` binary
2. Make it executable: `chmod +x TaskTimer`
3. Users run: `./TaskTimer`

---

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `MONGODB_URL` | MongoDB connection string | `mongodb+srv://user:pass@cluster.mongodb.net/db` |
| `SECRET_KEY` | JWT secret key | `abc123xyz...` |
| `CORS_ORIGINS` | Allowed frontend URLs | `*` or `https://example.com` |
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8000` |

---

## Cost Estimate

| Service | Free Tier | Paid Tier |
|---------|-----------|-----------|
| Render Backend | Free (spins down after 15 min) | $7/month (always on) |
| MongoDB Atlas | 512 MB (Free) | $9/month (2 GB) |
| **Total** | **$0/month** | **~$16/month** |

---

## Troubleshooting

### Backend Won't Start

**Problem**: Backend crashes on startup

**Solution**:
1. Check Render logs for errors
2. Verify MongoDB connection string is correct
3. Make sure all environment variables are set

### Desktop App Won't Connect

**Problem**: "Connection refused" error

**Solution**:
1. Verify backend URL is correct
2. Check if backend is running
3. Try accessing `/health` endpoint in browser

### PyInstaller Import Errors

**Problem**: "Module not found" errors

**Solution**:
1. Add missing modules to `--hidden-import`
2. Use `--collect-all` flag for problematic packages
3. Check if all dependencies are in `requirements.txt`

### Live View Not Updating

**Problem**: WebSocket connection fails

**Solution**:
1. Make sure you're using `wss://` for HTTPS
2. Check CORS settings
3. Verify share token is valid

---

## Security Checklist

Before distributing:

- [ ] Changed default `SECRET_KEY`
- [ ] Set up MongoDB Atlas IP whitelist
- [ ] Updated API URL in desktop client
- [ ] Added `.env` to `.gitignore`
- [ ] Tested all features
- [ ] Removed any debug code

---

## File Structure After Deployment

```
TaskTimer/
├── backend/              # Deployed to Render.com
│   ├── main.py
│   ├── config.py
│   ├── requirements.txt
│   ├── .env              # Not committed to git
│   └── ...
├── desktop_client/       # Included in executable
│   ├── api_client.py
│   ├── cloud_dashboard.py
│   └── ...
├── core/                 # Included in executable
│   ├── tracking_engine.py
│   ├── app_monitor.py
│   └── ...
├── ui/                   # Included in executable
│   ├── dashboard.py
│   └── ...
├── main_cloud.py         # Entry point for executable
├── dist/                 # Generated by PyInstaller
│   └── TaskTimer.exe     # Distribute this
└── DEPLOYMENT.md         # This file
```

---

## Next Steps

1. **Monitor Backend**: Use Render dashboard to monitor API health
2. **Collect Feedback**: Get feedback from beta users
3. **Add Features**: Consider adding more features based on user needs
4. **Scale Up**: If you have many users, upgrade to paid tiers

---

## Need Help?

- Render Documentation: https://render.com/docs
- MongoDB Atlas Docs: https://docs.atlas.mongodb.com
- PyInstaller Docs: https://pyinstaller.org
- FastAPI Docs: https://fastapi.tiangolo.com

---

**Good luck with your deployment! 🚀**
