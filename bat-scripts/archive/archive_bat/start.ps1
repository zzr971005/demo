#Requires -Version 5.1
# ============================================================
# 期货自动进化因子挖掘系统 - PowerShell 启动脚本
# ============================================================

$Host.UI.RawUI.WindowTitle = "期货自动进化因子挖掘系统 - 启动控制台"

function Show-Header {
    Write-Host ""
    Write-Host "  ╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "  ║     期货自动进化因子挖掘系统 - 启动控制台                 ║" -ForegroundColor Cyan
    Write-Host "  ╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

function Test-Docker {
    try {
        $dockerVersion = docker --version 2>$null
        if ($LASTEXITCODE -ne 0) { return $false }
        Write-Host "[INFO] Docker 版本: $dockerVersion" -ForegroundColor Green
        return $true
    } catch {
        return $false
    }
}

function Test-DockerCompose {
    try {
        $composeVersion = docker-compose --version 2>$null
        if ($LASTEXITCODE -ne 0) { return $false }
        Write-Host "[INFO] Docker Compose 版本: $composeVersion" -ForegroundColor Green
        return $true
    } catch {
        return $false
    }
}

function Start-FullSystem {
    Write-Host ""
    Write-Host "[INFO] 正在启动完整系统..." -ForegroundColor Yellow
    Write-Host "[INFO] 服务列表: TimescaleDB + Redis + Backend + Frontend" -ForegroundColor Yellow
    Write-Host ""

    # 检查 .env 文件
    if (-not (Test-Path ".env")) {
        Write-Host "[WARN] .env 文件不存在，正在从模板创建..." -ForegroundColor Yellow
        Copy-Item backend\.env.example .env -ErrorAction SilentlyContinue
        Write-Host "[INFO] 请编辑 .env 文件配置天勤账号等信息" -ForegroundColor Cyan
        Write-Host ""
    }

    # 构建并启动
    docker-compose up -d --build
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] 启动失败" -ForegroundColor Red
        pause
        return
    }

    Write-Host ""
    Write-Host "[SUCCESS] 系统启动成功!" -ForegroundColor Green
    Write-Host ""
    Write-Host "访问地址:" -ForegroundColor Cyan
    Write-Host "  前端界面: http://localhost" -ForegroundColor White
    Write-Host "  后端 API: http://localhost:8000" -ForegroundColor White
    Write-Host "  API 文档: http://localhost:8000/docs" -ForegroundColor White
    Write-Host "  健康检查: http://localhost:8000/health" -ForegroundColor White
    Write-Host ""
    pause
}

function Start-Infrastructure {
    Write-Host ""
    Write-Host "[INFO] 正在启动基础设施 (TimescaleDB + Redis)..." -ForegroundColor Yellow
    docker-compose up -d timescaledb redis
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] 启动失败" -ForegroundColor Red
        pause
        return
    }
    Write-Host "[SUCCESS] 基础设施已启动" -ForegroundColor Green
    Write-Host "[INFO] 可以手动启动后端和前端进行开发" -ForegroundColor Cyan
    Write-Host ""
    pause
}

function Stop-AllServices {
    Write-Host ""
    Write-Host "[INFO] 正在停止所有服务..." -ForegroundColor Yellow
    docker-compose down
    Write-Host "[SUCCESS] 所有服务已停止" -ForegroundColor Green
    Write-Host ""
    pause
}

function Restart-Services {
    Write-Host ""
    Write-Host "[INFO] 正在重启服务..." -ForegroundColor Yellow
    docker-compose restart
    Write-Host "[SUCCESS] 服务已重启" -ForegroundColor Green
    Write-Host ""
    pause
}

function Show-Status {
    Write-Host ""
    Write-Host "[INFO] 服务状态:" -ForegroundColor Cyan
    docker-compose ps
    Write-Host ""
    pause
}

function Show-Logs {
    Write-Host ""
    Write-Host "选择要查看日志的服务:" -ForegroundColor Cyan
    Write-Host "  [1] 后端 (backend)" -ForegroundColor White
    Write-Host "  [2] 前端 (frontend)" -ForegroundColor White
    Write-Host "  [3] 数据库 (timescaledb)" -ForegroundColor White
    Write-Host "  [4] Redis" -ForegroundColor White
    Write-Host "  [5] 所有服务" -ForegroundColor White
    Write-Host "  [0] 返回" -ForegroundColor White
    Write-Host ""
    $logChoice = Read-Host "请输入选项"

    switch ($logChoice) {
        "1" { docker-compose logs -f backend }
        "2" { docker-compose logs -f frontend }
        "3" { docker-compose logs -f timescaledb }
        "4" { docker-compose logs -f redis }
        "5" { docker-compose logs -f }
        "0" { return }
    }
}

function Clear-AllData {
    Write-Host ""
    Write-Host "[WARN] 这将删除所有数据卷，包括数据库数据!" -ForegroundColor Red
    $confirm = Read-Host "确认清理? [yes/no]"
    if ($confirm -ne "yes") { return }

    Write-Host "[INFO] 正在清理..." -ForegroundColor Yellow
    docker-compose down -v
    docker system prune -f
    Write-Host "[SUCCESS] 清理完成" -ForegroundColor Green
    Write-Host ""
    pause
}

function Enter-BackendContainer {
    Write-Host ""
    Write-Host "[INFO] 进入后端容器..." -ForegroundColor Cyan
    docker-compose exec backend bash
}

function Enter-Database {
    Write-Host ""
    Write-Host "[INFO] 进入数据库..." -ForegroundColor Cyan
    docker-compose exec timescaledb psql -U qmt -d quant_db
}

# ============================================================
# 主程序
# ============================================================

Show-Header

# 检查 Docker
if (-not (Test-Docker)) {
    Write-Host "[ERROR] Docker 未安装或未启动，请先安装 Docker Desktop" -ForegroundColor Red
    Write-Host "下载地址: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    pause
    exit 1
}

if (-not (Test-DockerCompose)) {
    Write-Host "[ERROR] Docker Compose 未安装" -ForegroundColor Red
    pause
    exit 1
}

Write-Host ""

# 主循环
while ($true) {
    Show-Header

    Write-Host "请选择启动模式:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  [1] 完整启动 (Docker Compose - 推荐)" -ForegroundColor White
    Write-Host "  [2] 仅启动基础设施 (TimescaleDB + Redis)" -ForegroundColor White
    Write-Host "  [3] 停止所有服务" -ForegroundColor White
    Write-Host "  [4] 重启服务" -ForegroundColor White
    Write-Host "  [5] 查看服务状态" -ForegroundColor White
    Write-Host "  [6] 查看日志" -ForegroundColor White
    Write-Host "  [7] 完全清理 (删除数据卷)" -ForegroundColor Red
    Write-Host "  [8] 进入后端容器" -ForegroundColor White
    Write-Host "  [9] 进入数据库" -ForegroundColor White
    Write-Host "  [0] 退出" -ForegroundColor Yellow
    Write-Host ""

    $choice = Read-Host "请输入选项 [0-9]"

    switch ($choice) {
        "1" { Start-FullSystem }
        "2" { Start-Infrastructure }
        "3" { Stop-AllServices }
        "4" { Restart-Services }
        "5" { Show-Status }
        "6" { Show-Logs }
        "7" { Clear-AllData }
        "8" { Enter-BackendContainer }
        "9" { Enter-Database }
        "0" {
            Write-Host ""
            Write-Host "[INFO] 退出启动脚本" -ForegroundColor Cyan
            Write-Host ""
            exit 0
        }
        default {
            Write-Host "[ERROR] 无效选项" -ForegroundColor Red
            pause
        }
    }
}
