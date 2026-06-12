@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM Stop All Services Script (Local Services)
REM ============================================================

title Stop All Services

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"
set "BACKEND_PATH=%PROJECT_ROOT%\backend"

echo.
echo ========================================
echo  Stop All Services
echo ========================================
echo.

echo [INFO] Checking current service status...
call "%SCRIPT_DIR%\check-service.bat" all
echo.

echo [1/5] Stopping PostgreSQL service...
sc query postgresql-x64-17 >nul 2>&1
if errorlevel 1 (
    echo [INFO] PostgreSQL not installed as service
) else (
    net stop postgresql-x64-17 >nul 2>&1
    if errorlevel 1 (
        echo [WARN] Could not stop PostgreSQL (may need admin rights)
    ) else (
        echo [OK] PostgreSQL service stopped
    )
)
echo.

echo [2/5] Stopping Redis service...
sc query redis >nul 2>&1
if errorlevel 1 (
    echo [INFO] Redis not installed as service
    for /f "tokens=5" %%p in ('netstat -ano ^| findstr "0.0.0.0:6379" ^| findstr "LISTENING"') do (
        echo [INFO] Found Redis process PID: %%p
        taskkill /F /PID %%p >nul 2>&1
        if !errorlevel! equ 0 (
            echo [OK] Stopped Redis PID %%p
        )
    )
) else (
    net stop redis >nul 2>&1
    if errorlevel 1 (
        echo [WARN] Could not stop Redis (may need admin rights)
    ) else (
        echo [OK] Redis service stopped
    )
)
echo.

echo [3/5] Stopping backend service (port 8000)...
set "BACKEND_STOPPED=0"

for /f "tokens=5" %%p in ('netstat -ano ^| findstr "0.0.0.0:8000" ^| findstr "LISTENING"') do (
    echo [INFO] Found backend process PID: %%p
    taskkill /F /PID %%p >nul 2>&1
    if !errorlevel! equ 0 (
        echo [OK] Stopped PID %%p
        set "BACKEND_STOPPED=1"
    )
)

for /f "tokens=5" %%p in ('netstat -ano ^| findstr "127.0.0.1:8000" ^| findstr "LISTENING"') do (
    echo [INFO] Found backend process PID: %%p
    taskkill /F /PID %%p >nul 2>&1
    if !errorlevel! equ 0 (
        echo [OK] Stopped PID %%p
        set "BACKEND_STOPPED=1"
    )
)

for /f "tokens=2" %%p in ('tasklist /FI "IMAGENAME eq python.exe" /FO CSV 2^>nul ^| findstr /I "uvicorn"') do (
    set "PID=%%p"
    set "PID=!PID:"=!"
    if not "!PID!"=="" (
        echo [INFO] Found uvicorn process PID: !PID!
        taskkill /F /PID !PID! >nul 2>&1
        if !errorlevel! equ 0 (
            echo [OK] Stopped PID !PID!
            set "BACKEND_STOPPED=1"
        )
    )
)

if !BACKEND_STOPPED! equ 0 (
    echo [INFO] No running backend service found
)
echo.

echo [4/5] Stopping frontend service (port 5173)...
set "FRONTEND_STOPPED=0"

for /f "tokens=5" %%p in ('netstat -ano ^| findstr "0.0.0.0:5173" ^| findstr "LISTENING"') do (
    echo [INFO] Found frontend process PID: %%p
    taskkill /F /PID %%p >nul 2>&1
    if !errorlevel! equ 0 (
        echo [OK] Stopped PID %%p
        set "FRONTEND_STOPPED=1"
    )
)

for /f "tokens=5" %%p in ('netstat -ano ^| findstr "127.0.0.1:5173" ^| findstr "LISTENING"') do (
    echo [INFO] Found frontend process PID: %%p
    taskkill /F /PID %%p >nul 2>&1
    if !errorlevel! equ 0 (
        echo [OK] Stopped PID %%p
        set "FRONTEND_STOPPED=1"
    )
)

for /f "tokens=2" %%p in ('tasklist /FI "IMAGENAME eq node.exe" /FO CSV 2^>nul') do (
    set "PID=%%p"
    set "PID=!PID:"=!"
    if not "!PID!"=="" (
        echo [INFO] Found node process PID: !PID!
        taskkill /F /PID !PID! >nul 2>&1
        if !errorlevel! equ 0 (
            echo [OK] Stopped PID !PID!
            set "FRONTEND_STOPPED=1"
        )
    )
)

if !FRONTEND_STOPPED! equ 0 (
    echo [INFO] No running frontend service found
)
echo.

echo [5/5] Summary:
echo   - PostgreSQL: Stopped
echo   - Redis: Stopped
echo   - Backend (8000): Stopped
echo   - Frontend (5173): Stopped
echo.
echo [SUCCESS] All services stopped
echo.
pause