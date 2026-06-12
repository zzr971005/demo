@echo off
setlocal

title Launch Center Enhanced - Futures Factor Mining

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:menu
cls
echo.
echo ========================================
echo  Launch Center Enhanced - Futures Factor Mining
echo ========================================
echo.

echo  [Service Status]
sc query postgresql-x64-17 >nul 2>&1
if errorlevel 1 (
    echo    PostgreSQL: Not installed
) else (
    sc query postgresql-x64-17 | findstr "RUNNING" >nul
    if errorlevel 1 (
        echo    PostgreSQL: Stopped
    ) else (
        echo    PostgreSQL: Running
    )
)
sc query redis >nul 2>&1
if errorlevel 1 (
    echo    Redis: Not installed
) else (
    sc query redis | findstr "RUNNING" >nul
    if errorlevel 1 (
        echo    Redis: Stopped
    ) else (
        echo    Redis: Running
    )
)
echo.

echo  [GPU Status]
where nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo    GPU: Not detected
) else (
    for /f "delims=" %%i in ('nvidia-smi --query-gpu=name --format=csv,noheader 2^>nul') do (
        echo    GPU: %%i
        goto :gpu_done
    )
    echo    GPU: Detected
)
:gpu_done
echo.

echo  Main Functions:
echo    [1] Start Development Mode (Basic)
echo    [2] Start Enhanced Dev Mode (with GPU detection)
echo    [3] Start Infrastructure Only
echo    [4] Start Backend Only
echo    [5] Start Frontend Only
echo.
echo  Data Management:
echo    [6] Initialize Data
echo    [7] Check Service Status
echo    [8] Check Database Status
echo.
echo  Data Cleanup:
echo    [9] Clean All Factor Data (NEW!)
echo    [10] Clean Data + Start Dev Mode (NEW!)
echo    [11] Clean Data + Start Enhanced Mode (NEW!)
echo.
echo  Operations:
echo    [12] Restart All Services
echo    [13] Stop All Services
echo    [14] Clean Port Occupation
echo.
echo  GPU Setup:
echo    [15] GPU Acceleration Setup (PyTorch Nightly)
echo    [16] Check PyTorch Status
echo.
echo  Evolution Mode:
echo    [18] Start Joint Evolution (Multi-Symbol)
echo    [19] Start Hybrid Evolution (Universal + Symbol-Specific)
echo    [20] Evolution Mode Comparison Test
echo.
echo  Other:
echo    [21] View README
echo    [0] Exit
echo.

set /p choice="Enter option [0-21]: "

if "%choice%"=="0" goto :exit
if "%choice%"=="1" goto :dev_mode
if "%choice%"=="2" goto :dev_pro_mode
if "%choice%"=="3" goto :infra_mode
if "%choice%"=="4" goto :backend_mode
if "%choice%"=="5" goto :frontend_mode
if "%choice%"=="6" goto :init_data
if "%choice%"=="7" goto :check_status
if "%choice%"=="8" goto :check_db
if "%choice%"=="9" goto :clean_data_only
if "%choice%"=="10" goto :clean_data_then_dev
if "%choice%"=="11" goto :clean_data_then_pro
if "%choice%"=="12" goto :restart_all
if "%choice%"=="13" goto :stop_all
if "%choice%"=="14" goto :clean_ports
if "%choice%"=="15" goto :gpu_setup
if "%choice%"=="16" goto :check_pytorch
if "%choice%"=="18" goto :joint_evolution
if "%choice%"=="19" goto :hybrid_evolution
if "%choice%"=="20" goto :evolution_comparison
if "%choice%"=="21" goto :readme

echo Invalid option
timeout /t 1 /nobreak >nul
goto :menu

:dev_mode
echo.
echo [INFO] Starting Basic Development Mode...
start "Development Mode" "%SCRIPT_DIR%\start-dev.bat"
goto :menu

:dev_pro_mode
echo.
echo [INFO] Starting Enhanced Development Mode (with GPU detection)...
start "Enhanced Dev Mode" "%SCRIPT_DIR%\start-dev-pro.bat"
goto :menu

:infra_mode
echo.
echo [INFO] Starting Infrastructure...
sc query postgresql-x64-17 >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PostgreSQL service not found
) else (
    net start postgresql-x64-17 >nul 2>&1
    echo [OK] PostgreSQL started or already running
)
sc query redis >nul 2>&1
if errorlevel 1 (
    echo [WARN] Redis service not found
) else (
    net start redis >nul 2>&1
    echo [OK] Redis started or already running
)
pause
goto :menu

:backend_mode
echo.
echo [INFO] Starting Backend...
start "Backend Service" "%SCRIPT_DIR%\start-backend-only.bat"
goto :menu

:frontend_mode
echo.
echo [INFO] Starting Frontend...
start "Frontend Service" "%SCRIPT_DIR%\start-frontend-only.bat"
goto :menu

:init_data
echo.
echo [INFO] Initializing Data...
call "%SCRIPT_DIR%\init-data.bat"
pause
goto :menu

:check_status
echo.
echo [INFO] Checking Service Status...
call "%SCRIPT_DIR%\check-service.bat" all
pause
goto :menu

:check_db
echo.
echo [INFO] Checking Database Status...
call "%SCRIPT_DIR%\check-db-status.bat"
goto :menu

:clean_data_only
echo.
echo ========================================
echo  Clean All Factor Data
echo ========================================
echo.
echo This will clean:
echo   - Validation pipeline data
echo   - Candidate factors
echo   - Evolution tasks
echo   - Generation statistics
echo.
echo WARNING: This action cannot be undone!
echo.
set /p confirm="Are you sure you want to clean all data? [y/N]: "
if /i not "%confirm%"=="y" (
    echo [INFO] Cancelled
    pause
    goto :menu
)

echo.
echo [INFO] Cleaning all factor data...
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"
set "BACKEND_PATH=%PROJECT_ROOT%\backend"
cd /d "%BACKEND_PATH%"

for /f "delims=" %%i in ('cd /d "%BACKEND_PATH%" ^& poetry env info --path 2^>nul') do set "VENV_PATH=%%i"
if defined VENV_PATH (
    echo [INFO] Using Python from: %VENV_PATH%
    "%VENV_PATH%\Scripts\python.exe" scripts\cleanup\clean_data_simple.py clean
    if errorlevel 1 (
        echo [ERROR] Data cleaning failed
    ) else (
        echo [OK] Data cleaning completed successfully
    )
) else (
    echo [ERROR] Poetry environment not found
    echo [INFO] Trying system Python...
    python scripts\cleanup\clean_data_simple.py clean
    if errorlevel 1 (
        echo [ERROR] Data cleaning failed with system Python
    ) else (
        echo [OK] Data cleaning completed successfully
    )
)
pause
goto :menu

:clean_data_then_dev
echo.
echo ========================================
echo  Clean Data + Start Dev Mode
echo ========================================
echo.
echo This will:
echo   1. Start infrastructure (PostgreSQL + Redis)
echo   2. Clean all factor data
echo   3. Start basic development mode
echo.
set /p confirm="Continue with clean and start? [y/N]: "
if /i not "%confirm%"=="y" (
    echo [INFO] Cancelled
    pause
    goto :menu
)

echo.
echo [INFO] Step 1: Starting infrastructure (PostgreSQL + Redis)...
sc query postgresql-x64-17 >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PostgreSQL service not found
    pause
    goto :menu
) else (
    net start postgresql-x64-17 >nul 2>&1
    echo [OK] PostgreSQL started or already running
)
sc query redis >nul 2>&1
if errorlevel 1 (
    echo [WARN] Redis service not found
) else (
    net start redis >nul 2>&1
    echo [OK] Redis started or already running
)
echo [OK] Waiting for database to be ready...
timeout /t 3 /nobreak >nul

echo.
echo [INFO] Step 2: Cleaning all factor data...
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"
set "BACKEND_PATH=%PROJECT_ROOT%\backend"
cd /d "%BACKEND_PATH%"

for /f "delims=" %%i in ('cd /d "%BACKEND_PATH%" ^& poetry env info --path 2^>nul') do set "VENV_PATH=%%i"
if defined VENV_PATH (
    "%VENV_PATH%\Scripts\python.exe" scripts\cleanup\clean_data_simple.py clean
    if errorlevel 1 (
        echo [ERROR] Data cleaning failed, aborting startup
        pause
        goto :menu
    )
) else (
    python scripts\cleanup\clean_data_simple.py clean
    if errorlevel 1 (
        echo [ERROR] Data cleaning failed, aborting startup
        pause
        goto :menu
    )
)

echo [OK] Data cleaning completed
echo.
echo [INFO] Step 3: Starting Development Mode...
timeout /t 2 /nobreak >nul
start "Development Mode" "%SCRIPT_DIR%\start-dev.bat"
goto :menu

:clean_data_then_pro
echo.
echo ========================================
echo  Clean Data + Start Enhanced Mode
echo ========================================
echo.
echo This will:
echo   1. Start infrastructure (PostgreSQL + Redis)
echo   2. Clean all factor data
echo   3. Start enhanced development mode (with GPU detection)
echo.
set /p confirm="Continue with clean and start? [y/N]: "
if /i not "%confirm%"=="y" (
    echo [INFO] Cancelled
    pause
    goto :menu
)

echo.
echo [INFO] Step 1: Starting infrastructure (PostgreSQL + Redis)...
sc query postgresql-x64-17 >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PostgreSQL service not found
    pause
    goto :menu
) else (
    net start postgresql-x64-17 >nul 2>&1
    echo [OK] PostgreSQL started or already running
)
sc query redis >nul 2>&1
if errorlevel 1 (
    echo [WARN] Redis service not found
) else (
    net start redis >nul 2>&1
    echo [OK] Redis started or already running
)
echo [OK] Waiting for database to be ready...
timeout /t 3 /nobreak >nul

echo.
echo [INFO] Step 2: Cleaning all factor data...
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"
set "BACKEND_PATH=%PROJECT_ROOT%\backend"
cd /d "%BACKEND_PATH%"

for /f "delims=" %%i in ('cd /d "%BACKEND_PATH%" ^& poetry env info --path 2^>nul') do set "VENV_PATH=%%i"
if defined VENV_PATH (
    "%VENV_PATH%\Scripts\python.exe" scripts\cleanup\clean_data_simple.py clean
    if errorlevel 1 (
        echo [ERROR] Data cleaning failed, aborting startup
        pause
        goto :menu
    )
) else (
    python scripts\cleanup\clean_data_simple.py clean
    if errorlevel 1 (
        echo [ERROR] Data cleaning failed, aborting startup
        pause
        goto :menu
    )
)

echo [OK] Data cleaning completed
echo.
echo [INFO] Step 3: Starting Enhanced Development Mode...
timeout /t 2 /nobreak >nul
start "Enhanced Dev Mode" "%SCRIPT_DIR%\start-dev-pro.bat"
goto :menu

:restart_all
echo.
echo [INFO] Restarting All Services...
call "%SCRIPT_DIR%\restart-all.bat"
goto :menu

:stop_all
echo.
echo [INFO] Stopping services...
net stop postgresql-x64-17 >nul 2>&1
net stop redis >nul 2>&1
echo [OK] Services stopped
pause
goto :menu

:clean_ports
echo.
echo [INFO] Cleaning port occupation...
call "%SCRIPT_DIR%\clean-ports.bat"
pause
goto :menu

:gpu_setup
echo.
echo ========================================
echo  GPU Acceleration Setup - PyTorch Nightly
echo ========================================
echo.
echo This tool installs PyTorch Nightly for RTX 5070 Ti
echo.
echo Notes:
echo   - RTX 5070 Ti (Blackwell sm_120) requires PyTorch Nightly
echo   - Stable PyTorch does not support sm_120 architecture
echo.
echo Options:
echo   [1] Install PyTorch Nightly (CUDA 12.8) - Recommended
echo   [2] Install PyTorch Nightly (CUDA 13.0) - For newer drivers
echo   [3] Return to main menu
echo.
set /p gpu_choice="Enter option [1-3]: "

if "%gpu_choice%"=="3" goto :menu
if "%gpu_choice%"=="1" goto :install_cu128
if "%gpu_choice%"=="2" goto :install_cu130

goto :gpu_setup

:install_cu128
echo.
echo [INFO] Installing PyTorch Nightly (CUDA 12.8)...
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"
set "BACKEND_PATH=%PROJECT_ROOT%\backend"
cd /d "%BACKEND_PATH%"
for /f "delims=" %%i in ('cd /d "%BACKEND_PATH%" ^& poetry env info --path 2^>nul') do set "VENV_PATH=%%i"
if defined VENV_PATH (
    "%VENV_PATH%\Scripts\python.exe" -m pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128
    echo [OK] Installation completed
) else (
    echo [ERROR] Poetry environment not found
)
pause
goto :menu

:install_cu130
echo.
echo [INFO] Installing PyTorch Nightly (CUDA 13.0)...
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"
set "BACKEND_PATH=%PROJECT_ROOT%\backend"
cd /d "%BACKEND_PATH%"
for /f "delims=" %%i in ('cd /d "%BACKEND_PATH%" ^& poetry env info --path 2^>nul') do set "VENV_PATH=%%i"
if defined VENV_PATH (
    "%VENV_PATH%\Scripts\python.exe" -m pip install --pre torch torchvision --index-url https://download.pytorch.org/whl/nightly/cu130
    echo [OK] Installation completed
) else (
    echo [ERROR] Poetry environment not found
)
pause
goto :menu

:check_pytorch
echo.
echo [INFO] Checking PyTorch Status...
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"
set "BACKEND_PATH=%PROJECT_ROOT%\backend"
cd /d "%BACKEND_PATH%"
for /f "delims=" %%i in ('cd /d "%BACKEND_PATH%" ^& poetry env info --path 2^>nul') do set "VENV_PATH=%%i"
if defined VENV_PATH (
    echo.
    "%VENV_PATH%\Scripts\python.exe" -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA Available: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"CPU Mode\"}')"
) else (
    echo [ERROR] Poetry environment not found
)
echo.
pause
goto :menu

:readme
echo.
echo [INFO] Opening README...
if exist "%SCRIPT_DIR%\README-zh.md" (
    start "" "%SCRIPT_DIR%\README-zh.md"
    echo [OK] Document opened
) else (
    echo [ERR] README file not found
)
pause
goto :menu

:joint_evolution
echo.
echo [INFO] Starting Joint Evolution Mode...
start "Joint Evolution" "%SCRIPT_DIR%\start-joint-evolution.bat"
goto :menu

:hybrid_evolution
echo.
echo [INFO] Starting Hybrid Evolution Mode...
start "Hybrid Evolution" "%SCRIPT_DIR%\start-hybrid-evolution.bat"
goto :menu

:evolution_comparison
echo.
echo [INFO] Starting Evolution Mode Comparison Test...
start "Evolution Comparison" "%SCRIPT_DIR%\start-evolution-comparison.bat"
goto :menu
timeout /t 2 /nobreak >nul
goto :menu

:exit
echo.
echo Thank you for using Launch Center Enhanced!
echo.
endlocal
exit /b 0
