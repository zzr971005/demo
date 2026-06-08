@echo off
setlocal enabledelayedexpansion
title Smart Start (Simple)

echo.
echo ===============================
echo  Smart Start (Simple Mode)
echo ===============================
echo.

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"
set "BACKEND_PATH=%PROJECT_ROOT%\backend"
set "FRONTEND_PATH=%PROJECT_ROOT%\frontend"
set "BACKEND_PORT=8000"
set "FRONTEND_PORT=3000"

for /f "delims=" %%i in ('cd /d "%BACKEND_PATH%" ^& poetry env info --path 2^>nul') do set "VENV_PATH=%%i"
if not defined VENV_PATH set "VENV_PATH=%BACKEND_PATH%\.venv"
set "PYTHON=%VENV_PATH%\Scripts\python.exe"

echo [Check] Services...
echo.

REM Check PostgreSQL
sc query postgresql-x64-17 >nul 2>&1
if errorlevel 1 (
    echo [WARN] PostgreSQL 17 service not found
) else (
    sc query postgresql-x64-17 | findstr "RUNNING" >nul
    if errorlevel 1 (
        echo [INFO] Starting PostgreSQL...
        net start postgresql-x64-17 >nul 2>&1
        if !errorlevel! equ 0 (
            echo [OK] PostgreSQL started
        ) else (
            echo [OK] PostgreSQL already running
        )
    ) else (
        echo [OK] PostgreSQL already running
    )
)

REM Check Redis
netstat -ano | findstr "0.0.0.0:6379" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo [INFO] Starting Redis...
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
        if !errorlevel! equ 0 (
            echo [OK] Redis started
        ) else (
            echo [OK] Redis already running
        )
    )
) else (
    echo [OK] Redis already running
)

REM Check Backend
netstat -ano | findstr "0.0.0.0:%BACKEND_PORT%" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo [INFO] Starting backend...
    start "Backend" cmd /k cd /d "%BACKEND_PATH%" ^&^& set PYTHONPATH=%BACKEND_PATH% ^&^& "%PYTHON%" -m uvicorn app.main:app --host 0.0.0.0 --port %BACKEND_PORT% --reload
    timeout /t 3 /nobreak >nul
) else (
    echo [OK] Backend already running
)

REM Check Frontend
netstat -ano | findstr "0.0.0.0:%FRONTEND_PORT%" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo [INFO] Starting frontend...
    start "Frontend" cmd /k cd /d "%FRONTEND_PATH%" ^&^& npm run dev
) else (
    echo [OK] Frontend already running
)

echo.
echo ===============================
echo  Startup Complete!
echo ===============================
echo.
echo  Access URLs:
echo    Frontend:  http://localhost:%FRONTEND_PORT%
echo    Backend:   http://localhost:%BACKEND_PORT%
echo    API Docs:  http://localhost:%BACKEND_PORT%/docs
echo.
pause