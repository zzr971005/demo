@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM Start Frontend Only
REM ============================================================

title Frontend Service - Port 5173

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"
set "FRONTEND_PATH=%PROJECT_ROOT%\frontend"
set "FRONTEND_PORT=5173"

echo.
echo ========================================
echo  Start Frontend Only
echo ========================================
echo.
echo Project Root: %PROJECT_ROOT%
echo Frontend Path: %FRONTEND_PATH%
echo Port: %FRONTEND_PORT%
echo.

echo [1/3] Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not installed
    pause
    exit /b 1
)
echo [OK] Node.js installed
echo.

echo [2/3] Checking frontend dependencies...
if not exist "%FRONTEND_PATH%\node_modules" (
    echo [INFO] node_modules not found, installing...
    cd /d "%FRONTEND_PATH%"
    npm install
    if errorlevel 1 (
        echo [ERROR] Installation failed
        pause
        exit /b 1
    )
)
echo [OK] Dependencies installed
echo.

echo [3/3] Checking port %FRONTEND_PORT%...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr "0.0.0.0:%FRONTEND_PORT%" ^| findstr "LISTENING"') do (
    echo [INFO] Port %FRONTEND_PORT% occupied (0.0.0.0), killing PID: %%p...
    taskkill /F /PID %%p >nul 2>&1
    timeout /t 1 /nobreak >nul
)
for /f "tokens=5" %%p in ('netstat -ano ^| findstr "127.0.0.1:%FRONTEND_PORT%" ^| findstr "LISTENING"') do (
    echo [INFO] Port %FRONTEND_PORT% occupied (127.0.0.1), killing PID: %%p...
    taskkill /F /PID %%p >nul 2>&1
    timeout /t 1 /nobreak >nul
)
for /f "tokens=5" %%p in ('netstat -ano ^| findstr "[::]:%FRONTEND_PORT%" ^| findstr "LISTENING"') do (
    echo [INFO] Port %FRONTEND_PORT% occupied (IPv6), killing PID: %%p...
    taskkill /F /PID %%p >nul 2>&1
    timeout /t 1 /nobreak >nul
)
echo [OK] Port ready
echo.

echo ========================================
echo  Starting Frontend Service
echo ========================================
echo.
echo Access:
echo   - Frontend: http://localhost:%FRONTEND_PORT%
echo.
echo Tips:
echo   - Hot Module Replacement (HMR) enabled
echo   - UI changes auto-refresh
echo   - Ctrl+C to stop service
echo   - Press any key to start...
pause >nul

echo.
echo [INFO] Starting frontend service...
echo.

cd /d "%FRONTEND_PATH%"
npm run dev

echo.
echo [INFO] Frontend service stopped
echo.
pause
