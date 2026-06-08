<#
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
& "$scriptDir\check-service.bat" all
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
    "1" { Write-Host "启动增强版开发模式..."; & "$scriptDir\start-dev-pro.bat" }
    "2" { Write-Host "启动基础开发模式..."; & "$scriptDir\start-dev.bat" }
    "3" { Write-Host "启动 Docker 完整模式..."; & "$scriptDir\start.bat" }
    "4" { 
        Write-Host "仅启动基础设施..."
        Set-Location (Split-Path $scriptDir)
        docker-compose up -d timescaledb redis
        Write-Host "基础设施已启动"
        Read-Host "按回车继续"
    }
    "5" { Write-Host "仅启动后端服务..."; & "$scriptDir\start-backend-only.bat" }
    "6" { Write-Host "仅启动前端服务..."; & "$scriptDir\start-frontend-only.bat" }
    "7" { Write-Host "数据初始化工具..."; & "$scriptDir\init-data.bat" }
    "8" { Write-Host "检查服务状态..."; & "$scriptDir\check-status.bat"; Read-Host "按回车继续" }
    "9" { Write-Host "一键重启所有服务..."; & "$scriptDir\restart-all.bat" }
    "10" { Write-Host "停止所有服务..."; & "$scriptDir\stop-all.bat" }
    "11" { Write-Host "清理端口占用..."; & "$scriptDir\clean-ports.bat"; Read-Host "按回车继续" }
    "12" { Write-Host "检查数据库状态..."; & "$scriptDir\检查数据库状态.bat" }
    "13" { 
        Write-Host "查看使用说明文档..."
        if (Test-Path "$scriptDir\README-zh.md") {
            Start-Process "$scriptDir\README-zh.md"
            Write-Host "文档已打开"
        } else {
            Write-Host "文档文件不存在" -ForegroundColor Red
        }
        Start-Sleep -Seconds 2
    }
    default { Write-Host "无效选项，请重新选择" -ForegroundColor Red; Start-Sleep -Seconds 2 }
}

goto menu
