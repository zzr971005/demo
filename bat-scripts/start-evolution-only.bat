@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM Start Evolution Engine Only (Independent Window)
REM ============================================================

title Evolution Engine - Continuous Factor Mining

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"
set "BACKEND_PATH=%PROJECT_ROOT%\backend"

for /f "delims=" %%i in ('cd /d "%BACKEND_PATH%" ^& poetry env info --path 2^>nul') do set "VENV_PATH=%%i"
if not defined VENV_PATH set "VENV_PATH=%BACKEND_PATH%\.venv"
set "PYTHON=%VENV_PATH%\Scripts\python.exe"

echo.
echo ========================================
echo  Evolution Engine - Continuous Mining
echo ========================================
echo.
echo Project root: %PROJECT_ROOT%
echo Backend path: %BACKEND_PATH%
echo.

echo [1/3] Checking Python virtual environment...
if not exist "%PYTHON%" (
    echo [ERROR] Python virtual environment not found
    echo [INFO] Please run: cd backend ^&^& poetry install
    pause
    exit /b 1
)
echo [OK] Python environment ready
echo.

echo [2/3] Checking PostgreSQL service...
sc query postgresql-x64-17 ^>nul 2^>^&1
if errorlevel 1 (
    echo [WARN] PostgreSQL 17 service not found
) else (
    sc query postgresql-x64-17 | findstr "RUNNING" ^>nul
    if errorlevel 1 (
        echo [INFO] PostgreSQL not running, starting...
        net start postgresql-x64-17 ^>nul 2^>^&1
    ) else (
        echo [OK] PostgreSQL already running
    )
)
echo.

echo [3/3] Checking Redis...
netstat -ano | findstr "0.0.0.0:6379" | findstr "LISTENING" ^>nul
if errorlevel 1 (
    echo [INFO] Redis not running, attempting to start...
    sc query redis ^>nul 2^>^&1
    if errorlevel 1 (
        if exist "C:\Program Files\Redis\redis-server.exe" (
            start "" "C:\Program Files\Redis\redis-server.exe"
            echo [OK] Redis started manually
        ) else (
            echo [WARN] Redis not found, continuing anyway...
        )
    ) else (
        net start redis ^>nul 2^>^&1
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

echo ========================================
echo  Starting Continuous Evolution Engine
echo ========================================
echo.
echo Features:
echo   - Runs in a separate window from the backend API
echo   - Logs are isolated and won't flood the API window
echo   - Results are saved to the shared database
echo   - Supports Ctrl+C for graceful shutdown
echo.
echo Press any key to start...
pause ^>nul

echo.
echo [INFO] Starting evolution engine...
echo.

cd /d "%BACKEND_PATH%"
set PYTHONPATH=%BACKEND_PATH%
"%PYTHON%" scripts\run_continuous_evolution.py

echo.
echo [INFO] Evolution engine stopped
echo.
pause
