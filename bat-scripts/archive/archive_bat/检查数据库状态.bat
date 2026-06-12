@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM 数据库诊断工具
REM ============================================================

chcp 936 >nul 2>&1

title 数据库诊断工具

REM 获取脚本目录和项目目录
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\"
for %%I in ("%PROJECT_ROOT%") do set "PROJECT_ROOT=%%~fI"

echo.
echo ========================================
echo  数据库诊断工具
echo ========================================
echo.
echo 项目根目录: %PROJECT_ROOT%
echo.

REM 数据库连接信息
set "DB_USER=qmt"
set "DB_PASS=qmt_secret"
set "DB_NAME=quant_db"
set "DB_PORT=5432"

echo 数据库配置:
echo   用户: %DB_USER%
echo   数据库: %DB_NAME%
echo   端口: %DB_PORT%
echo.

REM ========================================
REM 检查 1: Docker 状态
REM ========================================
echo [检查 1/6] Docker 状态
echo ----------------------------------------
docker --version >nul 2>&1
if errorlevel 1 (
    echo   [ERR] Docker 未安装或未运行
    echo   [建议] 请安装并启动 Docker Desktop
    goto :end_check
)
echo   [OK] Docker 已安装

docker info >nul 2>&1
if errorlevel 1 (
    echo   [ERR] Docker 守护进程未运行
    echo   [建议] 请启动 Docker Desktop
    goto :end_check
)
echo   [OK] Docker 守护进程运行中
echo.

REM ========================================
REM 检查 2: TimescaleDB 容器状态
REM ========================================
echo [检查 2/6] TimescaleDB 容器状态
echo ----------------------------------------
docker-compose -f "%PROJECT_ROOT%\docker-compose.yml" ps timescaledb 2>&1 | findstr "Up" >nul
if errorlevel 1 (
    echo   [WARN] TimescaleDB 容器未运行
    echo   [INFO] 尝试启动容器...
    cd /d "%PROJECT_ROOT%"
    docker-compose up -d timescaledb
    timeout /t 5 /nobreak >nul
    
    docker-compose ps timescaledb 2>&1 | findstr "Up" >nul
    if errorlevel 1 (
        echo   [ERR] 容器启动失败
        echo   [建议] 查看日志: docker-compose logs timescaledb
        goto :end_check
    )
    echo   [OK] 容器已启动
) else (
    echo   [OK] TimescaleDB 容器运行中
)
echo.

REM ========================================
REM 检查 3: 端口监听状态
REM ========================================
echo [检查 3/6] 端口监听状态
echo ----------------------------------------
netstat -ano | findstr "0.0.0.0:%DB_PORT%" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo   [WARN] 端口 %DB_PORT% 未监听
    echo   [INFO] 等待数据库启动...
    timeout /t 10 /nobreak >nul
    
    netstat -ano | findstr "0.0.0.0:%DB_PORT%" | findstr "LISTENING" >nul
    if errorlevel 1 (
        echo   [ERR] 端口仍未监听
        echo   [建议] 检查容器日志: docker-compose logs timescaledb
        goto :end_check
    )
)
echo   [OK] 端口 %DB_PORT% 正在监听
echo.

REM ========================================
REM 检查 4: 数据库就绪状态
REM ========================================
echo [检查 4/6] 数据库就绪状态
echo ----------------------------------------
docker-compose -f "%PROJECT_ROOT%\docker-compose.yml" exec -T timescaledb pg_isready -U %DB_USER% -d %DB_NAME% >nul 2>&1
if errorlevel 1 (
    echo   [WARN] 数据库未就绪，等待中...
    
    set "READY=0"
    for /L %%i in (1,1,30) do (
        timeout /t 1 /nobreak >nul
        docker-compose -f "%PROJECT_ROOT%\docker-compose.yml" exec -T timescaledb pg_isready -U %DB_USER% -d %DB_NAME% >nul 2>&1
        if !errorlevel! equ 0 (
            set "READY=1"
            goto :ready_check
        )
        echo|set /p=.
    )
    echo.
    
    :ready_check
    if !READY! equ 0 (
        echo   [ERR] 数据库连接超时
        echo   [建议] 检查数据库日志: docker-compose logs timescaledb
        goto :end_check
    )
)
echo   [OK] 数据库已就绪
echo.

REM ========================================
REM 检查 5: 数据库连接测试
REM ========================================
echo [检查 5/6] 数据库连接测试
echo ----------------------------------------
docker-compose -f "%PROJECT_ROOT%\docker-compose.yml" exec -T timescaledb psql -U %DB_USER% -d %DB_NAME% -c "SELECT 1;" >nul 2>&1
if errorlevel 1 (
    echo   [ERR] 数据库连接失败
    echo   [建议] 检查用户名和密码是否正确
    goto :end_check
)
echo   [OK] 数据库连接成功
echo.

REM ========================================
REM 检查 6: 数据库表结构
REM ========================================
echo [检查 6/6] 数据库表结构
echo ----------------------------------------
docker-compose -f "%PROJECT_ROOT%\docker-compose.yml" exec -T timescaledb psql -U %DB_USER% -d %DB_NAME% -c "\dt" 2>nul
echo.

REM ========================================
REM 诊断总结
REM ========================================
:end_check
echo ========================================
echo  诊断完成
echo ========================================
echo.
echo 常见问题排查:
echo.
echo 1. 容器无法启动
echo    - 检查 Docker Desktop 是否运行
echo    - 检查端口 5432 是否被占用
echo    - 查看日志: docker-compose logs timescaledb
echo.
echo 2. 连接被拒绝
echo    - 等待数据库完全启动（约30秒）
echo    - 检查用户名密码: %DB_USER%/%DB_PASS%
echo    - 检查数据库名: %DB_NAME%
echo.
echo 3. 权限问题
echo    - 进入容器: docker-compose exec timescaledb bash
echo    - 切换用户: su - postgres
echo    - 检查权限: psql -c "\du"
echo.
echo 有用的命令:
echo   - 查看容器日志: docker-compose logs -f timescaledb
echo   - 重启容器: docker-compose restart timescaledb
echo   - 进入数据库: docker-compose exec timescaledb psql -U %DB_USER% -d %DB_NAME%
echo   - 查看表结构: docker-compose exec timescaledb psql -U %DB_USER% -d %DB_NAME% -c "\dt"
echo.

pause
