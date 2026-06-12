@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM Check Database Status (Local PostgreSQL + TimescaleDB)
REM ============================================================

title Check Database Status

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"

echo.
echo ========================================
echo  Check Database Status
echo ========================================
echo.
echo Project root: %PROJECT_ROOT%
echo.

set "DB_USER=postgres"
set "DB_PASS=postgres"
set "DB_NAME=quant_db"
set "DB_PORT=5432"

echo Database configuration:
echo   User: %DB_USER%
echo   Database: %DB_NAME%
echo   Port: %DB_PORT%
echo.

echo ========================================
echo  [1/6] PostgreSQL Service Status
echo ========================================
sc query postgresql-x64-17 >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] PostgreSQL 17 service not found
    echo   [INFO] Please install PostgreSQL 17 first
    goto :end_check
) else (
    sc query postgresql-x64-17 | findstr "RUNNING" >nul 2>&1
    if errorlevel 1 (
        echo   [WARN] PostgreSQL service not running
        echo   [INFO] Starting service...
        net start postgresql-x64-17 >nul 2>&1
        if errorlevel 1 (
            echo   [ERROR] Failed to start PostgreSQL service
            goto :end_check
        )
        timeout /t 3 /nobreak >nul
        echo   [OK] PostgreSQL service started
    ) else (
        echo   [OK] PostgreSQL service running
    )
)
echo.

echo ========================================
echo  [2/6] TimescaleDB Extension Check
echo ========================================
set "PGPASSWORD=%DB_PASS%"
"C:\Program Files\PostgreSQL\17\bin\psql.exe" -U %DB_USER% -d %DB_NAME% -c "SELECT extname, extversion FROM pg_extension WHERE extname='timescaledb';" > "%TEMP%\timescaledb_check.txt" 2>&1
findstr "timescaledb" "%TEMP%\timescaledb_check.txt" >nul 2>&1
if errorlevel 1 (
    echo   [WARN] TimescaleDB extension not found in database %DB_NAME%
    echo   [INFO] Creating extension...
    "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U %DB_USER% -d %DB_NAME% -c "CREATE EXTENSION IF NOT EXISTS timescaledb;" 2>&1
    if errorlevel 1 (
        echo   [ERROR] Failed to create TimescaleDB extension
    ) else (
        echo   [OK] TimescaleDB extension created
    )
) else (
    type "%TEMP%\timescaledb_check.txt"
    echo   [OK] TimescaleDB extension exists
)
del "%TEMP%\timescaledb_check.txt" 2>nul
echo.

echo ========================================
echo  [3/6] Port Listening Status
echo ========================================
netstat -ano | findstr "0.0.0.0:%DB_PORT%" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo   [WARN] Port %DB_PORT% not listening
) else (
    echo   [OK] Port %DB_PORT% listening
)
echo.

echo ========================================
echo  [4/6] Database Connection Test
echo ========================================
set "PGPASSWORD=%DB_PASS%"
"C:\Program Files\PostgreSQL\17\bin\psql.exe" -U %DB_USER% -d %DB_NAME% -c "SELECT 1 AS connection_test;" > "%TEMP%\db_conn.txt" 2>&1
findstr "connection_test" "%TEMP%\db_conn.txt" >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Database connection failed
    type "%TEMP%\db_conn.txt"
) else (
    echo   [OK] Database connection successful
)
del "%TEMP%\db_conn.txt" 2>nul
echo.

echo ========================================
echo  [5/6] Redis Status
echo ========================================
sc query redis >nul 2>&1
if errorlevel 1 (
    netstat -ano | findstr "0.0.0.0:6379" | findstr "LISTENING" >nul
    if errorlevel 1 (
        echo   [WARN] Redis not running
    ) else (
        echo   [OK] Redis running on port 6379 (direct start)
    )
) else (
    sc query redis | findstr "RUNNING" >nul
    if errorlevel 1 (
        echo   [WARN] Redis service not running
    ) else (
        echo   [OK] Redis service running (Port 6379)
    )
)
echo.

echo ========================================
echo  [6/6] Database Tables
echo ========================================
set "PGPASSWORD=%DB_PASS%"
"C:\Program Files\PostgreSQL\17\bin\psql.exe" -U %DB_USER% -d %DB_NAME% -c "\dt" 2>&1
echo.

:end_check
echo ========================================
echo  Summary
echo ========================================
echo.
echo Common troubleshooting steps:
echo.
echo 1. PostgreSQL won't start
echo    - Check if port 5432 is occupied by another process
echo    - Check Windows Event Viewer for errors
echo    - Restart: net stop postgresql-x64-17 ^&^& net start postgresql-x64-17
echo.
echo 2. Connection rejected
echo    - Verify credentials: %DB_USER%/%DB_PASS%
echo    - Verify database name: %DB_NAME%
echo    - Check pg_hba.conf for authentication settings
echo.
echo 3. Redis not available
echo    - Install Redis or start manually from C:\Program Files\Redis
echo    - Run: redis-server.exe
echo.
echo Useful commands:
echo   - Check PG: "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U %DB_USER% -d %DB_NAME% -c "\dt"
echo   - Test PG: "C:\Program Files\PostgreSQL\17\bin\pg_isready.exe"
echo   - Test Redis: "C:\Program Files\Redis\redis-cli.exe" ping
echo.
pause