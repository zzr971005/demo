# 期货自动进化因子挖掘系统 - 数据库架构文档

## 概述

系统采用双数据库架构：
- **PostgreSQL**: 主数据库，存储业务数据
- **SQLite**: 进化数据库，存储进化引擎数据

## PostgreSQL数据库 (quant_db)

### 连接信息
- 主机: localhost
- 端口: 5432
- 数据库: quant_db
- 用户: postgres
- ORM: SQLAlchemy (Async)

### 主要表结构

#### 1. ohlcv_data
OHLCV行情数据表
- symbol: 品种代码
- datetime: 时间戳
- open, high, low, close, volume: OHLCV数据
- 按品种和时间索引

#### 2. factor_values
因子值表
- symbol: 品种代码
- factor_id: 因子ID
- datetime: 时间戳
- value: 因子值
- 按品种、因子、时间索引

#### 3. candidates
候选因子表（核心表）
- factor_id: 因子ID
- expression: 因子表达式
- symbol: 品种代码
- generation: 世代
- 性能指标: sharpe_ratio, calmar_ratio, max_drawdown, total_return, win_rate
- IC指标: ic_mean_4h, ic_mean_24h, ic_mean_168h, ic_std, ic_ir, ic_half_life
- 复杂度: node_count, tree_depth
- 过拟合检验: pbo_value, dsr_value, wfe_value, overfitting_passed
- 策略选择: is_selected_strategy, strategy_rank, factor_category
- 按品种、世代、候选状态索引

#### 4. trades
交易记录表
- symbol: 品种代码
- factor_id: 因子ID
- datetime: 时间戳
- direction: 方向
- volume: 数量
- price: 价格
- pnl: 盈亏
- 按品种、因子、时间索引

#### 5. symbol_switches
品种切换记录表
- symbol: 品种代码
- from_factor: 原因子
- to_factor: 新因子
- switch_time: 切换时间
- reason: 切换原因

#### 6. evolution_generations
进化世代统计表
- task_id: 任务ID
- generation: 世代
- 性能统计: avg_sharpe, max_sharpe, min_sharpe, top_10_sharpe
- 多样性: diversity_score, unique_expressions
- 过拟合: pbo_value, dsr_value, wfe_value
- 按任务、世代索引

#### 7. evolution_tasks
进化任务表
- task_id: 任务ID
- symbol: 品种代码
- status: 状态
- generations: 总世代数
- population_size: 种群大小
- 统计: total_factors_generated, factors_passed_overfitting
- 按任务ID、品种索引

#### 8. risk_events
风控事件表
- symbol: 品种代码
- event_type: 事件类型
- level: 风险等级
- message: 事件消息
- resolved: 是否已解决
- 按品种、状态索引

#### 9. strategy_rotation_history
策略轮换历史表
- rotation_id: 轮换ID
- symbol: 品种代码
- from_strategies: 原策略列表
- to_strategies: 新策略列表
- rotation_time: 轮换时间
- 按品种、时间索引

#### 10. factor_decay_history
因子衰减历史表
- factor_id: 因子ID
- symbol: 品种代码
- ic_value: IC值
- decay_rate: 衰减率
- recorded_at: 记录时间
- 按因子、品种、时间索引

#### 11. factor_live_stats
因子实时统计表
- factor_id: 因子ID
- symbol: 品种代码
- live_sharpe: 实时夏普
- live_return: 实时收益
- live_drawdown: 实时回撤
- updated_at: 更新时间
- 按因子、品种索引

## SQLite数据库 (runtime.db)

### 连接信息
- 路径: `data/runtime.db`
- ORM: SQLAlchemy (Sync)
- 用途: 进化引擎专用数据库

### 主要表结构

#### 1. evolution_tasks
进化任务表（与PostgreSQL同步）
- task_id: 任务ID
- symbol: 品种代码
- status: 状态
- generations: 总世代数
- population_size: 种群大小
- 统计信息

#### 2. evolution_generations
进化世代记录表
- task_id: 任务ID
- generation: 世代
- 性能统计
- 多样性指标
- 过拟合检验

#### 3. evolution_factors
进化因子记录表（核心表）
- factor_id: 因子ID
- task_id: 任务ID
- symbol: 品种代码
- expression: 因子表达式
- generation: 世代
- origin: 来源
- 复杂度: node_count, tree_depth
- 性能指标: sharpe_ratio, calmar_ratio, max_drawdown, total_return, win_rate
- IC指标: ic_mean_4h, ic_mean_24h, ic_mean_168h, ic_std, ic_ir, ic_half_life
- 因子分类: factor_category
- 策略选择: is_selected_strategy, strategy_rank
- 过拟合检验: pbo_value, dsr_value, wfe_value, overfitting_passed
- 排名: rank_in_generation, overall_rank
- 候选状态: is_candidate
- 实盘状态: is_live, live_since, last_deployed_at

#### 4. factor_live_stats
因子实时统计表
- factor_id: 因子ID
- symbol: 品种代码
- 实时性能指标
- 更新时间

## 数据同步策略

### PostgreSQL -> SQLite
- 候选因子数据从PostgreSQL同步到SQLite
- 进化任务配置从PostgreSQL同步到SQLite
- 实时统计数据从PostgreSQL同步到SQLite

### SQLite -> PostgreSQL
- 进化产生的因子从SQLite同步到PostgreSQL
- 世代统计从SQLite同步到PostgreSQL
- 过拟合检验结果从SQLite同步到PostgreSQL

## 数据库迁移历史

### PostgreSQL迁移
- v1 -> v2: 添加IC相关字段到candidates表
  - ic_mean_4h, ic_mean_24h, ic_mean_168h
  - ic_std, ic_ir, ic_half_life
  - factor_category, is_selected_strategy, strategy_rank

### SQLite迁移
- v1 -> v2: 添加IC相关字段到evolution_factors表
  - ic_mean_4h, ic_mean_24h, ic_mean_168h
  - ic_std, ic_ir, ic_half_life
  - factor_category, is_selected_strategy, strategy_rank

## 维护建议

1. 定期备份PostgreSQL数据库
2. 定期清理SQLite数据库中的历史数据
3. 监控数据库大小和性能
4. 定期执行VACUUM优化SQLite
5. 确保双数据库数据一致性
