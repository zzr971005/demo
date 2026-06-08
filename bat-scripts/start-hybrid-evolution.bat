@echo off
setlocal

title Hybrid Evolution Mode - Universal + Symbol-Specific

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"
set "BACKEND_PATH=%PROJECT_ROOT%\backend"

cls
echo.
echo ========================================
echo  Hybrid Evolution Mode
echo ========================================
echo.
echo This mode starts hybrid evolution combining:
echo - Universal factors (cross-symbol)
echo - Symbol-specific factors (single symbol)
echo.

REM Check Python environment
for /f "delims=" %%i in ('cd /d "%BACKEND_PATH%" ^&^& poetry env info --path 2^>nul') do set "VENV_PATH=%%i"
if not defined VENV_PATH (
    echo [ERROR] Poetry virtual environment not found
    pause
    exit /b 1
)
set "PYTHON=%VENV_PATH%\Scripts\python.exe"
echo [OK] Python environment ready

REM Check if backend is running
curl -s http://localhost:8000/health >nul 2>&1
if errorlevel 1 (
    echo [INFO] Backend is not running. Please start backend first.
    echo [INFO] Run: start-backend-only.bat
    pause
    exit /b 1
)
echo [OK] Backend is running

REM Set hybrid evolution environment variables
set ENABLE_EVOLUTION_POOL=1
set ENABLE_SCHEDULER=0
set EVOLUTION_MODE=hybrid

REM Start hybrid evolution
echo.
echo [INFO] Starting hybrid evolution mode...
echo [INFO] Evolution mode: hybrid (universal + symbol-specific)
echo.

cd /d "%BACKEND_PATH%"
"%PYTHON%" scripts/run_continuous_evolution.py

pause
