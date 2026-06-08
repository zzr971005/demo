@echo off
setlocal

title Development Mode - Port 5173

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"
set "BACKEND_PATH=%PROJECT_ROOT%\backend"
set "FRONTEND_PATH=%PROJECT_ROOT%\frontend"
set "BACKEND_PORT=8000"
set "FRONTEND_PORT=5173"

cls
echo.
echo ========================================
echo  Development Mode
echo ========================================
echo.
echo Project Root: %PROJECT_ROOT%
echo Backend Path: %BACKEND_PATH%
echo Frontend Path: %FRONTEND_PATH%
echo Backend Port: %BACKEND_PORT%
echo Frontend Port: %FRONTEND_PORT%
echo.

REM Check Python environment
for /f "delims=" %%i in ('cd /d "%BACKEND_PATH%" ^&^& poetry env info --path 2^>nul') do set "VENV_PATH=%%i"
if not defined VENV_PATH (
    echo [INFO] Creating Poetry virtual environment...
    cd /d "%BACKEND_PATH%"
    poetry install --no-interaction
    for /f "delims=" %%i in ('cd /d "%BACKEND_PATH%" ^&^& poetry env info --path 2^>nul') do set "VENV_PATH=%%i"
)
set "PYTHON=%VENV_PATH%\Scripts\python.exe"
if not exist "%PYTHON%" (
    echo [ERROR] Python executable not found
    pause
    exit /b 1
)
echo [OK] Python environment ready

REM Check Node.js
echo.
echo [INFO] Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not installed
    pause
    exit /b 1
)
for /f "delims=" %%i in ('node --version') do echo [OK] Node.js: %%i

if not exist "%FRONTEND_PATH%\node_modules" (
    echo [INFO] Installing frontend dependencies...
    cd /d "%FRONTEND_PATH%"
    npm install
)
echo [OK] Frontend ready

REM Start services
echo.
echo ========================================
echo  Starting Services
echo ========================================
echo.

REM Start PostgreSQL
echo [1/4] Starting PostgreSQL...
sc query postgresql-x64-17 >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PostgreSQL not installed
    pause
    exit /b 1
) else (
    net start postgresql-x64-17 >nul 2>&1
    echo [OK] PostgreSQL started
)

REM Start Redis
echo [2/4] Starting Redis...
sc query redis >nul 2>&1
if errorlevel 1 (
    if exist "C:\Program Files\Redis\redis-server.exe" (
        start "" "C:\Program Files\Redis\redis-server.exe"
        echo [OK] Redis started manually
    ) else (
        echo [WARN] Redis not found
    )
) else (
    net start redis >nul 2>&1
    echo [OK] Redis started
)

REM Start Backend
echo [3/4] Starting Backend...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr "0.0.0.0:%BACKEND_PORT%" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%p >nul 2>&1
)
timeout /t 1 /nobreak >nul
start "Backend - Port %BACKEND_PORT%" cmd /k cd /d "%BACKEND_PATH%" ^&^& set PYTHONPATH=%BACKEND_PATH% ^&^& "%PYTHON%" -m uvicorn app.main:app --host 0.0.0.0 --port %BACKEND_PORT% --reload --log-level info
echo [OK] Backend started

REM Wait for backend to be ready
echo [INFO] Waiting for backend to be ready...
set "BACKEND_READY=0"
set "MAX_WAIT=30"
set "WAIT_COUNT=0"

:wait_loop
if %WAIT_COUNT% geq %MAX_WAIT% (
    echo [WARN] Backend did not become ready within %MAX_WAIT% seconds
    goto :start_frontend_anyway
)

curl -s http://localhost:%BACKEND_PORT%/health >nul 2>&1
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    set /a WAIT_COUNT+=1
    goto :wait_loop
) else (
    echo [OK] Backend is ready
    set "BACKEND_READY=1"
    goto :start_frontend
)

:start_frontend_anyway
echo [WARN] Starting frontend anyway (backend may not be ready)

:start_frontend
REM Start Frontend
echo [4/5] Starting Frontend...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr "0.0.0.0:%FRONTEND_PORT%" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%p >nul 2>&1
)
timeout /t 1 /nobreak >nul
start "Frontend - Port %FRONTEND_PORT%" cmd /k cd /d "%FRONTEND_PATH%" ^&^& npm run dev
echo [OK] Frontend started

REM Start Evolution Engine
echo [5/5] Starting Evolution Engine...
for /f "tokens=2" %%p in ('tasklist /V /FI "IMAGENAME eq python.exe" 2^>nul ^| findstr /I "run_continuous_evolution"') do (
    echo [WARN] Killing existing Evolution Engine process PID=%%p...
    taskkill /F /PID %%p >nul 2>&1
)
timeout /t 1 /nobreak >nul
start "Evolution Engine" cmd /k cd /d "%BACKEND_PATH%" ^&^& set PYTHONPATH=%BACKEND_PATH% ^&^& "%PYTHON%" scripts\run_continuous_evolution.py
echo [OK] Evolution engine started (separate window)

echo.
echo ========================================
echo  All Services Started
echo ========================================
echo.
echo Access:
echo   - Backend API: http://localhost:%BACKEND_PORT%
echo   - API Docs: http://localhost:%BACKEND_PORT%/docs
echo   - Frontend: http://localhost:%FRONTEND_PORT%
echo.
echo Press any key to exit...
pause >nul

endlocal
exit /b 0
