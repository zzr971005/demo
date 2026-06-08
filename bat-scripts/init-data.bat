@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM Data Initialization Script - Download Historical K-line Data
REM ============================================================

title Data Initialization Tool

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"
set "BACKEND_PATH=%PROJECT_ROOT%\backend"

for /f "delims=" %%i in ('cd /d "%BACKEND_PATH%" ^& poetry env info --path 2^>nul') do set "VENV_PATH=%%i"
if not defined VENV_PATH (
    set "VENV_PATH=%BACKEND_PATH%\.venv"
)
set "PYTHON=%VENV_PATH%\Scripts\python.exe"

echo.
echo ========================================
echo  Data Initialization Tool
echo ========================================
echo.
echo Project Root: %PROJECT_ROOT%
echo Backend Dir: %BACKEND_PATH%
echo Python: %PYTHON%
echo.

echo [1/4] Checking Python virtual environment...
if not exist "%PYTHON%" (
    echo [ERR] Python virtual environment not found
    echo [INFO] Run: cd backend ^& poetry install
    pause
    exit /b 1
)
echo [OK] Python environment ready

echo [2/4] Checking PostgreSQL service...
sc query postgresql-x64-17 >nul 2>&1
if errorlevel 1 (
    echo [ERR] PostgreSQL 17 service not found
    echo [INFO] Please install PostgreSQL 17 with TimescaleDB first
    pause
    exit /b 1
)

sc query postgresql-x64-17 | findstr "RUNNING" >nul
if errorlevel 1 (
    echo [INFO] PostgreSQL not running, starting...
    net start postgresql-x64-17 >nul 2>&1
    if errorlevel 1 (
        echo [ERR] Failed to start PostgreSQL
        pause
        exit /b 1
    )
    echo [OK] PostgreSQL started
) else (
    echo [OK] PostgreSQL already running
)

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

echo [4/4] Select initialization mode:
echo.
echo   [1] Incremental update (continue from last end time)
echo   [2] Full initialization (download all symbols, last 1 year)
echo   [3] Check data status
echo   [4] Download extended symbols (AU, CU, SC, IF)
echo   [5] Check backup status (DB vs CSV)
echo   [6] Restore from CSV backup
echo   [7] Download term structure data (full, default symbols)
echo   [8] Download term structure data (incremental)
echo   [9] Download term structure data (extended, incl. IF)
echo.
set /p choice=Enter option [1-9]:

if "%choice%"=="1" goto :incremental
if "%choice%"=="2" goto :full
if "%choice%"=="3" goto :check
if "%choice%"=="4" goto :extended
if "%choice%"=="5" goto :check_backup
if "%choice%"=="6" goto :restore_backup
if "%choice%"=="7" goto :term_structure
if "%choice%"=="8" goto :term_structure_incremental
if "%choice%"=="9" goto :term_structure_extended

echo [ERR] Invalid option
pause
exit /b 1

:incremental
echo.
echo [INFO] Starting incremental update...
echo.
cd /d "%BACKEND_PATH%"
"%PYTHON%" -m app.init_data --incremental
if errorlevel 1 (
    echo.
    echo [ERR] Incremental update failed!
    pause
    exit /b 1
)
goto :success

:full
echo.
echo [WARN] Full initialization will overwrite existing data!
pause
cd /d "%BACKEND_PATH%"
"%PYTHON%" -m app.init_data --full --force
if errorlevel 1 (
    echo.
    echo [ERR] Full initialization failed!
    pause
    exit /b 1
)
goto :success

:check
echo.
echo [INFO] Checking data status...
echo.
cd /d "%BACKEND_PATH%"
"%PYTHON%" -m app.init_data --check
if errorlevel 1 (
    echo.
    echo [ERR] Check data status failed!
    pause
    exit /b 1
)
goto :success

:extended
echo.
echo [INFO] Downloading extended symbols...
echo.
cd /d "%BACKEND_PATH%"
"%PYTHON%" -m app.init_data --full --extended
if errorlevel 1 (
    echo.
    echo [ERR] Download extended symbols failed!
    pause
    exit /b 1
)
goto :success

:check_backup
echo.
echo [INFO] Checking backup status...
echo.
cd /d "%BACKEND_PATH%"
"%PYTHON%" -m app.init_data --check-backup
if errorlevel 1 (
    echo.
    echo [ERR] Check backup status failed!
    pause
    exit /b 1
)
goto :success

:restore_backup
echo.
echo [WARN] Restore from CSV backup will overwrite existing data!
pause
cd /d "%BACKEND_PATH%"
"%PYTHON%" -m app.init_data --restore
if errorlevel 1 (
    echo.
    echo [ERR] Restore from backup failed!
    pause
    exit /b 1
)
echo.
echo [INFO] Restore complete! Suggest running incremental update to get latest data...
pause
goto :success

:term_structure
echo.
echo [INFO] Downloading term structure data (full)...
echo.
cd /d "%BACKEND_PATH%"
"%PYTHON%" -m app.init_data --term-structure --force
if errorlevel 1 (
    echo.
    echo [ERR] Term structure download failed!
    pause
    exit /b 1
)
goto :success

:term_structure_incremental
echo.
echo [INFO] Downloading term structure data (incremental)...
echo.
cd /d "%BACKEND_PATH%"
"%PYTHON%" -m app.init_data --term-structure-incremental
if errorlevel 1 (
    echo.
    echo [ERR] Term structure incremental update failed!
    pause
    exit /b 1
)
goto :success

:term_structure_extended
echo.
echo [INFO] Downloading term structure data (extended, incl. IF)...
echo.
cd /d "%BACKEND_PATH%"
"%PYTHON%" -m app.init_data --term-structure --extended --force
if errorlevel 1 (
    echo.
    echo [ERR] Term structure extended download failed!
    pause
    exit /b 1
)
goto :success

:success
echo.
echo ========================================
echo [SUCCESS] Operation completed!
echo ========================================
echo.
echo Notes:
echo   - Data saved to TimescaleDB
echo   - Data auto-backed up to CSV
echo   - Can view data in frontend
echo.
pause
exit /b 0

:error
echo.
echo ========================================
echo [FAILED] Operation failed!
echo ========================================
echo.
echo Notes:
echo   - Check error message and fix problem
echo   - Can rerun this tool
echo.
pause
exit /b 1