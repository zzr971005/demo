@echo off
setlocal enabledelayedexpansion

REM 设置代码页为 UTF-8 (65001) 以支持中文显示
chcp 936 >nul 2>&1

title Quant Evo Factor Mining - Frontend

:: ============================================================
:: Quant Evo Factor Mining - Frontend Startup
:: ============================================================

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\"
for %%I in ("%PROJECT_ROOT%") do set "PROJECT_ROOT=%%~fI"
set "FRONTEND_PATH=%PROJECT_ROOT%\frontend"
set "FRONTEND_PORT=3000"

echo.
echo ========================================
echo  Quant Evo Factor Mining - Frontend
echo ========================================
echo.
echo Project root: %PROJECT_ROOT%
echo Frontend path: %FRONTEND_PATH%
echo Frontend port: %FRONTEND_PORT%
echo.

:: ========== Check Node.js ==========
echo [1/2] Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERR] Node.js not installed
    echo [INFO] Please install Node.js first
    pause
    exit /b 1
)
echo [OK] Node.js is available

:: ========== Check node_modules ==========
echo [2/2] Checking frontend dependencies...
cd /d "%FRONTEND_PATH%"

if not exist "node_modules" (
    echo [INFO] node_modules not found, installing dependencies...
    npm install
    if errorlevel 1 (
        echo [ERR] Failed to install frontend dependencies
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed
) else (
    echo [OK] node_modules exists
)

:: ========== Check Port ==========
for /f "tokens=5" %%p in ('netstat -ano ^| findstr "0.0.0.0:%FRONTEND_PORT%" ^| findstr "LISTENING"') do (
    echo [INFO] Port %FRONTEND_PORT% is in use, stopping existing process...
    taskkill /F /PID %%p >nul 2>&1
)
timeout /t 1 /nobreak >nul

:: ========== Start Frontend ==========
echo.
echo ========================================
echo Frontend Service
echo URL: http://localhost:%FRONTEND_PORT%
echo ========================================
echo.
echo Starting frontend dev server...
echo DO NOT CLOSE THIS WINDOW!
echo.

npm run dev
set "VITE_EXIT=!errorlevel!"

echo.
echo ========================================
echo Frontend service stopped
echo Exit code: !VITE_EXIT!
echo ========================================
echo.

echo [OK] Press any key to exit...
pause >nul

endlocal
