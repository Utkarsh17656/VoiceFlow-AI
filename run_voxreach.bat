@echo off
TITLE VoxReach AI - Startup Script
COLOR 0A

echo ==========================================
echo       INITIALIZING VOXREACH AI
echo ==========================================

:: Step 1: Check for .env file
if not exist ".env" (
    echo [WARNING] .env file not found in directory!
    echo Please create it and add your OPENROUTER_API_KEY.
    echo Copying .env.example to .env as a template...
    copy .env.example .env
    echo [ACTION] Please edit .env with your API key and restart this script.
    pause
    exit /b
)

:: Step 2: Install dependencies
echo [1/2] Installing/Updating dependencies...
pip install -r voxreach_ai\requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install dependencies. Make sure Python and Pip are installed.
    pause
    exit /b
)

:: Step 3: Run the application
echo [2/2] Starting FastAPI Server...
echo API Documentation will be available at: http://localhost:8000/docs
echo.
python -m uvicorn voxreach_ai.main:app --host 127.0.0.1 --port 8000 --reload

pause
