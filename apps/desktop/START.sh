#!/bin/bash

echo "========================================"
echo "ClaimAI Desktop - Quick Start"
echo "========================================"
echo ""

cd "$(dirname "$0")"

echo "[1/4] Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.11+ from https://python.org/"
    exit 1
fi

echo "[2/4] Setting up Python backend..."
cd python-backend

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo ""
echo "[3/4] Setting up Electron app..."
cd ../electron

if [ ! -d "node_modules" ]; then
    echo "Installing Node dependencies..."
    npm install
fi

echo ""
echo "[4/4] Starting ClaimAI Desktop..."
echo ""
echo "========================================"
echo "Application is starting..."
echo "========================================"
echo ""
echo "- Python backend will start on port 8765"
echo "- Electron window will open automatically"
echo "- Press Ctrl+C to stop the application"
echo ""

# Start Python backend in background
cd ../python-backend
source venv/bin/activate
python server.py &
PYTHON_PID=$!

# Wait a bit for backend to start
sleep 3

# Start Electron app
cd ../electron
npm start

# Clean up - kill Python backend when Electron closes
kill $PYTHON_PID

echo ""
echo "Application closed."
