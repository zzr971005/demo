# 期货自动进化因子挖掘系统 - 后端

基于遗传编程的期货因子挖掘与自动交易系统后端。

## 快速开始

```bash
# 安装依赖
poetry install

# 启动服务
poetry run uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| 面板HTTP服务 | 8000 | FastAPI主服务，提供API和WebSocket |
| 进化引擎服务 | 8001 | 进化计算服务（可选，分离部署） |
| 执行网关服务 | 8002 | 交易执行网关（可选，分离部署） |

## 配置

### 环境变量配置

复制 `.env.example` 为 `.env` 并填写实际配置：

```bash
cp .env.example .env
```

### 关键配置项

- `DATABASE_URL`: PostgreSQL + TimescaleDB 数据库连接
- `REDIS_URL`: Redis 缓存服务连接
- `TQSDK_ACCOUNT`: 天勤量化账号（如需实盘交易）
- `TQSDK_PASSWORD`: 天勤量化密码（如需实盘交易）
- `APP_ENV`: 运行环境（development/production）

## 数据库

### 数据库架构

- **PostgreSQL + TimescaleDB**: 统一数据存储
  - 行情OHLCV数据（时序表）
  - 因子值（时序表）
  - 进化任务状态
  - 因子候选结果
  - 交易记录

### 数据库初始化

首次运行会自动创建表结构和超表。如需手动初始化：

```bash
poetry run python -c "from app.db import init_db; init_db()"
```

## 依赖管理

### 核心依赖
项目使用 [Poetry](https://python-poetry.org/) 管理所有 Python 依赖。

```bash
# 安装所有依赖
poetry install

# 安装可选依赖（如天勤SDK）
poetry install --extras "tq"

# 添加新依赖
poetry add <package_name>

# 更新依赖
poetry update
```

### 关键依赖说明

| 依赖 | 用途 | 备注 |
|------|------|------|
| pyarrow | K线数据缓存加速 | 可选，提升性能 |
| tqsdk | 天勤量化数据源 | 实盘交易需要 |
| timescaledb | 时序数据库 | 通过本地服务运行 |
| redis | 缓存服务 | 通过本地服务运行 |
| fastapi | Web框架 | API服务 |
| sqlalchemy | ORM | 数据库操作 |
| numpy/pandas | 数据处理 | 因子计算 |

## 脚本工具

### 数据管理脚本

位于 `scripts/` 目录：

- `check_evolution_tasks.py`: 检查进化任务状态
- `check_pipeline_data.py`: 检查验证流程数据
- `clear_old_tasks.py`: 清理旧任务
- `stop_evolution.py`: 停止运行中的进化任务

### 数据库迁移脚本

位于 `scripts/migration/` 目录：

- `add_cumulative_fields.py`: 添加累计字段
- `add_pipeline_fields_to_tasks.py`: 添加验证流程字段
- `remove_cumulative_fields.py`: 移除累计字段

## 测试

```bash
# 运行所有测试
poetry run pytest tests/ -v

# 运行特定测试
poetry run pytest tests/test_evolution.py -v
```

## 健康检查

服务启动后，可通过以下端点检查健康状态：

```bash
curl http://localhost:8000/health
```

返回示例：
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "database": true,
    "redis": true
  },
  "db_pool": {
    "pool_size": 10,
    "checked_in": 10,
    "checked_out": 0,
    "overflow": 0
  }
}
```

## 常见问题

### 数据库连接失败

1. 检查 PostgreSQL 服务是否运行
2. 检查 `.env` 中的 `DATABASE_URL` 配置
3. 检查数据库用户名密码是否正确

### Redis 连接失败

1. 检查 Redis 服务是否运行
2. 检查 `.env` 中的 `REDIS_URL` 配置

### 进化任务无响应

1. 检查进化线程池是否初始化
2. 查看日志中的错误信息
3. 使用 `scripts/stop_evolution.py` 停止卡住的任务
