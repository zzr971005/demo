# -*- coding: utf-8 -*-

bat_content = '''@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM 数据初始化脚本 - 下载历史K线数据
REM ============================================================

REM 设置代码页为 GBK (936) 以支持中文显示
chcp 936 >nul 2>&1

title 数据初始化工具

REM 获取脚本目录和项目根目录
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
for %%I in ("%PROJECT_ROOT%") do set "PROJECT_ROOT=%%~fI"
set "BACKEND_PATH=%PROJECT_ROOT%\\backend"

REM 获取 Poetry 虚拟环境路径
for /f "delims=" %%i in ('cd /d "%BACKEND_PATH%" ^& poetry env info --path 2^>nul') do set "VENV_PATH=%%i"
if not defined VENV_PATH (
    set "VENV_PATH=%BACKEND_PATH%\\.venv"
)
set "PYTHON=%VENV_PATH%\\Scripts\\python.exe"

echo.
echo ========================================
echo  数据初始化工具
echo ========================================
echo.
echo 项目根目录: %PROJECT_ROOT%
echo 后端目录: %BACKEND_PATH%
echo Python: %PYTHON%
echo.

REM 检查 Python 虚拟环境
echo [1/4] 检查 Python 虚拟环境...
if not exist "%PYTHON%" (
    echo [ERR] Python 虚拟环境未找到
    echo [INFO] 请执行: cd backend ^& poetry install
    pause
    exit /b 1
)
echo [OK] Python 环境正常

REM 检查 Docker
echo [2/4] 检查 Docker...
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERR] Docker 未安装或未运行
    echo [INFO] 请启动 Docker Desktop
    pause
    exit /b 1
)
echo [OK] Docker 正常

REM 检查基础设施
echo [3/4] 检查基础设施...
cd /d "%PROJECT_ROOT%"
docker-compose ps timescaledb 2>&1 | findstr "Up" >nul
if errorlevel 1 (
    echo [INFO] TimescaleDB 未运行，正在启动...
    docker-compose up -d timescaledb redis

    REM 等待数据库就绪
    echo [INFO] 等待数据库就绪...
    set "DB_READY=0"
    for /L %%i in (1,1,30) do (
        timeout /t 1 /nobreak >nul
        docker-compose exec -T timescaledb pg_isready -U qmt -d quant_db >nul 2>&1
        if !errorlevel! equ 0 (
            set "DB_READY=1"
            goto :db_ready
        )
        echo|set /p=.
    )
    echo.

    :db_ready
    if !DB_READY! equ 0 (
        echo [ERR] 数据库连接超时!
        echo [INFO] 解决方案:
        echo   1. 确认已启动 Docker Desktop
        echo   2. 确认项目 docker-compose.yml 配置正确
        echo   3. 手动启动: docker-compose up -d timescaledb redis
        pause
        exit /b 1
    ) else (
        echo [OK] 数据库就绪
    )
) else (
    echo [OK] 基础设施已运行
)

REM 选择初始化模式
echo [4/4] 选择初始化模式:
echo.
echo   [1] 增量更新 (仅下载新数据)
echo   [2] 全量初始化 (覆盖已有数据)
echo   [3] 仅检查数据状态
echo   [4] 下载扩展品种 (AU, CU, SC, IF)
echo.
set /p choice=请输入选项 [1-4]: 

if "%choice%"=="1" goto :incremental
if "%choice%"=="2" goto :full
if "%choice%"=="3" goto :check
if "%choice%"=="4" goto :extended

echo [ERR] 无效选项
pause
exit /b 1

:incremental
echo.
echo [INFO] 开始增量更新...
echo.
cd /d "%BACKEND_PATH%"
"%PYTHON%" -m app.init_data --incremental
if errorlevel 1 (
    echo.
    echo [ERR] 增量更新失败!
    pause
    exit /b 1
)
goto :success

:full
echo.
echo [WARN] 全量初始化将覆盖已有数据!
pause
cd /d "%BACKEND_PATH%"
"%PYTHON%" -m app.init_data --full --force
if errorlevel 1 (
    echo.
    echo [ERR] 全量初始化失败!
    pause
    exit /b 1
)
goto :success

:check
echo.
echo [INFO] 检查数据状态...
echo.
cd /d "%BACKEND_PATH%"
"%PYTHON%" -m app.init_data --check
if errorlevel 1 (
    echo.
    echo [ERR] 检查数据状态失败!
    pause
    exit /b 1
)
goto :success

:extended
echo.
echo [INFO] 下载扩展品种数据...
echo.
cd /d "%BACKEND_PATH%"
"%PYTHON%" -m app.init_data --full --extended
if errorlevel 1 (
    echo.
    echo [ERR] 下载扩展品种数据失败!
    pause
    exit /b 1
)
goto :success

:success
echo.
echo ========================================
echo [SUCCESS] 数据初始化完成!
echo ========================================
echo.
echo 提示:
echo   - 数据已保存到 TimescaleDB
echo   - 可以在后端查看数据
echo.
pause

:error
echo.
echo ========================================
echo [FAILED] 数据初始化失败!
echo ========================================
echo.
echo 提示:
echo   - 请检查错误信息并修复问题
echo   - 可以重新运行初始化工具
echo.
pause
exit /b 1
'''

with open(r'd:\期货自动进化因子挖掘系统\bat-scripts\init-data.bat', 'w', encoding='gbk') as f:
    f.write(bat_content)

print('文件已保存，编码: GBK (936)')
print('修复内容:')
print('  - 添加Python命令退出码检查')
print('  - 失败时显示错误信息并退出')
print('  - 只有成功时才显示成功信息')