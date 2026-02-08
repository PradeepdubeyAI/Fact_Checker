@echo off
echo ========================================
echo ClaimAI Desktop - Quick Start
echo ========================================
echo.

cd /d "%~dp0"

echo [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11+ from https://python.org/
    pause
    exit /b 1
)

echo [2/4] Setting up Python backend...
cd python-backend
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing Python dependencies...
pip install -r requirements.txt

echo.
echo [3/4] Setting up Electron app...
cd ..\electron

if not exist node_modules (
    echo Installing Node dependencies...
    call npm install
)

echo.
echo [4/4] Starting ClaimAI Desktop...
echo.
echo ========================================
echo Application is starting...
echo ========================================
echo.
echo - Python backend will start on port 8765
echo - Electron window will open automatically
echo - Press Ctrl+C to stop the application
echo.

start /B cmd /c "cd ..\python-backend && venv\Scripts\python.exe server.py"
timeout /t 3 /nobreak >nul

call npm start

echo.
echo Application closed.
pause
