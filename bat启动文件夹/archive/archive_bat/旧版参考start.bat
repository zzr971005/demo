@echo off
setlocal

REM 设置代码页为 GBK (936) 以支持中文显示
chcp 936 >nul 2>&1

title Quant Evo Factor Mining - Launcher

:: Change to project root for docker-compose
cd /d "%~dp0..\"

:: ============================================================
:: Quant Evo Factor Mining - Windows Launcher
:: ============================================================

echo.
echo  ========================================
echo   Quant Evo Factor Mining - Launcher
echo  ========================================
echo.

:: Check Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker not installed or not running. Please install Docker Desktop
    echo Download: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

:: Check Docker Compose
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Compose not installed
    pause
    exit /b 1
)

echo [INFO] Docker version:
docker --version
echo [INFO] Docker Compose version:
docker-compose --version
echo.

:: Menu
:menu
echo Select startup mode:
echo.
echo   [1] Full start (Docker Compose - Recommended)
echo   [2] Infra only (TimescaleDB + Redis)
echo   [3] Stop all services
echo   [4] Restart services
echo   [5] Service status
echo   [6] View logs
echo   [7] Full cleanup (delete volumes)
echo   [8] Enter backend container
echo   [9] Enter database
echo   [0] Exit
echo.

set /p choice="Enter option [0-9]: "

if "%choice%"=="1" goto start_full
if "%choice%"=="2" goto start_infra
if "%choice%"=="3" goto stop_all
if "%choice%"=="4" goto restart_all
if "%choice%"=="5" goto status
if "%choice%"=="6" goto logs
if "%choice%"=="7" goto clean_all
if "%choice%"=="8" goto enter_backend
if "%choice%"=="9" goto enter_db
if "%choice%"=="0" goto exit_script

echo [ERROR] Invalid option
pause
goto menu

:: ============================================================
:: 1. Full start
:: ============================================================
:start_full
echo.
echo [INFO] Starting full system...
echo [INFO] Services: TimescaleDB + Redis + Backend + Frontend
echo.

:: Check .env file
if not exist ".env" (
    echo [WARN] .env file not found, creating from template...
    copy backend\.env.example .env >nul
    echo [INFO] Please edit .env file to configure TQSDK account
    echo.
)

:: Build and start
docker-compose up -d --build
if errorlevel 1 (
    echo [ERROR] Start failed
    pause
    exit /b 1
)

echo.
echo [SUCCESS] System started!
echo.
echo Access:
echo   Frontend: http://localhost
echo   Backend API: http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo   Health: http://localhost:8000/health
echo.
pause
goto menu

:: ============================================================
:: 2. Infra only
:: ============================================================
:start_infra
echo.
echo [INFO] Starting infrastructure (TimescaleDB + Redis)...
docker-compose up -d timescaledb redis
if errorlevel 1 (
    echo [ERROR] Start failed
    pause
    exit /b 1
)
echo [SUCCESS] Infrastructure started
echo [INFO] You can manually start backend and frontend for dev
echo.
pause
goto menu

:: ============================================================
:: 3. Stop all
:: ============================================================
:stop_all
echo.
echo [INFO] Stopping all services...
docker-compose down
echo [SUCCESS] All services stopped
echo.
pause
goto menu

:: ============================================================
:: 4. Restart
:: ============================================================
:restart_all
echo.
echo [INFO] Restarting services...
docker-compose restart
echo [SUCCESS] Services restarted
echo.
pause
goto menu

:: ============================================================
:: 5. Status
:: ============================================================
:status
echo.
echo [INFO] Service status:
docker-compose ps
echo.
pause
goto menu

:: ============================================================
:: 6. Logs
:: ============================================================
:logs
echo.
echo Select service to view logs:
echo   [1] Backend
echo   [2] Frontend
echo   [3] TimescaleDB
echo   [4] Redis
echo   [5] All services
echo   [0] Back
echo.
set /p log_choice="Enter option: "

if "%log_choice%"=="1" docker-compose logs -f backend
if "%log_choice%"=="2" docker-compose logs -f frontend
if "%log_choice%"=="3" docker-compose logs -f timescaledb
if "%log_choice%"=="4" docker-compose logs -f redis
if "%log_choice%"=="5" docker-compose logs -f
if "%log_choice%"=="0" goto menu

goto menu

:: ============================================================
:: 7. Full cleanup
:: ============================================================
:clean_all
echo.
echo [WARN] This will delete all data volumes, including database data!
set /p confirm="Confirm cleanup? [yes/no]: "
if /i not "%confirm%"=="yes" goto menu

echo [INFO] Cleaning up...
docker-compose down -v
docker system prune -f
echo [SUCCESS] Cleanup completed
echo.
pause
goto menu

:: ============================================================
:: 8. Enter backend container
:: ============================================================
:enter_backend
echo.
echo [INFO] Entering backend container...
docker-compose exec backend bash
goto menu

:: ============================================================
:: 9. Enter database
:: ============================================================
:enter_db
echo.
echo [INFO] Entering database...
docker-compose exec timescaledb psql -U qmt -d quant_db
goto menu

:: ============================================================
:: 0. Exit
:: ============================================================
:exit_script
echo.
echo [INFO] Exiting launcher
echo.
exit /b 0