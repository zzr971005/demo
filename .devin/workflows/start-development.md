---
description: 日常开发启动流程
---

# 日常开发启动流程

## 1. 确认本地基础设施已启动

```powershell
# 确认 PostgreSQL 服务已运行
Get-Service postgresql* | Select-Object Name, Status

# 确认 Redis 服务已运行
redis-cli ping
```

## 2. 启动后端服务

在 IDE 终端面板中创建独立标签页运行：

```powershell
# 标签页1：面板HTTP服务
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 标签页2：进化引擎（如需独立调试）
cd backend
poetry run python -m quant_engine.ops.evolution_center

# 标签页3：执行网关（如需独立调试）
cd backend
poetry run python -m quant_engine.runtime.execution_gateway
```

## 3. 启动前端

```powershell
cd frontend
npm run dev
```

## 4. 验证服务状态

```powershell
Invoke-RestMethod -Uri http://localhost:8000/health -Method GET
```

## 5. 停止服务

```powershell
# 在各终端标签页按 Ctrl+C 停止后端和前端进程
```
