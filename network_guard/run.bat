@echo off
setlocal enabledelayedexpansion

echo ======================================================================
echo           Starting Network Defense Lab (Autonomous Gateway)
echo ======================================================================

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo [1/3] Checking dependencies...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 3 is required but was not found in PATH.
    pause
    exit /b 1
)

npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js / npm is required but was not found in PATH.
    pause
    exit /b 1
)

echo [2/3] Starting Backend API Server (FastAPI on http://127.0.0.1:8766)...
start "Network Defense Lab - Backend API" cmd /k "cd /d %SCRIPT_DIR% && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8766 --reload"

echo [3/3] Starting Frontend Dashboard (Vite on http://localhost:5174)...
start "Network Defense Lab - Frontend UI" cmd /k "cd /d %SCRIPT_DIR%frontend && npm run dev"

echo.
echo ======================================================================
echo  Network Defense Lab is starting!
echo  Backend:  http://127.0.0.1:8766
echo  Frontend: http://localhost:5174
echo  API Docs: http://127.0.0.1:8766/docs
echo ======================================================================
echo.
timeout /t 3 >nul
start http://localhost:5174
pause
