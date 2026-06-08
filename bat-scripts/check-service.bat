@echo off
setlocal

title Service Status Check

echo.
echo ========================================
echo  Service Status Check
echo ========================================
echo.

echo [Checking] PostgreSQL...
sc query postgresql-x64-17 >nul 2>&1
if errorlevel 1 (
    echo [PostgreSQL] Not installed
) else (
    sc query postgresql-x64-17 | findstr "RUNNING" >nul
    if errorlevel 1 (
        echo [PostgreSQL] Installed but not running
    ) else (
        echo [PostgreSQL] Running (Port 5432)
    )
)

echo [Checking] Redis...
sc query redis >nul 2>&1
if errorlevel 1 (
    echo [Redis] Not installed
) else (
    sc query redis | findstr "RUNNING" >nul
    if errorlevel 1 (
        echo [Redis] Installed but not running
    ) else (
        echo [Redis] Running (Port 6379)
    )
)

echo [Checking] Backend...
netstat -ano | findstr ":8000" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo [Backend] Not running
) else (
    echo [Backend] Running (Port 8000)
)

echo [Checking] Frontend...
netstat -ano | findstr ":5173" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo [Frontend] Not running
) else (
    echo [Frontend] Running (Port 5173)
)

echo.
echo ========================================
echo  Quick Access
echo ========================================
echo.
echo   Backend API: http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo   Frontend: http://localhost:5173
echo.

endlocal
exit /b 0