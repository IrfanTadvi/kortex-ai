@echo off
echo ============================================
echo AI Knowledge Copilot - Startup Script
echo ============================================
echo.
echo IMPORTANT: Make sure you have:
echo 1. Python 3.11+ installed
echo 2. Node.js 18+ installed  
echo 3. Added your OpenAI API key to .env file
echo.
echo ============================================
echo.

:: Check if backend dependencies are installed
if not exist "backend\venv" (
    echo [1/5] Creating Python virtual environment...
    cd backend
    python -m venv venv
    cd ..
)

:: Install backend dependencies
echo [2/5] Installing backend dependencies...
cd backend
call venv\Scripts\activate.bat
pip install -r requirements.txt
cd ..

:: Check if frontend dependencies are installed
if not exist "frontend\node_modules" (
    echo [3/5] Installing frontend dependencies...
    cd frontend
    call npm install
    cd ..
)

:: Create data directories
echo [4/5] Creating data directories...
if not exist "data\uploads" mkdir data\uploads
if not exist "data\vectors" mkdir data\vectors
if not exist "logs" mkdir logs

echo [5/5] Starting services...
echo.
echo ============================================
echo Backend will start on: http://localhost:8000
echo Frontend will start on: http://localhost:3000
echo API Docs: http://localhost:8000/api/docs
echo ============================================
echo.

:: Start backend in new window
start "AI Copilot - Backend" cmd /k "cd backend && venv\Scripts\activate.bat && uvicorn app.main:app --reload --port 8000"

:: Wait a bit for backend to start
timeout /t 5 /nobreak

:: Start frontend in new window
start "AI Copilot - Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo Both services are starting in separate windows...
echo Press any key to close this window.
pause
