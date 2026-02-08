@echo off
REM Quick start script for ClaimAI Desktop
echo ================================
echo ClaimAI Desktop - Starting...
echo ================================
echo.

cd /d "%~dp0python-backend"

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Start Python backend
echo Starting Python backend server...
python server.py

pause
