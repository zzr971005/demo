@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM Status Check Tool (Local Services)
REM ============================================================

title Status Check

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"

echo.
echo ========================================
echo  Status Check
echo ========================================
echo.

set "ALL_OK=1"

REM Check PostgreSQL
echo [1/5] Checking PostgreSQL...
sc query postgresql-x64-17 >nul 2>&1
if errorlevel 1 (
    echo   [WARN] PostgreSQL not installed
    set "ALL_OK=0"
) else (
    sc query postgresql-x64-17 | findstr "RUNNING" >nul 2>&1
    if errorlevel 1 (
        echo   [WARN] PostgreSQL service not running
        set "ALL_OK=0"
    ) else (
        echo   [OK] PostgreSQL running (Port 5432)
    )
)
echo.

REM Check TimescaleDB
echo [2/5] Checking TimescaleDB (Port 5432)...
netstat -ano | findstr "0.0.0.0:5432" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo   [WARN] Port 5432 not listening
    set "ALL_OK=0"
) else (
    echo   [OK] Port 5432 listening
)
echo.

REM Check Redis
echo [3/5] Checking Redis (Port 6379)...
netstat -ano | findstr "0.0.0.0:6379" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo   [WARN] Port 6379 not listening (Redis not running)
    set "ALL_OK=0"
) else (
    echo   [OK] Redis running (Port 6379)
)
echo.

REM Check Backend
echo [4/5] Checking Backend (Port 8000)...
netstat -ano | findstr "0.0.0.0:8000" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo   [INFO] Backend not running
) else (
    echo   [OK] Backend running
    curl -s http://localhost:8000/health >nul 2>&1
    if !errorlevel! equ 0 (
        echo   [OK] Health check passed
    )
)
echo.

REM Check Frontend
echo [5/5] Checking Frontend (Port 5173)...
netstat -ano | findstr "0.0.0.0:5173" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo   [INFO] Frontend not running
) else (
    echo   [OK] Frontend running
)
echo.

echo ========================================
echo  Database Connection Test
echo ========================================
set "PGPASSWORD=postgres"
"C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -d quant_db -c "SELECT current_timestamp AS db_time;" 2>"%TEMP%\db_err.txt"
if errorlevel 1 (
    echo [ERR] Database connection failed
    type "%TEMP%\db_err.txt"
) else (
    echo [OK] Database connection successful
)
del "%TEMP%\db_err.txt" 2>nul
echo.

if "%ALL_OK%"=="1" (
    echo [SUCCESS] All services are running
) else (
    echo [WARN] Some services are not running
    echo [INFO] Use launch center to start services
)
echo.