# -*- coding: utf-8 -*-
"""
完全重写 start-dev-pro.bat，移除所有复杂的颜色变量和条件嵌套
"""
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
bat_path = os.path.join(SCRIPT_DIR, 'start-dev-pro.bat')

# 完全重写 start-dev-pro.bat，使用最简单的版本
new_content = '''@echo off
chcp 936 >nul 2>&1
title 增强版开发模式

echo.
echo ===============================
echo  增强版开发模式启动脚本
echo ===============================
echo.

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
set "BACKEND_PATH=%PROJECT_ROOT%\backend"
set "FRONTEND_PATH=%PROJECT_ROOT%\frontend"
set "BACKEND_PORT=8000"
set "FRONTEND_PORT=5173"

REM 预检查
echo [1/9] 环境预检查...
echo.

REM 检查 Docker
echo    [检查] Docker...
docker --version >nul 2>&1
if errorlevel 1 (
    echo    [错误] Docker 未安装或未运行
    echo    [提示] 请先安装并启动 Docker Desktop
    pause
    exit /b 1
)
echo    [OK] Docker 可用

REM 检查 Python 虚拟环境
echo    [检查] Python 虚拟环境...
for /f "delims=" %%i in ('cd /d "%BACKEND_PATH%" ^& poetry env info --path 2^>nul') do set "VENV_PATH=%%i"
if not defined VENV_PATH (
    echo    [提示] Poetry 虚拟环境未找到，正在创建...
    cd /d "%BACKEND_PATH%"
    poetry install --no-interaction
    if errorlevel 1 (
        echo    [错误] 虚拟环境创建失败
        pause
        exit /b 1
    )
    for /f "delims=" %%i in ('cd /d "%BACKEND_PATH%" ^& poetry env info --path 2^>nul') do set "VENV_PATH=%%i"
)
set "PYTHON=%VENV_PATH%\\Scripts\\python.exe"
if not exist "%PYTHON%" (
    echo    [错误] Python 可执行文件不存在
    pause
    exit /b 1
)
echo    [OK] Python 环境正常

REM 检查 Node.js
echo    [检查] Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo    [错误] Node.js 未安装
    pause
    exit /b 1
)
echo    [OK] Node.js 可用

REM 检查前端依赖
echo    [检查] 前端依赖...
if not exist "%FRONTEND_PATH%\\node_modules" (
    echo    [提示] node_modules 不存在，正在安装...
    cd /d "%FRONTEND_PATH%"
    npm install
    if errorlevel 1 (
        echo    [错误] 前端依赖安装失败
        pause
        exit /b 1
    )
)
echo    [OK] 前端依赖已安装

REM 检查服务状态
echo.
echo [2/9] 检查服务状态...
echo.

set "INFRA_NEED_START=0"
set "BACKEND_NEED_START=0"
set "FRONTEND_NEED_START=0"

docker-compose -f "%PROJECT_ROOT%\\docker-compose.yml" ps timescaledb 2>&1 | findstr "Up" >nul
if errorlevel 1 (
    echo    [基础设施] 未运行
    set "INFRA_NEED_START=1"
) else (
    echo    [基础设施] 运行中
)

netstat -ano | findstr "0.0.0.0:%BACKEND_PORT%" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo    [后端服务] 未运行
    set "BACKEND_NEED_START=1"
) else (
    echo    [后端服务] 运行中
)

netstat -ano | findstr "0.0.0.0:%FRONTEND_PORT%" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo    [前端服务] 未运行
    set "FRONTEND_NEED_START=1"
) else (
    echo    [前端服务] 运行中
)

REM 选择启动模式
echo.
echo [3/9] 选择启动模式:
echo.
echo    [1] 全部启动 (基础设施 + 后端 + 前端)
echo    [2] 仅启动基础设施
echo    [3] 仅启动后端
echo    [4] 仅启动前端
echo    [5] 智能启动 (仅启动未运行的服务)
echo    [0] 退出
echo.

set /p choice="请输入选项 [0-5]: "

if "%choice%"=="0" exit /b 0
if "%choice%"=="1" (
    set "INFRA_NEED_START=1"
    set "BACKEND_NEED_START=1"
    set "FRONTEND_NEED_START=1"
)
if "%choice%"=="2" (
    set "INFRA_NEED_START=1"
    set "BACKEND_NEED_START=0"
    set "FRONTEND_NEED_START=0"
)
if "%choice%"=="3" (
    set "INFRA_NEED_START=1"
    set "BACKEND_NEED_START=1"
    set "FRONTEND_NEED_START=0"
)
if "%choice%"=="4" (
    set "INFRA_NEED_START=0"
    set "BACKEND_NEED_START=0"
    set "FRONTEND_NEED_START=1"
)
if "%choice%"=="5" (
    echo.
    echo [提示] 智能启动模式，仅启动缺失的服务
)

REM 启动服务
echo.
echo [4-9/9] 启动服务...
echo.

REM 启动基础设施
if "%INFRA_NEED_START%"=="1" (
    echo    [启动] 基础设施...
    cd /d "%PROJECT_ROOT%"
    docker-compose up -d timescaledb redis
    if errorlevel 1 (
        echo    [错误] 基础设施启动失败
        pause
        exit /b 1
    )
    echo    [OK] 基础设施已启动
)

REM 检查并清理后端端口
if "%BACKEND_NEED_START%"=="1" (
    echo    [检查] 后端端口...
    for /f "tokens=5" %%p in ('netstat -ano ^| findstr "0.0.0.0:%BACKEND_PORT%" ^| findstr "LISTENING"') do (
        echo    [提示] 端口 %BACKEND_PORT% 被占用，清理进程 PID: %%p...
        taskkill /F /PID %%p >nul 2>&1
        timeout /t 1 /nobreak >nul
    )
    echo    [OK] 后端端口准备就绪
)

REM 检查并清理前端端口
if "%FRONTEND_NEED_START%"=="1" (
    echo    [检查] 前端端口...
    for /f "tokens=5" %%p in ('netstat -ano ^| findstr "0.0.0.0:%FRONTEND_PORT%" ^| findstr "LISTENING"') do (
        echo    [提示] 端口 %FRONTEND_PORT% 被占用，清理进程 PID: %%p...
        taskkill /F /PID %%p >nul 2>&1
        timeout /t 1 /nobreak >nul
    )
    echo    [OK] 前端端口准备就绪
)

REM 启动后端
if "%BACKEND_NEED_START%"=="1" (
    echo    [启动] 后端服务...
    echo    [信息] 端口: %BACKEND_PORT%
    echo    [提示] Ctrl+C 停止服务
    start "Backend - Port %BACKEND_PORT%" cmd /k cd /d "%BACKEND_PATH%" ^&^& set PYTHONPATH=%BACKEND_PATH% ^&^& "%PYTHON%" -m uvicorn app.main:app --host 0.0.0.0 --port %BACKEND_PORT% --reload --log-level info
    
    REM 等待后端启动
    echo    [等待] 后端启动...
    timeout /t 3 /nobreak >nul
)

REM 启动前端
if "%FRONTEND_NEED_START%"=="1" (
    echo    [启动] 前端服务...
    echo    [信息] 端口: %FRONTEND_PORT%
    echo    [提示] Ctrl+C 停止服务
    start "Frontend - Port %FRONTEND_PORT%" cmd /k cd /d "%FRONTEND_PATH%" ^&^& npm run dev
)

REM 完成提示
echo.
echo ===============================
echo  启动完成!
echo ===============================
echo.
echo 服务访问:
echo    前端: http://localhost:%FRONTEND_PORT%
echo    后端 API: http://localhost:%BACKEND_PORT%
echo    API 文档: http://localhost:%BACKEND_PORT%/docs
echo.
echo 独立窗口:
if "%BACKEND_NEED_START%"=="1" (
    echo    [Backend] 后端服务（热重载已启用）
)
if "%FRONTEND_NEED_START%"=="1" (
    echo    [Frontend] 前端服务（HMR 已启用）
)
echo.
echo 提示:
echo    后端代码修改自动重载
echo    前端 UI 修改自动刷新
echo    停止服务直接关闭对应窗口即可
echo.
echo 其他工具:
echo    init-data.bat     : 下载历史K线数据
echo    check-status.bat   : 检查服务状态
echo    stop-all.bat       : 停止所有服务
echo    clean-ports.bat    : 清理端口占用
echo.
echo 按任意键关闭此窗口（服务将继续运行...
pause >nul
'''

with open(bat_path, 'w', encoding='gbk') as f:
    f.write(new_content)

print('start-dev-pro.bat 已完全重写')