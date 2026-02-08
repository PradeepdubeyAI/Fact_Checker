@echo off
REM Quick start script for Electron app
echo ================================
echo ClaimAI Desktop - Electron App
echo ================================
echo.

cd /d "%~dp0electron"

REM Check if node_modules exists
if not exist node_modules (
    echo Installing dependencies...
    call npm install
)

REM Start Electron
echo Starting Electron app...
call npm start

pause
