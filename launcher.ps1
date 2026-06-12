﻿﻿#Requires -Version 5.1
# ============================================================
# 期货自动进化因子挖掘系统 - PowerShell 启动中心
# ============================================================

$Host.UI.RawUI.WindowTitle = "期货自动进化因子挖掘系统 - 启动中心"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 获取项目路径
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
# 如果脚本在项目根目录，直接使用；如果在子目录，返回父目录
if (Test-Path "$ScriptDir\backend") {
    $ProjectRoot = $ScriptDir
} else {
    $ProjectRoot = Resolve-Path "$ScriptDir\.."
}
$BackendPath = Join-Path $ProjectRoot "backend"
$FrontendPath = Join-Path $ProjectRoot "frontend"

function Show-Menu {
    Clear-Host
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  期货自动进化因子挖掘系统 - 启动中心" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "当前目录: $ScriptDir" -ForegroundColor Yellow
    Write-Host ""
    
    # 检查服务状态
    Write-Host "服务状态:" -ForegroundColor Cyan
    
    # 端口检查
    $ports = @(5432, 6379, 8000, 5173)
    $portNames = @("TimescaleDB", "Redis", "后端服务", "前端服务")
    for ($i = 0; $i -lt $ports.Count; $i++) {
        $port = $ports[$i]
        $name = $portNames[$i]
        try {
            $connection = Test-NetConnection -ComputerName localhost -Port $port -WarningAction SilentlyContinue
            if ($connection.TcpTestSucceeded) {
                Write-Host "  [OK] $name - 端口 $port 运行中" -ForegroundColor Green
            } else {
                Write-Host "  [  ] $name - 端口 $port 未启动" -ForegroundColor Gray
            }
        } catch {
            Write-Host "  [  ] $name - 端口 $port 未启动" -ForegroundColor Gray
        }
    }
    
    Write-Host ""
    Write-Host "请选择操作:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  [1] 增强版开发模式 (推荐)" -ForegroundColor White
    Write-Host "  [2] 启动基础设施 + 前后端" -ForegroundColor White
    Write-Host "  [3] 仅启动基础设施 (数据库 + Redis)" -ForegroundColor White
    Write-Host "  [4] 仅启动后端服务" -ForegroundColor White
    Write-Host "  [5] 仅启动前端服务" -ForegroundColor White
    Write-Host "  [6] 数据初始化 / 下载历史K线" -ForegroundColor Yellow
    Write-Host "  [7] 一键重启所有服务" -ForegroundColor White
    Write-Host "  [8] 停止所有服务" -ForegroundColor White
    Write-Host "  [9] 清理端口占用" -ForegroundColor White
    Write-Host "  [0] 退出" -ForegroundColor Red
    Write-Host ""
}

function Start-Infrastructure {
    Write-Host ""
    Write-Host "[INFO] 检查基础设施..." -ForegroundColor Yellow
    
    # 启动 PostgreSQL 服务
    $pgService = Get-Service -Name "postgresql-x64-17" -ErrorAction SilentlyContinue
    if ($pgService) {
        if ($pgService.Status -ne "Running") {
            Start-Service -Name "postgresql-x64-17" -ErrorAction SilentlyContinue
            Write-Host "  [OK] PostgreSQL 服务已启动" -ForegroundColor Green
        } else {
            Write-Host "  [OK] PostgreSQL 已在运行" -ForegroundColor Green
        }
    } else {
        Write-Host "  [WARN] PostgreSQL 服务未安装" -ForegroundColor Yellow
    }
    
    # 启动 Redis 服务
    $redisService = Get-Service -Name "redis" -ErrorAction SilentlyContinue
    if ($redisService) {
        if ($redisService.Status -ne "Running") {
            Start-Service -Name "redis" -ErrorAction SilentlyContinue
            Write-Host "  [OK] Redis 服务已启动" -ForegroundColor Green
        } else {
            Write-Host "  [OK] Redis 已在运行" -ForegroundColor Green
        }
    } else {
        Write-Host "  [WARN] Redis 服务未安装" -ForegroundColor Yellow
    }
    
    Write-Host "[SUCCESS] 基础设施检查完成" -ForegroundColor Green
    Start-Sleep -Seconds 1
}

function Start-Backend {
    Write-Host ""
    Write-Host "[INFO] 启动后端服务..." -ForegroundColor Yellow
    # 检查 Poetry 环境
    Set-Location $BackendPath
    $venvPath = & poetry env info --path 2>$null
    if (-not $venvPath) {
        Write-Host "[WARN] 虚拟环境不存在，正在创建..." -ForegroundColor Yellow
        & poetry install
    }
    
    $pythonPath = "$venvPath\Scripts\python.exe"
    $backendAbsolute = (Resolve-Path $BackendPath).Path
    
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "& '$pythonPath' -m app.main" -WorkingDirectory $backendAbsolute -WindowStyle Normal
    
    Write-Host "[SUCCESS] 后端服务已启动" -ForegroundColor Green
    Start-Sleep -Seconds 3
}

function Start-Frontend {
    Write-Host ""
    Write-Host "[INFO] 启动前端服务..." -ForegroundColor Yellow
    Write-Host "[DEBUG] 前端路径: $FrontendPath" -ForegroundColor Gray
    
    # 使用 WorkingDirectory 参数避免路径问题
    $frontendAbsolute = (Resolve-Path $FrontendPath).Path
    Write-Host "[DEBUG] 绝对路径: $frontendAbsolute" -ForegroundColor Gray
    
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "npm run dev" -WorkingDirectory $frontendAbsolute -WindowStyle Normal
    
    Write-Host "[SUCCESS] 前端服务已启动" -ForegroundColor Green
    Start-Sleep -Seconds 3
}

function Start-DataInit {
    Write-Host ""
    Write-Host "[INFO] 数据初始化工具" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "[1] 增量更新 (推荐)" -ForegroundColor Green
    Write-Host "[2] 全量初始化 (覆盖数据)" -ForegroundColor Red
    Write-Host "[3] 检查数据状态" -ForegroundColor White
    Write-Host "[0] 返回" -ForegroundColor Yellow
    Write-Host ""
    $choice = Read-Host "请选择"
    
    Set-Location $BackendPath
    $venvPath = & poetry env info --path 2>$null
    $pythonPath = "$venvPath\Scripts\python.exe"
    
    switch ($choice) {
        "1" {
            Write-Host "[INFO] 开始增量更新..." -ForegroundColor Yellow
            & $pythonPath -m app.init_data --incremental
        }
        "2" {
            Write-Host "[WARN] 将覆盖已有数据!" -ForegroundColor Red
            $confirm = Read-Host "确认? [yes/no]"
            if ($confirm -eq "yes") {
                & $pythonPath -m app.init_data --full --force
            }
        }
        "3" {
            & $pythonPath -m app.init_data --check
        }
    }
    Pause
}

function Stop-All {
    Write-Host ""
    Write-Host "[INFO] 停止所有服务..." -ForegroundColor Yellow
    
    # 停止本地进程
    $ports = @(8000, 5173)
    foreach ($port in $ports) {
        $result = netstat -ano | Select-String ":$port"
        if ($result) {
            $line = $result[0].ToString()
            $parts = $line -split '\s+'
            $pid = $parts[$parts.Length - 1]
            if ($pid) {
                Stop-Process -Id $pid -Force 2>$null
                Write-Host "[OK] 端口 $port 进程已停止" -ForegroundColor Green
            }
        }
    }
    Write-Host "[SUCCESS] 所有服务已停止" -ForegroundColor Green
    Pause
}

function Clear-Ports {
    Write-Host ""
    Write-Host "[INFO] 清理端口占用..." -ForegroundColor Yellow
    $ports = @(5432, 6379, 8000, 5173)
    foreach ($port in $ports) {
        $result = netstat -ano | Select-String ":$port"
        if ($result) {
            $line = $result[0].ToString()
            $parts = $line -split '\s+'
            $pid = $parts[$parts.Length - 1]
            if ($pid) {
                Stop-Process -Id $pid -Force 2>$null
                Write-Host "[OK] 端口 $port 已释放" -ForegroundColor Green
            }
        }
    }
    Write-Host "[SUCCESS] 端口清理完成" -ForegroundColor Green
    Pause
}

# 主循环
while ($true) {
    Show-Menu
    $choice = Read-Host "请输入选项 [0-9]"
    
    switch ($choice) {
        "1" {
            Start-Infrastructure
            Start-Backend
            Start-Frontend
        }
        "2" {
            Start-Infrastructure
            Start-Backend
            Start-Frontend
        }
        "3" { Start-Infrastructure }
        "4" { Start-Backend }
        "5" { Start-Frontend }
        "6" { Start-DataInit }
        "7" { Stop-All; Start-Sleep -Seconds 2; Start-Infrastructure; Start-Backend; Start-Frontend }
        "8" { Stop-All }
        "9" { Clear-Ports }
        "0" {
            Write-Host ""
            Write-Host "[INFO] 感谢使用，再见!" -ForegroundColor Cyan
            exit 0
        }
    }
}
