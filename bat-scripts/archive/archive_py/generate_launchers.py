# -*- coding: utf-8 -*-
"""
批处理文件生成器 - 解决编码兼容性问题
"""

# GBK 版本的批处理文件内容
bat_content = '''@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM 启动中心 - 期货自动进化因子挖掘系统 v2.1
REM ============================================================

chcp 936 >nul 2>&1

title 启动中心 - 期货自动进化因子挖掘系统
mode con: cols=90 lines=40

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:menu
cls
echo.
echo  ========================================
echo  启动中心 - 期货自动进化因子挖掘系统 v2.1
echo  ========================================
echo.
echo  当前目录: %SCRIPT_DIR%
echo.

REM 显示当前服务状态
echo  [当前服务状态]
call "%SCRIPT_DIR%\\check-service.bat" all
echo.

echo  快速启动:
echo    [1] 增强版开发模式
echo    [2] 基础开发模式
echo    [3] Docker 完整模式
echo.
echo  单一服务启动:
echo    [4] 仅启动基础设施
echo    [5] 仅启动后端服务
echo    [6] 仅启动前端服务
echo.
echo  数据管理工具:
echo    [7] 数据初始化
echo    [8] 检查服务状态
echo.
echo  工具与维护:
echo    [9] 一键重启所有服务
echo    [10] 停止所有服务
echo    [11] 清理端口占用
echo    [12] 检查数据库状态
echo.
echo  帮助:
echo    [13] 查看使用说明
echo    [0] 退出
echo.

set /p choice=请选择选项 [0-13]:

set choice=%choice%
set choice=%choice: =%

if "%choice%"=="0" goto :exit
if "%choice%"=="1" goto :dev_pro
if "%choice%"=="2" goto :dev_basic
if "%choice%"=="3" goto :docker_mode
if "%choice%"=="4" goto :infra_only
if "%choice%"=="5" goto :backend_only
if "%choice%"=="6" goto :frontend_only
if "%choice%"=="7" goto :init_data
if "%choice%"=="8" goto :check_status
if "%choice%"=="9" goto :restart
if "%choice%"=="10" goto :stop_all
if "%choice%"=="11" goto :clean_ports
if "%choice%"=="12" goto :check_db
if "%choice%"=="13" goto :readme

echo [ERR] 无效选项，请重新选择
timeout /t 2 /nobreak >nul
goto :menu

:dev_pro
echo [INFO] 启动增强版开发模式...
call "%SCRIPT_DIR%\\start-dev-pro.bat"
goto :menu

:dev_basic
echo [INFO] 启动基础开发模式...
call "%SCRIPT_DIR%\\start-dev.bat"
goto :menu

:docker_mode
echo [INFO] 启动 Docker 完整模式...
call "%SCRIPT_DIR%\\start.bat"
goto :menu

:infra_only
echo [INFO] 仅启动基础设施...
cd /d "%SCRIPT_DIR%.."
docker-compose up -d timescaledb redis
echo [SUCCESS] 基础设施已启动
echo 访问地址:
echo   - TimescaleDB: localhost:5432
echo   - Redis: localhost:6379
pause
goto :menu

:backend_only
echo [INFO] 仅启动后端服务...
call "%SCRIPT_DIR%\\start-backend-only.bat"
goto :menu

:frontend_only
echo [INFO] 仅启动前端服务...
call "%SCRIPT_DIR%\\start-frontend-only.bat"
goto :menu

:init_data
echo [INFO] 数据初始化工具...
call "%SCRIPT_DIR%\\init-data.bat"
goto :menu

:check_status
echo [INFO] 检查服务状态...
call "%SCRIPT_DIR%\\check-status.bat"
echo 按任意键返回菜单...
pause >nul
goto :menu

:check_db
echo [INFO] 检查数据库状态...
call "%SCRIPT_DIR%\\检查数据库状态.bat"
goto :menu

:restart
echo [INFO] 一键重启所有服务...
call "%SCRIPT_DIR%\\restart-all.bat"
goto :menu

:stop_all
echo [INFO] 停止所有服务...
call "%SCRIPT_DIR%\\stop-all.bat"
goto :menu

:clean_ports
echo [INFO] 清理端口占用...
call "%SCRIPT_DIR%\\clean-ports.bat"
echo 按任意键返回菜单...
pause >nul
goto :menu

:readme
echo [INFO] 查看使用说明文档...
if exist "%SCRIPT_DIR%\\README-zh.md" (
    start "" "%SCRIPT_DIR%\\README-zh.md"
    echo [OK] 文档已打开
) else (
    echo [ERR] 文档文件不存在
)
timeout /t 2 /nobreak >nul
goto :menu

:exit
echo ========================================
echo  感谢使用，再见!
echo ========================================
timeout /t 1 /nobreak >nul
exit /b 0
'''

# UTF-8 版本的 PowerShell 脚本内容
ps1_content = '''<#
.SYNOPSIS
期货自动进化因子挖掘系统 - PowerShell 启动器

.DESCRIPTION
用于在 PowerShell 环境中启动系统
#>

# 设置代码页为 UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 启动目录
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptDir

:menu
Clear-Host
Write-Host ""
Write-Host " ======================================== " -ForegroundColor Cyan
Write-Host " 启动中心 - 期货自动进化因子挖掘系统 v2.1 " -ForegroundColor Cyan
Write-Host " ======================================== " -ForegroundColor Cyan
Write-Host ""
Write-Host " 当前目录: $scriptDir"
Write-Host ""

# 检查服务状态
Write-Host " [当前服务状态]" -ForegroundColor Yellow
& "$scriptDir\\check-service.bat" all
Write-Host ""

Write-Host " 快速启动:" -ForegroundColor Green
Write-Host "    [1] 增强版开发模式"
Write-Host "    [2] 基础开发模式"
Write-Host "    [3] Docker 完整模式"
Write-Host ""
Write-Host " 单一服务启动:" -ForegroundColor Green
Write-Host "    [4] 仅启动基础设施"
Write-Host "    [5] 仅启动后端服务"
Write-Host "    [6] 仅启动前端服务"
Write-Host ""
Write-Host " 数据管理工具:" -ForegroundColor Green
Write-Host "    [7] 数据初始化"
Write-Host "    [8] 检查服务状态"
Write-Host ""
Write-Host " 工具与维护:" -ForegroundColor Green
Write-Host "    [9] 一键重启所有服务"
Write-Host "    [10] 停止所有服务"
Write-Host "    [11] 清理端口占用"
Write-Host "    [12] 检查数据库状态"
Write-Host ""
Write-Host " 帮助:" -ForegroundColor Green
Write-Host "    [13] 查看使用说明"
Write-Host "    [0] 退出"
Write-Host ""

$choice = Read-Host "请选择选项 [0-13]"

switch ($choice) {
    "0" { Write-Host "感谢使用，再见!"; exit }
    "1" { Write-Host "启动增强版开发模式..."; & "$scriptDir\\start-dev-pro.bat" }
    "2" { Write-Host "启动基础开发模式..."; & "$scriptDir\\start-dev.bat" }
    "3" { Write-Host "启动 Docker 完整模式..."; & "$scriptDir\\start.bat" }
    "4" { 
        Write-Host "仅启动基础设施..."
        Set-Location (Split-Path $scriptDir)
        docker-compose up -d timescaledb redis
        Write-Host "基础设施已启动"
        Read-Host "按回车继续"
    }
    "5" { Write-Host "仅启动后端服务..."; & "$scriptDir\\start-backend-only.bat" }
    "6" { Write-Host "仅启动前端服务..."; & "$scriptDir\\start-frontend-only.bat" }
    "7" { Write-Host "数据初始化工具..."; & "$scriptDir\\init-data.bat" }
    "8" { Write-Host "检查服务状态..."; & "$scriptDir\\check-status.bat"; Read-Host "按回车继续" }
    "9" { Write-Host "一键重启所有服务..."; & "$scriptDir\\restart-all.bat" }
    "10" { Write-Host "停止所有服务..."; & "$scriptDir\\stop-all.bat" }
    "11" { Write-Host "清理端口占用..."; & "$scriptDir\\clean-ports.bat"; Read-Host "按回车继续" }
    "12" { Write-Host "检查数据库状态..."; & "$scriptDir\\检查数据库状态.bat" }
    "13" { 
        Write-Host "查看使用说明文档..."
        if (Test-Path "$scriptDir\\README-zh.md") {
            Start-Process "$scriptDir\\README-zh.md"
            Write-Host "文档已打开"
        } else {
            Write-Host "文档文件不存在" -ForegroundColor Red
        }
        Start-Sleep -Seconds 2
    }
    default { Write-Host "无效选项，请重新选择" -ForegroundColor Red; Start-Sleep -Seconds 2 }
}

goto menu
'''

# 写入文件
with open('启动中心.bat', 'w', encoding='gbk') as f:
    f.write(bat_content)
print('启动中心.bat (GBK) 已创建 - 用于双击打开')

with open('启动中心.ps1', 'w', encoding='utf-8') as f:
    f.write(ps1_content)
print('启动中心.ps1 (UTF-8) 已创建 - 用于 PowerShell')