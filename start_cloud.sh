#!/bin/bash
# TaskTimer Cloud Desktop Client Startup Script

echo "🚀 Starting TaskTimer Cloud Desktop Client..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r desktop_client/requirements.txt

# Check for Linux dependencies
if [ "$(uname)" = "Linux" ]; then
    echo "🔍 Checking for Linux dependencies..."
    if ! command -v xdotool &> /dev/null; then
        echo "⚠️  xdotool not found. Install with: sudo apt-get install xdotool"
    fi
    if ! command -v wmctrl &> /dev/null; then
        echo "⚠️  wmctrl not found. Install with: sudo apt-get install wmctrl"
    fi
fi

# Start the application
echo "✅ Starting TaskTimer Cloud..."
python main_cloud.py
