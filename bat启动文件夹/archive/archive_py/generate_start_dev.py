# -*- coding: utf-8 -*-
"""
生成 start-dev.bat 批处理文件
"""
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

bat_content = r"""@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM 基础开发模式启动脚本
REM ============================================================

chcp 936 >nul 2>&1

title 基础开发模式 - 期货自动进化因子挖掘系统

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
for %%I in ("%PROJECT_ROOT%") do set "PROJECT_ROOT=%%~fI"
set "BACKEND_PATH=%PROJECT_ROOT%\backend"
set "FRONTEND_PATH=%PROJECT_ROOT%\frontend"
set "BACKEND_PORT=8000"
set "FRONTEND_PORT=5173"

for /f "delims=" %%i in ('cd /d "%BACKEND_PATH%" ^&^& poetry env info --path 2^>nul') do set "VENV_PATH=%%i"
if not defined VENV_PATH (
    set "VENV_PATH=%BACKEND_PATH%\.venv"
)
set "PYTHON=%VENV_PATH%\Scripts\python.exe"

:menu
cls
echo.
echo ========================================
echo  基础开发模式 - 期货自动进化因子挖掘系统
echo ========================================
echo.
echo 项目目录: %PROJECT_ROOT%
echo 后端目录: %BACKEND_PATH%
echo 前端目录: %FRONTEND_PATH%
echo 后端端口: %BACKEND_PORT%
echo 前端端口: %FRONTEND_PORT%
echo.

REM 检查服务状态
echo [服务状态]
call "%SCRIPT_DIR%\check-service.bat" all
echo.

echo 启动选项:
echo   [1] 完整启动 (基础设施 + 后端 + 前端)
echo   [2] 仅启动基础设施
echo   [3] 仅启动后端
echo   [4] 仅启动前端
echo   [5] 智能启动 (仅启动未运行的服务)
echo   [0] 退出
echo.

set /p choice=请选择选项 [0-5]:

if "%choice%"=="0" goto :exit_script
if "%choice%"=="1" goto :start_all
if "%choice%"=="2" goto :start_infra
if "%choice%"=="3" goto :start_backend
if "%choice%"=="4" goto :start_frontend
if "%choice%"=="5" goto :start_smart

echo [ERR] 无效选项，请重新选择
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
set "INFRA_NEED_START=0"
set "BACKEND_NEED_START=0"
set "FRONTEND_NEED_START=0"
docker-compose -f "%PROJECT_ROOT%\docker-compose.yml" ps timescaledb 2>&1 | findstr "Up" >nul
if errorlevel 1 set "INFRA_NEED_START=1"
netstat -ano | findstr "0.0.0.0:%BACKEND_PORT%" | findstr "LISTENING" >nul
if errorlevel 1 set "BACKEND_NEED_START=1"
netstat -ano | findstr "0.0.0.0:%FRONTEND_PORT%" | findstr "LISTENING" >nul
if errorlevel 1 set "FRONTEND_NEED_START=1"
goto :start_process

:start_process
echo.

if "!INFRA_NEED_START!"=="1" (
    echo [INFO] 启动基础设施 (TimescaleDB + Redis)...
    cd /d "%PROJECT_ROOT%"
    docker-compose up -d timescaledb redis
    if errorlevel 1 (
        echo [ERR] 基础设施启动失败
        pause
        exit /b 1
    )
    echo [OK] 基础设施已启动
)

if "!BACKEND_NEED_START!"=="1" (
    echo [INFO] 启动后端服务...
    for /f "tokens=5" %%p in ('netstat -ano ^| findstr "0.0.0.0:%BACKEND_PORT%" ^| findstr "LISTENING"') do (
        taskkill /F /PID %%p >nul 2>&1
    )
    timeout /t 1 /nobreak >nul
    start "Backend - Port %BACKEND_PORT%" cmd /k cd /d "%BACKEND_PATH%" ^&^& set PYTHONPATH=%BACKEND_PATH% ^&^& "%PYTHON%" -m uvicorn app.main:app --host 0.0.0.0 --port %BACKEND_PORT% --reload --log-level info
    echo [OK] 后端服务已启动
)

if "!FRONTEND_NEED_START!"=="1" (
    echo [INFO] 启动前端服务...
    for /f "tokens=5" %%p in ('netstat -ano ^| findstr "0.0.0.0:%FRONTEND_PORT%" ^| findstr "LISTENING"') do (
        taskkill /F /PID %%p >nul 2>&1
    )
    timeout /t 1 /nobreak >nul
    start "Frontend - Port %FRONTEND_PORT%" cmd /k cd /d "%FRONTEND_PATH%" ^&^& npm run dev
    echo [OK] 前端服务已启动
)

echo.
echo ========================================
echo  启动完成!
echo ========================================
echo.
echo 访问地址:
echo   前端: http://localhost:%FRONTEND_PORT%
echo   后端 API: http://localhost:%BACKEND_PORT%
echo   API 文档: http://localhost:%BACKEND_PORT%/docs
echo.
echo 按任意键返回菜单...
pause >nul
goto :menu

:exit_script
echo 再见!
exit /b 0
"""

# 写入 GBK 编码的批处理文件
with open(os.path.join(SCRIPT_DIR, 'start-dev.bat'), 'w', encoding='gbk') as f:
    f.write(bat_content)

print('start-dev.bat 已重新创建 (GBK 编码)')