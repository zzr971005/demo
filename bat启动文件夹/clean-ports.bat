@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM Port Cleanup Script
REM ============================================================

title Port Cleanup

echo.
echo ========================================
echo  Port Cleanup
echo ========================================
echo.

set "PORTS=5432 6379 8000 5173"

echo [INFO] Ports to clean: %PORTS%
echo.

for %%p in (%PORTS%) do (
    echo [Processing] Port %%p...
    set "PORT_CLEANED=0"
    
    for /f "tokens=5" %%i in ('netstat -ano ^| findstr "0.0.0.0:%%p" ^| findstr "LISTENING"') do (
        set "PID=%%i"
        if not "!PID!"=="" (
            echo [INFO] Port %%p occupied by PID !PID! (0.0.0.0)
            taskkill /F /PID !PID! >nul 2>&1
            if !errorlevel! equ 0 (
                echo [OK] Killed PID !PID!
                set "PORT_CLEANED=1"
            ) else (
                echo [WARN] Failed to kill PID !PID!
            )
        )
    )
    
    for /f "tokens=5" %%i in ('netstat -ano ^| findstr "127.0.0.1:%%p" ^| findstr "LISTENING"') do (
        set "PID=%%i"
        if not "!PID!"=="" (
            echo [INFO] Port %%p occupied by PID !PID! (127.0.0.1)
            taskkill /F /PID !PID! >nul 2>&1
            if !errorlevel! equ 0 (
                echo [OK] Killed PID !PID!
                set "PORT_CLEANED=1"
            ) else (
                echo [WARN] Failed to kill PID !PID!
            )
        )
    )
    
    for /f "tokens=5" %%i in ('netstat -ano ^| findstr "[::]:%%p" ^| findstr "LISTENING"') do (
        set "PID=%%i"
        if not "!PID!"=="" (
            echo [INFO] Port %%p occupied by PID !PID! (IPv6)
            taskkill /F /PID !PID! >nul 2>&1
            if !errorlevel! equ 0 (
                echo [OK] Killed PID !PID!
                set "PORT_CLEANED=1"
            ) else (
                echo [WARN] Failed to kill PID !PID!
            )
        )
    )
    
    if !PORT_CLEANED! equ 0 (
        echo [OK] Port %%p not occupied
    )
    echo.
)

echo [Extra] Cleaning related processes...
echo.

tasklist /FI "IMAGENAME eq python.exe" 2>nul | findstr /I "uvicorn" >nul
if !errorlevel! equ 0 (
    echo [INFO] Found uvicorn processes, stopping...
    for /f "tokens=2" %%p in ('tasklist /FI "IMAGENAME eq python.exe" /FO CSV 2^>nul ^| findstr /I "uvicorn"') do (
        set "PID=%%p"
        set "PID=!PID:"=!"
        if not "!PID!"=="" (
            taskkill /F /PID !PID! >nul 2>&1
            if !errorlevel! equ 0 (
                echo [OK] Killed Python PID !PID!
            )
        )
    )
)

tasklist /FI "IMAGENAME eq node.exe" 2>nul | findstr /I "node" >nul
if !errorlevel! equ 0 (
    echo [INFO] Found node processes, stopping...
    for /f "tokens=2" %%p in ('tasklist /FI "IMAGENAME eq node.exe" /FO CSV 2^>nul') do (
        set "PID=%%p"
        set "PID=!PID:"=!"
        if not "!PID!"=="" (
            taskkill /F /PID !PID! >nul 2>&1
            if !errorlevel! equ 0 (
                echo [OK] Killed Node PID !PID!
            )
        )
    )
)

tasklist /FI "IMAGENAME eq postgres.exe" 2>nul | findstr /I "postgres" >nul
if !errorlevel! equ 0 (
    echo [INFO] Found postgres processes (will be managed by service)
)
echo.
echo [SUCCESS] Port cleanup completed
echo.