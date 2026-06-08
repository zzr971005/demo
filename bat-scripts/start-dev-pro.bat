@echo off
setlocal

title Enhanced Development Mode - GPU Support

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"
set "BACKEND_PATH=%PROJECT_ROOT%\backend"
set "FRONTEND_PATH=%PROJECT_ROOT%\frontend"
set "BACKEND_PORT=8000"
set "FRONTEND_PORT=5173"

cls
echo.
echo ========================================
echo  Enhanced Development Mode - GPU Support
echo ========================================
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

REM GPU Detection
echo.
echo ========================================
echo  GPU Detection
echo ========================================
echo.

nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo [GPU] No NVIDIA GPU detected
    echo [GPU] Evolution will run in CPU mode
) else (
    echo [GPU] NVIDIA GPU detected
    for /f "delims=" %%i in ('nvidia-smi --query-gpu=name --format=csv,noheader 2^>nul') do (
        echo [GPU] Name: %%i
    )
    for /f "delims=" %%i in ('nvidia-smi --query-gpu=driver_version --format=csv,noheader 2^>nul') do (
        echo [GPU] Driver: %%i
    )
)

REM Check PyTorch
echo.
echo ========================================
echo  PyTorch Status
echo ========================================
echo.

cd /d "%BACKEND_PATH%"
"%PYTHON%" -c "import torch; print('PyTorch:', torch.__version__); print('CUDA Available:', torch.cuda.is_available()); print('CUDA Version:', torch.version.cuda if torch.cuda.is_available() else 'N/A')" 2>nul
if errorlevel 1 (
    echo [PyTorch] Not installed
    echo.
    echo [HINT] Install PyTorch:
    echo   - For RTX 5070 Ti: Use option [12] in Launch Center
    echo   - Or run: poetry run pip install torch torchvision
) else (
    echo.
    echo [PyTorch] Check completed
)

REM Check Node.js
echo.
echo ========================================
echo  Frontend Environment
echo ========================================
echo.

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

REM Service Status
echo.
echo ========================================
echo  Service Status
echo ========================================
echo.

sc query postgresql-x64-17 >nul 2>&1
if errorlevel 1 (
    echo [PostgreSQL] Not installed
) else (
    sc query postgresql-x64-17 | findstr "RUNNING" >nul
    if errorlevel 1 (
        echo [PostgreSQL] Stopped
    ) else (
        echo [PostgreSQL] Running
    )
)

netstat -ano | findstr "0.0.0.0:6379" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo [Redis] Stopped
) else (
    echo [Redis] Running
)

netstat -ano | findstr "0.0.0.0:%BACKEND_PORT%" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo [Backend] Stopped
) else (
    echo [Backend] Running
)

netstat -ano | findstr "0.0.0.0:%FRONTEND_PORT%" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo [Frontend] Stopped
) else (
    echo [Frontend] Running
)

REM Menu
echo.
echo ========================================
echo  Options
echo ========================================
echo.
echo   [1] Start all services (Separated: API + Evolution + Frontend)
echo   [2] Start infrastructure only
echo   [3] Start backend only
echo   [4] Start frontend only
echo   [5] Smart start (missing only)
echo   [6] Install PyTorch Nightly (CUDA 12.8)
echo   [7] Check PyTorch GPU status
echo   [0] Exit
echo.

set /p choice="Select option [0-7]: "

if "%choice%"=="0" goto :exit
if "%choice%"=="1" goto :start_all
if "%choice%"=="2" goto :start_infra
if "%choice%"=="3" goto :start_backend
if "%choice%"=="4" goto :start_frontend
if "%choice%"=="5" goto :start_smart
if "%choice%"=="6" goto :install_pytorch
if "%choice%"=="7" goto :check_pytorch

echo Invalid option
timeout /t 2 /nobreak >nul
goto :menu_restart

:menu_restart
echo.
echo Press any key to return to menu...
pause >nul
goto :menu

:start_all
echo.
echo [INFO] Starting all services (Separated Mode)...
net start postgresql-x64-17 >nul 2>&1
net start redis >nul 2>&1
timeout /t 2 /nobreak >nul

REM Start backend API (evolution pool disabled - runs in separate window)
for /f "tokens=5" %%p in ('netstat -ano ^| findstr "0.0.0.0:%BACKEND_PORT%" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%p >nul 2>&1
)
timeout /t 1 /nobreak >nul
start "Backend API - Port %BACKEND_PORT%" cmd /k cd /d "%BACKEND_PATH%" ^&^& set PYTHONPATH=%BACKEND_PATH% ^&^& set DISABLE_EVOLUTION_POOL=1 ^&^& "%PYTHON%" -m uvicorn app.main:app --host 0.0.0.0 --port %BACKEND_PORT% --reload --log-level info
echo [OK] Backend API started (evolution pool DISABLED)

REM Evolution Engine is NOT auto-started - use frontend to control evolution tasks
echo [INFO] Evolution Engine is NOT auto-started
echo [INFO] Use the frontend Evolution Center to start/stop evolution tasks

REM Start frontend
for /f "tokens=5" %%p in ('netstat -ano ^| findstr "0.0.0.0:%FRONTEND_PORT%" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%p >nul 2>&1
)
timeout /t 1 /nobreak >nul
start "Frontend - Port %FRONTEND_PORT%" cmd /k cd /d "%FRONTEND_PATH%" ^&^& npm run dev
echo [OK] Frontend started

echo.
echo [INFO] Services started in SEPARATED mode!
echo   Backend API:    http://localhost:%BACKEND_PORT%
echo   Frontend:       http://localhost:%FRONTEND_PORT%
echo   Evolution:      Use frontend to control (Evolution Center)
pause
goto :menu

:start_infra
echo.
echo [INFO] Starting infrastructure...
net start postgresql-x64-17 >nul 2>&1
echo [OK] PostgreSQL started
net start redis >nul 2>&1
echo [OK] Redis started
pause
goto :menu

:start_backend
echo.
echo [INFO] Starting backend...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr "0.0.0.0:%BACKEND_PORT%" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%p >nul 2>&1
)
timeout /t 1 /nobreak >nul
start "Backend - Port %BACKEND_PORT%" cmd /k cd /d "%BACKEND_PATH%" ^&^& set PYTHONPATH=%BACKEND_PATH% ^&^& "%PYTHON%" -m uvicorn app.main:app --host 0.0.0.0 --port %BACKEND_PORT% --reload --log-level info
echo [OK] Backend started
pause
goto :menu

:start_frontend
echo.
echo [INFO] Starting frontend...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr "0.0.0.0:%FRONTEND_PORT%" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%p >nul 2>&1
)
timeout /t 1 /nobreak >nul
start "Frontend - Port %FRONTEND_PORT%" cmd /k cd /d "%FRONTEND_PATH%" ^&^& npm run dev
echo [OK] Frontend started
pause
goto :menu

:start_smart
echo.
echo [INFO] Smart starting (missing services only, separated mode)...

sc query postgresql-x64-17 | findstr "RUNNING" >nul
if errorlevel 1 (
    net start postgresql-x64-17 >nul 2>&1
    echo [OK] PostgreSQL started
) else (
    echo [SKIP] PostgreSQL already running
)

netstat -ano | findstr "0.0.0.0:6379" | findstr "LISTENING" >nul
if errorlevel 1 (
    net start redis >nul 2>&1
    echo [OK] Redis started
) else (
    echo [SKIP] Redis already running
)

REM Check Backend API (separated mode: no evolution pool)
netstat -ano | findstr "0.0.0.0:%BACKEND_PORT%" | findstr "LISTENING" >nul
if errorlevel 1 (
    for /f "tokens=5" %%p in ('netstat -ano ^| findstr "0.0.0.0:%BACKEND_PORT%" ^| findstr "LISTENING"') do (
        taskkill /F /PID %%p >nul 2>&1
    )
    timeout /t 1 /nobreak >nul
    start "Backend API - Port %BACKEND_PORT%" cmd /k cd /d "%BACKEND_PATH%" ^&^& set PYTHONPATH=%BACKEND_PATH% ^&^& set DISABLE_EVOLUTION_POOL=1 ^&^& "%PYTHON%" -m uvicorn app.main:app --host 0.0.0.0 --port %BACKEND_PORT% --reload --log-level info
    echo [OK] Backend API started (evolution pool DISABLED)
) else (
    echo [SKIP] Backend API already running on port %BACKEND_PORT%
)

REM Evolution Engine is NOT auto-started - use frontend to control evolution tasks
echo [INFO] Evolution Engine is NOT auto-started
echo [INFO] Use the frontend Evolution Center to start/stop evolution tasks

REM Check Frontend (by port)
netstat -ano | findstr "0.0.0.0:%FRONTEND_PORT%" | findstr "LISTENING" >nul
if errorlevel 1 (
    for /f "tokens=5" %%p in ('netstat -ano ^| findstr "0.0.0.0:%FRONTEND_PORT%" ^| findstr "LISTENING"') do (
        taskkill /F /PID %%p >nul 2>&1
    )
    timeout /t 1 /nobreak >nul
    start "Frontend - Port %FRONTEND_PORT%" cmd /k cd /d "%FRONTEND_PATH%" ^&^& npm run dev
    echo [OK] Frontend started
) else (
    echo [SKIP] Frontend already running on port %FRONTEND_PORT%
)

echo.
echo [INFO] Smart start completed
echo   Evolution: Use frontend to control (Evolution Center)
echo.
pause
goto :menu

:install_pytorch
echo.
echo [INFO] Installing PyTorch Nightly (CUDA 12.8)...
echo This is required for RTX 5070 Ti (Blackwell architecture)
echo.
set /p confirm="Continue? [Y/N]: "
if /i not "%confirm%"=="Y" goto :menu

cd /d "%BACKEND_PATH%"
"%PYTHON%" -m pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128
echo.
echo [OK] Installation completed
echo Run option [7] to verify GPU support
pause
goto :menu

:check_pytorch
echo.
echo [INFO] Checking PyTorch GPU status...
echo.
cd /d "%BACKEND_PATH%"
"%PYTHON%" -c "import torch; print('='*50); print('PyTorch:', torch.__version__); print('CUDA Available:', torch.cuda.is_available()); print('CUDA Version:', torch.version.cuda if torch.cuda.is_available() else 'N/A'); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU Mode'); print('='*50)"
echo.
pause
goto :menu

:exit
echo.
echo Thank you for using Enhanced Development Mode!
echo.
endlocal
exit /b 0