# 期货自动进化因子挖掘系统 - 数据架构与治理方案

## 一、当前数据架构分析

### 1.1 数据库清单

| 数据库类型 | 用途 | 配置项 | 现状评估 |
|-----------|------|--------|----------|
| **PostgreSQL + TimescaleDB** | 统一数据存储（时序数据 + 业务数据） | `DATABASE_URL` | ✅ 合理 |
| **Redis** | 缓存与实时消息 | `REDIS_URL` | ✅ 明确 |

### 1.2 数据分布现状

```
┌─────────────────────────────────────────────────────────────────┐
│                      数据架构全景图                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────┐      │
│  │              PostgreSQL + TimescaleDB                │      │
│  │                    (统一数据存储)                     │      │
│  ├──────────────────────────────────────────────────────┤      │
│  │ • 时序数据：ohlcv_1m/h/d, factor_values              │      │
│  │ • 业务数据：candidates, trades, evolution_*          │      │
│  │ • 风控数据：risk_events, symbol_switches             │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                 │
│  ┌──────────────────────┐                                       │
│  │       Redis          │                                       │
│  │  (缓存/消息)         │                                       │
│  ├──────────────────────┤                                       │
│  │ • 实时数据缓存       │                                       │
│  │ • WebSocket消息转发  │                                       │
│  └──────────────────────┘                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 当前架构优势

| 特性 | 说明 |
|------|------|
| 统一存储 | 所有数据在同一个 PostgreSQL 数据库中，事务一致性有保障 |
| TimescaleDB 扩展 | 专业处理时序数据，支持超表、压缩、连续聚合等特性 |
| 简化架构 | 只需维护一个数据库，降低运维复杂度 |

---

## 二、数据架构治理方案

### 2.1 目标

1. **统一数据访问**：通过 `DataHub` 统一访问所有数据
2. **明确职责边界**：清晰划分数据库的职责
3. **简化架构**：保持架构简洁高效
4. **可维护性提升**：统一schema管理、迁移机制

### 2.2 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                    优化后数据架构                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                      应用层 (Application Layer)                 │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │ 进化引擎│ │ 回测引擎│ │ 风控模块│ │ 执行模块│ │ 策略管理│   │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘   │
│       │           │           │           │           │        │
│       └───────────┴────┬──────┴───────────┴───────────┘        │
│                        │                                       │
│              ┌─────────▼─────────┐                             │
│              │     DataHub       │  ← 统一数据访问层            │
│              │  (数据访问门面)    │                             │
│              └─────────┬─────────┘                             │
│                        │                                       │
│         ┌──────────────┼──────────────┐                        │
│         ▼              ▼              ▼                        │
│  ┌─────────────────────────────┐  ┌────────────┐               │
│  │  PostgreSQL + TimescaleDB   │  │   Redis    │               │
│  │       (统一数据存储)         │  │  (缓存)    │               │
│  ├─────────────────────────────┤  └────────────┘               │
│  │ • 时序数据：ohlcv_*, factors │  • 实时数据                  │
│  │ • 业务数据：candidates, trades│ • 会话状态                  │
│  │ • 进化数据：evolution_*      │                               │
│  │ • 风控数据：risk_events      │                               │
│  └─────────────────────────────┘                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 数据库职责划分

| 数据库 | 职责 | 存储内容 |
|--------|------|----------|
| **PostgreSQL + TimescaleDB** | 统一数据存储 | 时序数据（OHLCV、因子值）+ 业务数据（候选策略、交易记录、进化世代、风控事件、品种开关） |
| **Redis** | 缓存 | 实时行情快照、会话状态、高频临时数据 |

### 2.4 治理措施

#### 措施1：统一数据访问层

**目标**：统一数据访问入口

**实施要点**：

1. **增强 `DataHub`**：扩展 `TimescaleHub` 处理所有数据
2. **统一接口**：所有数据访问通过 `DataHub` 进行

**代码示例**：
```python
# 统一数据访问入口
class DataHub:
    def __init__(self):
        self.db = TimescaleHub()  # 统一数据库访问
        self.redis = RedisClient()  # 缓存
    
    # 统一接口
    def get_ohlcv(self, ...):
        return self.db.get_ohlcv(...)
    
    def save_candidate(self, ...):
        return self.db.save_candidate(...)
    
    def cache_factor(self, ...):
        return self.redis.set(...)
```

#### 措施2：Schema管理规范

**统一Schema定义**：

1. **使用SQLAlchemy模型**：所有表结构通过ORM模型定义
2. **版本化管理**：使用Alembic进行迁移管理
3. **文档化**：每个表需有字段说明文档

**模型示例**：
```python
# models/candidate.py
class Candidate(Base):
    """候选策略模型"""
    __tablename__ = "candidates"
    
    id = Column(String(64), primary_key=True)
    symbol = Column(String(16), nullable=False, index=True)
    status = Column(String(16), default="SEED", index=True)
    formula = Column(Text, nullable=False)
    sharpe_train = Column(Float)
    max_drawdown = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
```

#### 措施3：Redis使用规范

**明确使用场景**：

| 使用场景 | 说明 | 数据生命周期 |
|----------|------|--------------|
| 实时行情缓存 | T+0 K线数据 | 1小时 |
| 会话状态 | 用户登录状态 | 会话期间 |
| WebSocket消息队列 | 实时推送 | 即时消费 |
| 计算结果缓存 | 高频查询结果 | 5分钟 |

**禁止使用场景**：
- ❌ 持久化业务数据
- ❌ 交易记录存储
- ❌ 策略状态存储

#### 措施4：监控与运维

**监控指标**：

| 指标 | 监控目标 | 告警阈值 |
|------|----------|----------|
| 数据库连接数 | 连接池状态 | >80% |
| 查询响应时间 | 慢查询 | >100ms |
| 存储空间 | 磁盘使用 | >80% |
| 数据同步延迟 | 主从同步 | >1s |

**备份策略**：

| 数据库 | 备份频率 | 保留周期 |
|--------|----------|----------|
| PostgreSQL | 每日全量 + 每小时增量 | 7天全量 + 30天增量 |
| Redis | 每日RDB | 7天 |

---

## 三、实施路线图

### 3.1 短期（1-2周）

| 任务 | 描述 |
|------|------|
| 1 | 增强DataHub，统一所有数据访问 |
| 2 | 创建统一的SQLAlchemy模型 |
| 3 | 编写数据库初始化脚本 |

### 3.2 中期（3-4周）

| 任务 | 描述 |
|------|------|
| 1 | 更新所有模块使用统一DataHub |
| 2 | 添加数据库迁移机制（Alembic） |
| 3 | 完善监控告警体系 |

### 3.3 长期（1-2月）

| 任务 | 描述 |
|------|------|
| 1 | 实施Redis使用规范 |
| 2 | 建立完善的备份与恢复流程 |
| 3 | 完善文档和培训 |

---

## 四、预期收益

| 维度 | 改进前 | 改进后 |
|------|--------|--------|
| **架构复杂度** | 多种数据库 | 单一数据库 + Redis缓存 |
| **部署难度** | 需要配置多种数据库 | 主要配置PostgreSQL |
| **数据一致性** | 事务保障统一 | PostgreSQL事务支持 |
| **开发体验** | 需要熟悉多种API | 统一API |

---

## 五、风险评估

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| 数据迁移问题 | 低 | 高 | 迁移前备份、验证 |
| 代码改动引入bug | 中 | 中 | 单元测试、回归测试 |
| 性能下降 | 低 | 中 | 索引优化、查询优化 |
| Redis依赖问题 | 低 | 低 | 设置合理超时、降级方案 |

---

## 六、CSV备份与恢复策略

### 6.1 目标与设计原则

**目标**：
1. 建立数据库与CSV的双备份机制
2. 确保每次数据库更新后CSV同步备份
3. 支持从CSV快速恢复数据
4. 支持增量更新，减少恢复时间

**设计原则**：
- **同步备份**：数据库每次更新 → 立即写入CSV
- **分区存储**：按品种+频率组织CSV文件
- **增量更新**：恢复后可快速补齐缺失数据
- **版本兼容**：支持Schema演进
- **数据范围**：全量初始化下载**2年**历史数据，满足Walk-Forward回测验证需求

### 6.2 CSV备份目录结构

```
data_backup/
├── ohlcv/
│   ├── 1h/
│   │   ├── SHFE.rb.csv
│   │   ├── SHFE.cu.csv
│   │   └── ... (12个品种)
│   ├── 1d/
│   │   └── ...
│   └── 1m/
│       └── ...
├── factors/
│   └── ...
└── metadata.json
```

### 6.3 CSV格式规范

**OHLCV数据CSV格式**：

| 列名 | 类型 | 说明 |
|------|------|------|
| `symbol` | String | 品种代码 |
| `datetime` | DateTime | 时间戳 |
| `open` | Float | 开盘价 |
| `high` | Float | 最高价 |
| `low` | Float | 最低价 |
| `close` | Float | 收盘价 |
| `volume` | Float | 成交量 |
| `open_oi` | Float | 开盘持仓 |
| `close_oi` | Float | 收盘持仓 |

**CSV文件示例**：
```csv
symbol,datetime,open,high,low,close,volume,open_oi,close_oi
SHFE.rb,2026-01-01 09:00:00,3500,3520,3490,3510,15000,100000,105000
SHFE.rb,2026-01-01 10:00:00,3510,3530,3505,3525,18000,105000,108000
```

### 6.4 自动备份触发机制

```
┌─────────────────────────────────────────────────────────────┐
│                  数据更新与备份流程                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  TQSDK获取   │ →  │  写入数据库  │ →  │  写入CSV备份 │  │
│  │  最新数据    │    │ (PostgreSQL) │    │   (同步)     │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                              │
│  触发点：                                                    │
│  • 数据初始化（首次下载）                                    │
│  • 每日增量更新                                              │
│  • 手动数据刷新                                              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 6.5 备份与恢复API设计

```python
class DataBackup:
    """数据备份管理类"""
    
    def __init__(self, backup_root: str = "data_backup"):
        self.backup_root = Path(backup_root)
        
    def backup_ohlcv(self, symbol: str, freq: str, df: pd.DataFrame):
        """备份OHLCV数据到CSV"""
        pass
        
    def restore_ohlcv(self, symbol: str, freq: str) -> pd.DataFrame:
        """从CSV恢复OHLCV数据"""
        pass
        
    def check_backup_status(self) -> dict:
        """检查备份状态（数据库 vs CSV）"""
        pass
        
    def get_backup_metadata(self) -> dict:
        """获取备份元数据"""
        pass
```

### 6.6 检查与恢复流程

```
启动中心 → [5] 检查数据备份状态
    ↓
检查数据库记录数 vs CSV记录数
    ↓
    ├─ 数据库为空 → 显示"从CSV恢复"选项
    ├─ 数据库 < CSV × 0.9 → 显示"从CSV恢复"选项
    └─ 数据一致 → 显示"数据状态正常"
        ↓
    恢复完成 → 进行增量更新（补齐最新数据）
```

### 6.7 元数据管理（metadata.json）

```json
{
  "last_backup_time": "2026-05-23T20:00:00",
  "total_records": 36500,
  "symbols": {
    "SHFE.rb": {
      "1h": {"records": 3000, "last_datetime": "2026-05-23T15:00:00"},
      "1d": {"records": 120, "last_datetime": "2026-05-23"}
    }
  },
  "schema_version": "v1"
}
```

### 6.8 实施步骤

| 步骤 | 任务 | 说明 |
|------|------|------|
| 1 | 创建DataBackup类 | 实现备份/恢复核心功能 |
| 2 | 集成到data_init.py | 数据插入后自动备份 |
| 3 | 创建检查脚本 | check_backup.py |
| 4 | 更新启动中心 | 添加"检查数据备份状态"菜单 |
| 5 | 测试备份恢复 | 完整流程验证 |

---

## 七、数据格式规范

### 7.1 绩效指标存储格式

所有绩效指标统一使用**小数格式**存储，前端显示时统一乘以100转换为百分比。

| 字段 | 存储格式(小数) | 显示格式 | 示例 |
|------|---------------|----------|------|
| `max_drawdown` | 0.00079 | 0.08% | 0.079%的最大回撤 |
| `total_return` | 1.589877 | 158.99% | 158.99%的总收益 |
| `win_rate` | 0.95 | 95.0% | 95%的胜率 |
| `avg_trade_return` | 0.001423 | 0.142% | 0.142%的平均交易收益 |
| `sharpe_train` | 2.5 | 2.50 | 夏普比率（不转换） |
| `calmar` | 3.2 | 3.20 | 卡玛比率（不转换） |

### 7.2 前端显示规范

```tsx
// 统一乘以100显示为百分比
{(factor.max_drawdown * 100).toFixed(1)}%    // 0.08%
{(factor.total_return * 100).toFixed(1)}%    // 158.99%
{(factor.win_rate * 100).toFixed(1)}%        // 95.0%
{(factor.avg_trade_return * 100).toFixed(2)}% // 0.14%

// 比率类指标直接显示（不乘以100）
{factor.sharpe_train.toFixed(2)}              // 2.50
{factor.calmar.toFixed(2)}                   // 3.20
```

### 7.3 数据迁移说明

**2026-05-30 数据迁移**：
- 旧数据格式：百分比数值（如 `total_return = 15898.77` 表示 15898.77%）
- 新数据格式：小数格式（如 `total_return = 1.589877` 表示 158.99%）
- 迁移脚本：`scripts/migrate_normalize_percentages.py`

---

## 附录：严重 Bug 修复记录

### Bug #1：期货盈亏计算公式错误（2026-05-30 修复）

**严重级别**：🔴 **严重** - 导致所有回测收益被放大约 5000 倍

**问题描述**：
回测引擎 `engine.py` 中的期货盈亏计算公式错误地把 `contract_value_per_lot`（合约名义价值，约 50000 元）当成了 `每手吨数`（如 10 吨）。

**错误代码**：
```python
# 错误的计算（原代码第 167 行）
pnl = pos * (exit_px - pos_entry_px) * pos_lots * contract_value_per_lot
# 示例：价差 100元 × 226手 × 50000 = 1,130,000,000 元（11亿！）
```

**正确公式**：
```python
# 正确的计算（已修复）
pnl = pos * (exit_px - pos_entry_px) * pos_lots * contract_multiplier
# 示例：价差 100元 × 226手 × 10吨 = 226,000 元（22.6万）
```

**影响范围**：
| 指标 | 修复前（错误） | 修复后（正确） |
|------|---------------|---------------|
| total_return | 39709%（3.98亿） | 21.76%（22万） |
| max_drawdown | 显示异常低 | 正常显示 |
| sharpe | 被严重夸大 | 正常范围 |

**修复内容**：
1. 新增参数 `contract_multiplier`（每手吨数，默认 10）
2. 修改 `_nb_backtest_core` Numba 函数签名
3. 修正平仓盈亏计算（第 169 行）
4. 修正持仓浮动盈亏计算（第 212 行）
5. 更新所有调用点传递新参数

**涉及文件**：
- `quant_engine/validation/engine.py`
- `quant_engine/ops/gp_fitness.py`
- `quant_engine/ops/evolution_center.py`
- `scripts/run_continuous_evolution.py`

**数据清理**：
修复前数据库中的所有候选者数据（candidates 表）的收益数据都是错误的，建议：
1. 清空 candidates 表重新运行进化
2. 或重新运行数据迁移脚本修复历史数据

### Bug #2：单次交易平均收益率前端显示为 0（2026-05-30 修复）

**问题描述**：
前端表格中"单次交易平均收益率"列全部显示为 `0.000%`，但数据库中实际有值。

**原因**：
1. 后端 API `/evolution/factors` 返回的数据中**缺少 `avg_trade_return` 字段**
2. 前端 `EvolutionFactor` 接口未定义该字段
3. 前端显示时未乘以 100 转换为百分比

**修复内容**：
1. `app/api/routes/evolution.py` - 添加 `avg_trade_return` 字段到 API 响应
2. `frontend/src/lib/api.ts` - 在 `EvolutionFactor` 接口中添加 `avg_trade_return: number`
3. `frontend/src/pages/EvolutionCenter.tsx` - 显示时乘以 100：`(factor.avg_trade_return * 100).toFixed(3)%`

### Bug #3：API 查询逻辑问题导致数据不一致（2026-05-30 修复）

**问题描述**：
验证监控页面显示的数据不一致：
- Search 输入显示 480
- 总因子显示 195
两者应该一致（都是 total_factors）

**原因**：
`evolution_cycles.py` 查询任务时只按 `created_at` 排序，可能获取到已完成的任务而非正在运行的任务。

**修复内容**：
`app/api/evolution_cycles.py` - 优先查询 `RUNNING` 状态的任务，如果没有再获取最新任务。

### Bug #4：Search 输入数字会跳变（从大变小）（2026-05-30 修复）

**问题描述**：
验证监控页面中，Search 阶段的"输入"数字会从较大的值跳变为较小的值（例如从 2000+ 跳回 2000）。

**原因**：
`total_factors` 被设置为 `len(self.historical_individuals)`，这是**保留的历史个体数**（最多保留 2000 个优质因子）。当累计生成的个体超过 2000 时，会按适应度排序清理，只保留前 2000 个，导致 `total_factors` 从 2000+ 跳回 2000。

但用户期望的 Search 输入应该是**从运行开始至今累计生成的所有因子表达式总数**（只增不减）。

**修复内容**：
1. `evolution_center.py` - 添加 `total_generated_count` 累计计数器
2. `evolution_center.py` - 在每代回调中累加本代生成的因子数：`self.total_generated_count += len(self.gp.manager.population)`
3. `evolution_center.py` - 更新心跳调用使用累计值：`total_factors=self.total_generated_count`
4. `evolution_center.py` - 修复验证流程数据更新中的 `search_input` 使用累计值

**解决思路分析**：

1. **问题定位**：
   - 首先确认 Search 输入和总因子都使用 `task.total_factors`
   - 检查代码发现 `total_factors = len(self.historical_individuals)`
   - 发现 `historical_individuals` 有最大限制（2000），超过会被清理

2. **根本原因**：
   - `historical_individuals` 是**历史个体缓存**（用于构建进化树）
   - 设计上需要限制内存占用，所以只保留前 2000 个优质因子
   - 但 `total_factors` 被错误地用作**累计生成计数器**

3. **解决方案**：
   - 新增独立的累计计数器 `total_generated_count`
   - 在每代结束时累加本代种群大小（而非替换）
   - 该计数器只增不减，不受内存清理策略影响

4. **关键代码变更**：
   ```python
   # 新增累计计数器
   self.total_generated_count: int = 0
   
   # 每代累加（不是赋值）
   self.total_generated_count += len(self.gp.manager.population)
   
   # 使用累计值代替历史个体数
   total_factors=self.total_generated_count
   ```

**修复后的行为**：
- Search 输入 = 累计生成的所有因子数（从第 0 代至今）
- 该数字只会增加，不会减少
- 与"总因子"显示的数字一致

**注意**：这是total_factors的累计计数器，用于跟踪累计生成的因子总数。验证流程的累计逻辑已在2026-05-31更新，所有阶段的输入和输出都是累计值，反映从进化开始至今的总和。

**影响范围**：
- 修复前：累计生成超过 2000 后，Search 输入会跳回 2000
- 修复后：Search 输入正确反映累计生成数（可能达到数万）

### Bug #5：平均收益率显示为 0（2026-05-30 修复）

**问题描述**：
前端表格中"单次交易平均收益率"列始终显示 0.000%。

**根本原因**：
`gp_evolution.py` 中的 `evaluate_fitness` 方法在更新 `individual.metrics` 时**遗漏了 `avg_trade_return` 字段**！

```python
# 修复前（错误）
individual.metrics = {
    "total_return": result.total_return,
    "max_drawdown": result.max_drawdown,
    "total_trades": result.total_trades,
    "win_rate": result.win_rate,
    # 缺少 avg_trade_return！
}
```

这导致：
1. `FitnessEvaluator` 正确计算了 `avg_trade_return`
2. 但 `PopulationManager.evaluate_fitness` 覆盖了 `individual.metrics`，丢失了该字段
3. 保存到数据库时，`ind.metrics.get("avg_trade_return", 0.0)` 默认返回 0

**修复内容**：
1. `gp_evolution.py` - 在 `evaluate_fitness` 方法中添加 `avg_trade_return` 字段
2. 清除 Numba 缓存
3. 创建修复脚本重新计算历史数据

**修复后的验证**：
```python
# 修复前
avg_trade_return: 0.0, total_return=15.8123, total_trades=17

# 修复后  
avg_trade_return: 0.930135, total_return=15.8123, total_trades=17
```

**源头定位过程**：
1. 确认回测引擎 `_nb_calculate_metrics` 输出正确 ✓
2. 确认 `FitnessEvaluator._evaluate_single` 设置正确 ✓  
3. 发现 `PopulationManager.evaluate_fitness` 覆盖 metrics 时遗漏字段 ✗
4. 确认 `_save_to_database` 从 `ind.metrics` 读取 ✓

---

**文档版本**: v2.4  
**创建日期**: 2026-05-20  
**更新日期**: 2026-05-30  
**适用版本**: 期货自动进化因子挖掘系统 v1.0
