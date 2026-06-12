@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM Start Backend Only
REM ============================================================

title Backend Service - Port 8000

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"
set "BACKEND_PATH=%PROJECT_ROOT%\backend"
set "BACKEND_PORT=8000"

for /f "delims=" %%i in ('cd /d "%BACKEND_PATH%" ^& poetry env info --path 2^>nul') do set "VENV_PATH=%%i"
if not defined VENV_PATH set "VENV_PATH=%BACKEND_PATH%\.venv"
set "PYTHON=%VENV_PATH%\Scripts\python.exe"

echo.
echo ========================================
echo  Start Backend Only
echo ========================================
echo.
echo Project root: %PROJECT_ROOT%
echo Backend path: %BACKEND_PATH%
echo Port: %BACKEND_PORT%
echo.

echo [1/4] Checking Python virtual environment...
if not exist "%PYTHON%" (
    echo [ERROR] Python virtual environment not found
    echo [INFO] Please run: cd backend ^&^& poetry install
    pause
    exit /b 1
)
echo [OK] Python environment ready
echo.

echo [2/4] Checking PostgreSQL service...
sc query postgresql-x64-17 >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PostgreSQL 17 service not found
    echo [INFO] Please install PostgreSQL 17 with TimescaleDB first
    pause
    exit /b 1
)

sc query postgresql-x64-17 | findstr "RUNNING" >nul
if errorlevel 1 (
    echo [INFO] PostgreSQL not running, starting...
    net start postgresql-x64-17 >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Failed to start PostgreSQL
        pause
        exit /b 1
    )
    echo [OK] PostgreSQL started
) else (
    echo [OK] PostgreSQL already running
)
echo.

echo [3/4] Checking Redis...
netstat -ano | findstr "0.0.0.0:6379" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo [INFO] Redis not running, starting...
    sc query redis >nul 2>&1
    if errorlevel 1 (
        if exist "C:\Program Files\Redis\redis-server.exe" (
            start "" "C:\Program Files\Redis\redis-server.exe"
            echo [OK] Redis started manually
        ) else (
            echo [WARN] Redis not found, continuing anyway...
        )
    ) else (
        net start redis >nul 2>&1
        if errorlevel 1 (
            echo [WARN] Redis service start failed, continuing anyway...
        ) else (
            echo [OK] Redis started
        )
    )
) else (
    echo [OK] Redis already running
)
echo.

echo [4/4] Checking port %BACKEND_PORT%...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr "0.0.0.0:%BACKEND_PORT%" ^| findstr "LISTENING"') do (
    echo [INFO] Port %BACKEND_PORT% occupied (0.0.0.0), stopping PID: %%p...
    taskkill /F /PID %%p >nul 2>&1
    timeout /t 1 /nobreak >nul
)
for /f "tokens=5" %%p in ('netstat -ano ^| findstr "127.0.0.1:%BACKEND_PORT%" ^| findstr "LISTENING"') do (
    echo [INFO] Port %BACKEND_PORT% occupied (127.0.0.1), stopping PID: %%p...
    taskkill /F /PID %%p >nul 2>&1
    timeout /t 1 /nobreak >nul
)
for /f "tokens=5" %%p in ('netstat -ano ^| findstr "[::]:%BACKEND_PORT%" ^| findstr "LISTENING"') do (
    echo [INFO] Port %BACKEND_PORT% occupied (IPv6), stopping PID: %%p...
    taskkill /F /PID %%p >nul 2>&1
    timeout /t 1 /nobreak >nul
)
echo [OK] Port ready
echo.

echo ========================================
echo  Starting Backend Service
echo ========================================
echo.
echo Access URLs:
echo   - API: http://localhost:%BACKEND_PORT%
echo   - Docs: http://localhost:%BACKEND_PORT%/docs
echo   - Health: http://localhost:%BACKEND_PORT%/health
echo.
echo Tips:
echo   - Auto-reload on code changes
echo   - Press Ctrl+C to stop
echo   - Press any key to start...
pause >nul

echo.
echo [INFO] Starting backend service...
echo.

cd /d "%BACKEND_PATH%"
set PYTHONPATH=%BACKEND_PATH%
set DISABLE_EVOLUTION_POOL=1
"%PYTHON%" -m uvicorn app.main:app --host 0.0.0.0 --port %BACKEND_PORT% --reload --log-level info

echo.
echo [INFO] Backend service stopped
echo.
pause