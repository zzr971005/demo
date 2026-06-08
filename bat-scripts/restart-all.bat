@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM Restart All Services (Local Services)
REM ============================================================

title Restart All Services

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"

echo.
echo ========================================
echo  Restart All Services
echo ========================================
echo.

echo [1/3] Stopping all services...
call "%SCRIPT_DIR%\stop-all.bat"
echo.

echo [2/3] Cleaning ports...
call "%SCRIPT_DIR%\clean-ports.bat"
echo.

echo [3/3] Select restart mode:
echo.
echo   [1] Development Mode (Recommended)
echo       - Start PostgreSQL + Redis
echo       - Backend (auto-reload)
echo       - Frontend (HMR)
echo.
echo   [2] Infrastructure Only (for debugging)
echo       - PostgreSQL + Redis only
echo.
echo   [0] Exit
echo.
set /p choice="Enter option [0-2]: "

if "%choice%"=="0" goto :end
if "%choice%"=="1" goto :dev_mode
if "%choice%"=="2" goto :infra_mode

echo [ERROR] Invalid option
pause
exit /b 1

:dev_mode
echo.
echo [INFO] Starting development mode...
call "%SCRIPT_DIR%\start-dev.bat"
goto :end

:infra_mode
echo.
echo [INFO] Starting infrastructure only mode...
echo.
echo [Check] PostgreSQL service...
net start postgresql-x64-17 >nul 2>&1
if errorlevel 1 (
    sc query postgresql-x64-17 >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] PostgreSQL 17 not installed
    ) else (
        echo [OK] PostgreSQL service started
    )
) else (
    echo [OK] PostgreSQL already running
)

echo [Check] Redis service...
net start redis >nul 2>&1
if errorlevel 1 (
    if exist "C:\Program Files\Redis\redis-server.exe" (
        start "" "C:\Program Files\Redis\redis-server.exe"
        echo [OK] Redis started manually
    ) else (
        echo [WARN] Redis not installed
    )
) else (
    echo [OK] Redis already running
)

echo.
echo ========================================
echo [SUCCESS] Infrastructure started
echo ========================================
echo.
echo Access addresses:
echo   - PostgreSQL: localhost:5432
echo   - Redis: localhost:6379
echo.
echo To start backend: start-backend-only.bat
echo To start frontend: start-frontend-only.bat
echo.
pause
goto :end

:end
echo.
echo [INFO] Restart complete
echo.