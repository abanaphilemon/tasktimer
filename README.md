# TaskTimer - Intelligent Time Tracking Desktop Application

A cross-platform desktop application that tracks time spent on user-defined tasks with intelligent auto-pause functionality. Time is only counted when you're actively working on approved applications.

## Features

- **Task Management**: Create, edit, and delete tasks with custom descriptions
- **Application Filtering**: Define which applications count toward each task
- **Intelligent Tracking**: Automatically pauses when:
  - User is idle (no keyboard/mouse activity)
  - User switches to a non-approved application
- **Real-time Monitoring**: See current status, timer, and active application
- **Detailed Statistics**: View total time per task and app usage breakdown
- **Privacy-Focused**: Only detects activity presence, never logs keystrokes

## System Requirements

- Python 3.8 or higher
- Operating System: Windows, macOS, or Linux

## Installation

### 1. Clone or Download the Project

```bash
cd TaskTimer
```

### 2. Create Virtual Environment (Recommended)

```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### Platform-Specific Dependencies

**Windows:**
```bash
pip install pywin32
```

**Linux:**
```bash
# Install xdotool and wmctrl
sudo apt-get install xdotool wmctrl  # Debian/Ubuntu
sudo dnf install xdotool wmctrl      # Fedora
```

**macOS:**
No additional dependencies required (uses built-in osascript).

## Usage

### Running the Application

```bash
python main.py
```

### Creating a Task

1. Click the "+ New Task" button
2. Enter a task name and optional description
3. Select allowed applications from the list of running processes
4. Click "OK" to create the task

### Starting Tracking

1. Select a task from the task list
2. Click "Start Tracking"
3. The timer will only run when:
   - The selected task is active
   - The current application is in the allowed list
   - You are not idle (no activity for 60+ seconds)

### Stopping Tracking

Click "Stop Tracking" to end the current session and save the time log.

### Viewing Statistics

Select a task to view:
- Total time tracked
- App usage breakdown
- Recent time logs

## Project Structure

```
TaskTimer/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── core/                  # Core tracking logic
│   ├── __init__.py
│   ├── tracking_engine.py # Main tracking engine
│   ├── idle_detector.py   # Keyboard/mouse activity detection
│   └── app_monitor.py     # Active window and process monitoring
├── database/              # Data persistence
│   ├── __init__.py
│   ├── models.py          # Data models
│   └── handler.py         # SQLite database operations
├── ui/                    # User interface
│   ├── __init__.py
│   ├── dashboard.py       # Main dashboard window
│   └── task_dialog.py     # Task creation/editing dialog
└── utils/                 # Utility functions
    ├── __init__.py
    └── time_formatter.py  # Time formatting helpers
```

## Tracking Logic

The application follows this strict tracking logic:

```
IF task_active == TRUE
AND current_app IN allowed_apps
AND user_status == ACTIVE
THEN
    → increment timer
ELSE
    → pause timer
```

### Status States

- **ACTIVE**: Timer is running (all conditions met)
- **IDLE**: User has been inactive for 60+ seconds
- **PAUSED**: User is active but using a non-approved application
- **STOPPED**: No tracking session is active

## Database

The application uses SQLite for local data storage. Database location:

- **Windows**: `C:\Users\<username>\.tasktimer\tasktimer.db`
- **macOS**: `/Users/<username>/.tasktimer/tasktimer.db`
- **Linux**: `/home/<username>/.tasktimer/tasktimer.db`

### Database Schema

**Tasks**
- id, name, description, created_at

**AllowedApps**
- id, task_id, app_name

**TimeLogs**
- id, task_id, start_time, end_time, duration, status

**AppUsageLogs**
- id, task_id, app_name, timestamp, duration

## Configuration

### Idle Threshold

The default idle threshold is 60 seconds. This can be modified in the code by adjusting the `idle_threshold` parameter in `tracking_engine.py`.

### Platform-Specific Notes

**Windows:**
- Requires pywin32 for window detection
- May require administrator privileges for some applications

**Linux:**
- Requires xdotool and wmctrl for window detection
- Works best with X11-based desktop environments
- Wayland support is limited

**macOS:**
- Uses AppleScript for window detection
- Requires accessibility permissions (will prompt on first run)

## Troubleshooting

### Application won't start

- Ensure all dependencies are installed
- Check Python version (3.8+ required)
- Verify platform-specific dependencies are installed

### Window detection not working

- **Linux**: Install xdotool and wmctrl
- **macOS**: Grant accessibility permissions in System Preferences
- **Windows**: Run as administrator if needed

### Keyboard/mouse detection not working

- Ensure pynput is installed correctly
- On Linux, you may need to add your user to the `input` group:
  ```bash
  sudo usermod -a -G input $USER
  ```

### Database errors

- Check that the `.tasktimer` directory exists and is writable
- Delete the database file to reset (warning: loses all data)

## Privacy

TaskTimer is designed with privacy in mind:

- **No keystroke logging**: Only detects activity presence
- **No screen capture**: Never captures or records screen content
- **Local storage only**: All data is stored locally on your device
- **No network communication**: Does not send data to any external service

## License

This project is provided as-is for educational and personal use.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Support

For issues or questions, please check the troubleshooting section or create an issue in the project repository.
