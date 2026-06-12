@echo off
setlocal

title Basic Development Mode

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"
set "BACKEND_PATH=%PROJECT_ROOT%\backend"
set "FRONTEND_PATH=%PROJECT_ROOT%\frontend"
set "BACKEND_PORT=8000"
set "FRONTEND_PORT=3000"

REM Kill existing processes on port 8000 before starting
echo [INFO] Checking and cleaning port %BACKEND_PORT%...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr "0.0.0.0:%BACKEND_PORT%" ^| findstr "LISTENING"') do (
    echo [INFO] Killing process on port %BACKEND_PORT% (PID: %%p)
    taskkill /F /PID %%p >nul 2>&1
)
timeout /t 2 /nobreak >nul

for /f "delims=" %%i in ('cd /d "%BACKEND_PATH%" ^& poetry env info --path 2^>nul') do set "VENV_PATH=%%i"
if not defined VENV_PATH (
    set "VENV_PATH=%BACKEND_PATH%\.venv"
)
set "PYTHON=%VENV_PATH%\Scripts\python.exe"

:menu
cls
echo.
echo ========================================
echo  Basic Development Mode
echo ========================================
echo.
echo  Project: %PROJECT_ROOT%
echo  Backend: %BACKEND_PATH%
echo  Frontend: %FRONTEND_PATH%
echo  Backend Port: %BACKEND_PORT%
echo  Frontend Port: %FRONTEND_PORT%
echo.

echo  [Service Status]
call "%SCRIPT_DIR%\check-service.bat" all
echo.

echo  Options:
echo    [1] Start all (Infrastructure + Backend + Frontend)
echo    [2] Start infrastructure only
echo    [3] Start backend only
echo    [4] Start frontend only
echo    [5] Smart start (only missing services)
echo    [0] Exit
echo.

set /p choice="Select option [0-5]: "

if "%choice%"=="0" goto :exit_script
if "%choice%"=="1" goto :start_all
if "%choice%"=="2" goto :start_infra
if "%choice%"=="3" goto :start_backend
if "%choice%"=="4" goto :start_frontend
if "%choice%"=="5" goto :start_smart

echo [ERR] Invalid option
timeout /t 2 /nobreak >nul
goto :menu

:start_all
set "INFRA_NEED_START=1"
set "BACKEND_NEED_START=1"
set "FRONTEND_NEED_START=1"
goto :start_process

:start_infra
set "INFRA_NEED_START=1"
set "BACKEND_NEED_START=0"
set "FRONTEND_NEED_START=0"
goto :start_process

:start_backend
set "INFRA_NEED_START=1"
set "BACKEND_NEED_START=1"
set "FRONTEND_NEED_START=0"
goto :start_process

:start_frontend
set "INFRA_NEED_START=0"
set "BACKEND_NEED_START=0"
set "FRONTEND_NEED_START=1"
goto :start_process

:start_smart
echo.
echo [INFO] Smart start - checking and starting missing services...
echo.

set "INFRA_NEED_START=0"
set "BACKEND_NEED_START=0"
set "FRONTEND_NEED_START=0"

REM Check PostgreSQL
sc query postgresql-x64-17 >nul 2>&1
if errorlevel 1 (
    set "INFRA_NEED_START=1"
) else (
    sc query postgresql-x64-17 | findstr "RUNNING" >nul
    if errorlevel 1 set "INFRA_NEED_START=1"
)

REM Check Redis
netstat -ano | findstr "0.0.0.0:6379" | findstr "LISTENING" >nul
if errorlevel 1 set "INFRA_NEED_START=1"

REM For backend and frontend: always restart if port is occupied
REM (to ensure we have a fresh window with visible logs)
netstat -ano | findstr "0.0.0.0:%BACKEND_PORT%" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo [Smart] Backend not running, will start
    set "BACKEND_NEED_START=1"
) else (
    echo [Smart] Backend port occupied, will restart for fresh logs
    set "BACKEND_NEED_START=1"
)

netstat -ano | findstr "0.0.0.0:%FRONTEND_PORT%" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo [Smart] Frontend not running, will start
    set "FRONTEND_NEED_START=1"
) else (
    echo [Smart] Frontend port occupied, will restart for fresh logs
    set "FRONTEND_NEED_START=1"
)

goto :start_process

:start_process
echo.

if "%INFRA_NEED_START%"=="1" (
    echo [INFO] Starting infrastructure...
    
    sc query postgresql-x64-17 >nul 2>&1
    if errorlevel 1 (
        echo [WARN] PostgreSQL service not found
    ) else (
        net start postgresql-x64-17 >nul 2>&1
        echo [OK] PostgreSQL started or already running
    )
    
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
        echo [OK] Redis started or already running
    )
    
    timeout /t 2 /nobreak >nul
)

if "%BACKEND_NEED_START%"=="1" (
    echo [INFO] Starting backend service...
    
    for /f "tokens=5" %%p in ('netstat -ano ^| findstr "0.0.0.0:%BACKEND_PORT%" ^| findstr "LISTENING"') do (
        taskkill /F /PID %%p >nul 2>&1
    )
    timeout /t 1 /nobreak >nul
    
    start "Backend - Port %BACKEND_PORT%" cmd /k cd /d "%BACKEND_PATH%" ^&^& set PYTHONPATH=%BACKEND_PATH% ^&^& "%PYTHON%" -m uvicorn app.main:app --host 0.0.0.0 --port %BACKEND_PORT% --reload --log-level info
    echo [OK] Backend service started
)

if "%FRONTEND_NEED_START%"=="1" (
    echo [INFO] Starting frontend service...
    
    for /f "tokens=5" %%p in ('netstat -ano ^| findstr "0.0.0.0:%FRONTEND_PORT%" ^| findstr "LISTENING"') do (
        taskkill /F /PID %%p >nul 2>&1
    )
    timeout /t 1 /nobreak >nul
    
    start "Frontend - Port %FRONTEND_PORT%" cmd /k cd /d "%FRONTEND_PATH%" ^&^& npm run dev
    echo [OK] Frontend service started
)

echo.
echo ========================================
echo  Startup Complete!
echo ========================================
echo.
echo  Access URLs:
echo    Frontend:  http://localhost:%FRONTEND_PORT%
echo    Backend:   http://localhost:%BACKEND_PORT%
echo    API Docs:  http://localhost:%BACKEND_PORT%/docs
echo.
pause
goto :menu

:exit_script
echo Bye!
exit /b 0