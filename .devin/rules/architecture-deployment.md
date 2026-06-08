# 服务架构与部署规则

> 基于 `.trae/rules/backtest-consistency.md` + `database-management.md` + `service-architecture.md` 精简合并
> 优先级：P1（重要规范）

## 1. 服务列表

| 服务 | 端口 | 说明 |
|------|------|------|
| 面板HTTP服务 | 8000 | 前端API、WebSocket |
| 进化引擎服务 | 8001 | 遗传编程、因子挖掘 |
| 执行网关服务 | 8002 | 下单、风控、对账 |
| 前端 | 5173 | React SPA |
| TimescaleDB | 5432 | 时序数据库 |
| Redis | 6379 | 缓存、消息队列 |

## 2. 启动顺序

```
1. 本地基础设施（PostgreSQL + Redis 本地服务）
2. 面板HTTP服务（8000）
3. 进化引擎服务（8001）
4. 执行网关服务（8002）
5. 前端（5173）
```

## 3. 通信方式

| 场景 | 方式 | 说明 |
|------|------|------|
| 前端 -> 后端 | HTTP + WebSocket | REST API + 实时推送 |
| 服务间 | HTTP | 内部API调用 |
| 异步任务 | Redis Pub/Sub | 事件总线 |
| 数据共享 | 数据库 | 统一数据源 |

## 4. 部署方式

### 4.1 本地服务模式（推荐）

```bash
# 确保 PostgreSQL 和 Redis 本地服务已启动
# 然后通过 bat 启动脚本启动前后端
bat启动文件夹\启动中心_增强版.bat
```

### 4.2 独立终端（开发调试）

```
IDE 终端面板:
|-- 标签页1: 进化引擎 (start_evolution.bat)     端口 8001
|-- 标签页2: 执行网关 (start_execution.bat)     端口 8002
|-- 标签页3: 面板HTTP (start_panel.bat)         端口 8000
|-- 标签页4: 前端 (start_frontend.bat)          端口 5173
```

## 5. 环境变量

```bash
# .env
TQSDK_ACCOUNT=your_account
TQSDK_PASSWORD=your_password
DB_URL=postgresql://user:pass@localhost:5432/quantdb
REDIS_URL=redis://localhost:6379
```

## 6. 健康检查

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "services": {
            "database": check_db(),
            "redis": check_redis(),
            "tqsdk": check_tqsdk()
        }
    }
```

## 7. 日志规范

```python
import logging

logger = logging.getLogger("quant_engine")
logger.info("策略启动", extra={"strategy_id": "S01", "symbol": "rb"})
logger.error("下单失败", extra={"order_id": "123", "error": "保证金不足"})
```

## 8. 监控指标

| 指标 | 类型 | 告警阈值 |
|------|------|---------|
| 请求延迟 | Gauge | >500ms |
| 错误率 | Counter | >1% |
| CPU使用率 | Gauge | >80% |
| 内存使用率 | Gauge | >85% |
| 数据库连接数 | Gauge | >90% |
| 进化进度 | Gauge | - |

## 9. 部署Checklist

- [ ] 所有服务健康检查通过
- [ ] 数据库连接正常
- [ ] TQSDK连接正常
- [ ] 前端可访问
- [ ] 日志正常输出
- [ ] 监控指标正常

## 10. 数据库管理

### 10.1 数据库清单

| 数据库 | 用途 | 服务 |
|--------|------|------|
| `timescaledb` | 历史行情OHLCV、因子值 | 所有服务（只读/读写） |
| `runtime.db` | 策略状态、候选、交易记录 | 主服务、进化服务 |
| `backtest.db` | 回测结果 | 回测服务 |

### 10.2 迁移脚本

- 命名：`migrate_v{源版本}_to_v{目标版本}.py`
- 必须包含：备份逻辑、事务处理、验证逻辑、回滚逻辑
- 流程：备份 -> 执行迁移 -> 验证 -> 回滚（失败时）

### 10.3 数据模型

- 版本命名：`models_v1.py`, `models_v2.py`
- 必须字段：`id` (主键), `created_at`, `updated_at`
- 版本表：`SchemaVersion` (version, applied_at, description)

### 10.4 字段命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 主键 | `id` | `id` |
| 外键 | `{表}_id` | `candidate_id` |
| 时间戳 | `{动作}_at` | `created_at` |
| 布尔值 | `is_{描述}` | `is_active` |
| 状态 | `status` | `status` |
| 价格 | `{描述}_price` | `open_price` |
| 数量 | `{描述}_volume` | `trade_volume` |

### 10.5 数据访问

- 使用 DAO 模式
- 事务用上下文管理器
- 批量操作用 `bulk_save_objects`

### 10.6 备份策略

- 每日自动备份（保留7天）
- 每周备份（保留4周）
- 每月备份（保留12个月）
- 迁移前手动备份（永久保留）

### 10.7 性能优化

- 常用查询字段加索引
- 批量插入代替逐条
- 小表（<1000行）不加索引
- TimescaleDB hypertable 按时间和品种分区

### 10.8 变更Checklist

- [ ] 需求明确，变更已评审
- [ ] 迁移脚本已编写并自测
- [ ] 回滚脚本已准备
- [ ] 数据库已备份
- [ ] 迁移已验证
- [ ] 应用功能已测试

## 11. 回测与实盘一致性

### 11.1 一致性目标

- 收益偏差 < 10%
- 回撤偏差 < 20%
- 交易次数偏差 < 15%
- 胜率偏差 < 10%

### 11.2 回测参数

| 参数 | 值 | 说明 |
|------|-----|--------|
| 手续费 | 0.0001 | 万分之一 |
| 滑点 | 0.0002 | 万分之二 |
| 保证金比例 | 0.12 | 12% |
| 价格跳动 | 1 | 最小变动价位 |
| 合约乘数 | 10 | 每点10元 |

### 11.3 滑点模型

```python
class SlippageModel:
    def calculate(self, symbol, volume, direction):
        base = 0.00015  # 平均滑点
        volume_factor = min(volume / 10, 2.0)
        return base * volume_factor
```

### 11.4 成交模拟

- 检查交易时间
- 检查涨跌停
- 应用滑点
- 计算手续费和保证金
- IF 禁止 CLOSE_TODAY

### 11.5 一致性验证

验证流程：回测 -> 向量化回测 -> 天勤桥接验证 -> 模拟验证（>=2周）-> 对比分析 -> 实盘

通过标准：
- 回测与向量化差异 < 3%
- 回测与天勤差异 < 5%
- 回测与模拟差异 < 10%
- 或一致性评分 > 0.9

### 11.6 统计检验

- **PBO（回测过拟合概率）**: 使用 CSCV，PBO < 0.3 视为通过
- **DSR（放气夏普比率）**: DSR > 0.6 视为通过
- **BH-FDR**: p(i) <= (i/m) * Q
- **Walk-Forward 效率**: WFE = 验证窗口夏普 / 训练窗口夏普，WFE > 0.7 视为通过

### 11.7 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 收益偏差大 | 滑点设置低 | 调整滑点模型 |
| 交易次数偏差 | 信号触发不一致 | 统一信号逻辑 |
| 回撤偏差 | 止损执行延迟 | 模拟滑点延迟 |
| 向量化与天勤差异大 | 成交逻辑不一致 | 检查开平方向和手续费 |

### 11.8 持续改进

- 定期校准参数（基于实盘数据）
- 记录参数变更历史
- 分析偏差原因并优化
- 更新 PBO/DSR 基准

### 11.9 违规后果

一致性偏差 >30% 禁止实盘，未经验证报告将被拒绝，故意美化回测将被记录。
