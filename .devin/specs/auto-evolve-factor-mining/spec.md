# 期货自动进化因子挖掘系统 — 开发规格书

> **版本**: v1.0 最终版  
> **目标**: 一次性开发完成，直接部署运行  
> **市场**: 国内期货（CTP via 天勤TqSdk）  
> **开发工具**: Windsurf / Trae (AI IDE)  
> **主周期**: 1小时 (H1)，辅助日线Regime过滤  
> **change-id**: auto-evolve-factor-mining

---

## Why

个人期货量化交易者面临的核心困境是：手工开发的策略会随市场Regime变化而失效，且因子挖掘依赖经验和直觉，难以系统化。本系统通过**遗传编程自动进化因子组合**，每晚自动运行进化算法挖掘新策略，并通过**模拟盘验证→手动开关实盘→自动优胜劣汰**的闭环，实现策略的自适应更新。这是当前个人量化期货领域最系统化的终极解决方案。

## What Changes

- **新增** 12品种独立进化池系统（8低保证金+4高保证金）
- **新增** 遗传编程因子挖掘引擎（DEAP + 分层进化 + 语义约束）
- **新增** 候选策略全生命周期管理（Seed→Backtest→Paper→Deployable→Running→Degraded→Retired）
- **新增** 三周期金字塔架构（日线Regime过滤 + 1小时主信号 + 5分钟执行优化）
- **新增** 品种手动开关面板（OFF/PAPER/LIVE三态，切换LIVE需二次确认）
- **新增** 策略血缘追踪与进化树可视化
- **新增** 向量化回测引擎（Numba加速）+ 天勤桥接交叉验证
- **新增** 实时监控面板（全局监控/进化树/品种详情/手动控制四视图）
- **复用** AIQT旧项目的TQSDK连接管理、风控体系、数据库模型、回测引擎基础

## Impact

- **Affected specs**: 因子挖掘六层规范框架、候选状态机、三周期金字塔、品种矩阵
- **Affected code**: 全栈新系统，后端FastAPI + 前端React，数据层TimescaleDB + SQLite
- **Breaking**: 与AIQT旧项目不兼容，为独立新系统，但可复用部分模块

---

## ADDED Requirements

### Requirement: 12品种独立进化池

The system SHALL provide 12 independent evolution pools, one per symbol, with low correlation grouping.

#### Scenario: 品种矩阵初始化
- **WHEN** 系统启动时
- **THEN** 自动初始化12个品种的进化池配置（MA/RB/M/TA/FG/SR/SA/PP/AU/CU/SC/IF）
- **AND** 每个品种维护独立的种群（population=300）和进化历史

#### Scenario: 分组隔离
- **WHEN** 进化算法运行时
- **THEN** A组（化工能源）与B组（黑色建材）与C组（农产品）与D组（贵金属金融）之间不共享因子权重
- **AND** 组内品种也分独立池

### Requirement: 遗传编程因子挖掘引擎

The system SHALL use DEAP genetic programming with hierarchical evolution and semantic constraints.

#### Scenario: 分层进化三阶段
- **WHEN** 每晚20:30触发进化
- **THEN** Stage 1: 单因子挖掘（树深<=4，筛选IC>0.03）
- **AND** Stage 2: 双因子组合（跨族组合，筛选夏普>0.8）
- **AND** Stage 3: 策略填充（进化参数，测试集夏普>0.6）

#### Scenario: 语义约束拦截
- **WHEN** 进化生成新表达式
- **THEN** 自动检查约束：禁止close/volume、禁止log负数、ts_corr同量纲、树深<=8
- **AND** 违反约束的个体给予适应度惩罚或死亡

#### Scenario: 种子保护机制
- **WHEN** 进化前10代
- **THEN** 强制保留20%种子个体（S01-S04经典策略）
- **AND** 新个体必须击败至少一个种子才能进入Deployable池

#### Scenario: 动态方向调节
- **WHEN** 每周末分析
- **THEN** 计算各族近20日夏普中位数
- **AND** 夏普>1.0的族下一代选择概率x1.3，夏普<0的族概率x0.5

### Requirement: 候选策略全生命周期管理

The system SHALL manage candidate strategies through a complete state machine.

#### Scenario: 状态流转
- **WHEN** 策略被进化生成
- **THEN** 状态为SEED → 通过回测后变为BACKTEST → 模拟盘2周后变为PAPER → 达标后变为DEPLOYABLE → 用户手动开启后变为RUNNING → 表现不达标变为DEGRADED → 归档30天后变为RETIRED

#### Scenario: 自动替换
- **WHEN** Paper策略近5日夏普 > Running策略近5日夏普 x 1.2
- **AND** Paper运行>=14天
- **THEN** 自动替换Running策略，旧策略降级为DEPLOYABLE

#### Scenario: 回撤强制降级
- **WHEN** Running策略近5日夏普<0且回撤>8%
- **THEN** 强制降级为DEGRADED，次优策略顶上

### Requirement: 三周期金字塔架构

The system SHALL use a three-period pyramid for signal generation and execution.

#### Scenario: 日线Regime过滤
- **WHEN** 每日收盘后
- **THEN** 计算trend_strength = ts_corr(close_d, ts_mean(close_d, 20), 20)
- **AND** trend_strength>0.6时，1小时策略多头权重x1.5
- **AND** 高波动Regime时，1小时策略仓位减半

#### Scenario: 1小时主信号
- **WHEN** 每根1小时K线收盘
- **THEN** 计算所有Running策略的因子值
- **AND** 生成交易信号（BUY/SELL/HOLD）
- **AND** 执行下单/风控检查

#### Scenario: 5分钟执行优化
- **WHEN** 1小时信号触发后
- **THEN** 在5分钟级别进行TWAP拆单、滑点控制
- **AND** 5分钟不生成新信号，仅优化执行

### Requirement: 品种手动开关

The system SHALL provide manual control for each symbol with safety checks.

#### Scenario: 三态切换
- **WHEN** 用户切换品种状态
- **THEN** 支持OFF（完全关闭）/ PAPER（模拟盘）/ LIVE（实盘）
- **AND** 切换后该品种所有策略Pause，仓位可选"平仓"或"保持"

#### Scenario: LIVE切换自检
- **WHEN** 用户切换到LIVE
- **THEN** 系统强制检查：1)有Deployable策略 2)保证金充足 3)天勤连接正常 4)当日未熔断 5)不在交割月
- **AND** 显示当前策略近20日夏普和最大回撤，需二次确认

### Requirement: 回测与验证体系

The system SHALL provide vectorized backtesting with cross-validation.

#### Scenario: 向量化回测
- **WHEN** 输入因子值序列和参数
- **THEN** 使用Numba JIT加速计算回测结果
- **AND** 输出夏普、Calmar、最大回撤、换手、交易次数

#### Scenario: 天勤桥接验证
- **WHEN** 向量化回测完成后
- **THEN** 调用天勤TqSdk进行事件驱动回测
- **AND** 与向量化结果交叉验证，差异>5%时告警

#### Scenario: 样本切分
- **WHEN** 进化使用数据
- **THEN** 严格时序分离：训练6个月/验证6个月/测试6个月
- **AND** 滑动窗口每日前进，T-1截断（严禁未来函数）

### Requirement: 实时监控面板

The system SHALL provide a React-based monitoring dashboard with 4 views.

#### Scenario: 全局监控视图
- **WHEN** 用户打开Dashboard
- **THEN** 显示12品种矩阵卡片（颜色编码状态/保证金进度条/近5日夏普）
- **AND** 底部显示全局资金曲线、回撤、胜率、夏普、Calmar

#### Scenario: 进化树视图
- **WHEN** 用户查看某品种进化历史
- **THEN** 显示Gen1→Gen2→Gen3父子关系树
- **AND** 当前Running策略高亮，候选挑战者标注
- **AND** 右侧显示适应度曲线、种群多样性、原语族占比

#### Scenario: 品种详情视图
- **WHEN** 用户点击某品种卡片
- **THEN** 左侧显示策略列表（Running/Paper/Seed）
- **AND** 右侧显示信号面板、持仓面板、Regime雷达图、交易记录、研究基线

#### Scenario: 手动控制视图
- **WHEN** 用户打开控制面板
- **THEN** 显示品种开关矩阵、全局熔断按钮
- **AND** 保证金不足品种启动按钮灰色禁用
- **AND** LIVE切换弹窗显示策略表现和二次确认

### Requirement: 风控与保证金监控

The system SHALL enforce real-time risk monitoring and margin control.

#### Scenario: 实时监控
- **WHEN** 实盘运行时
- **THEN** 每秒监控：单品种回撤、单日亏损、总保证金占用
- **AND** 单品种回撤>10%自动暂停，单日亏损>5%全系统熔断

#### Scenario: 保证金限额
- **WHEN** 计算开仓
- **THEN** 实时计算占用保证金，接近1.5万限额时拒绝开仓
- **AND** IF品种严格禁止CLOSE_TODAY操作

#### Scenario: 仓位对账
- **WHEN** 每秒运行
- **THEN** 比对系统持仓与天勤持仓
- **AND** 不一致立即告警

---

## MODIFIED Requirements

### Requirement: 数据层架构（基于AIQT旧项目改进）

**原AIQT项目**: 使用PostgreSQL双库架构（历史库+实时库），模型设计成熟但过于复杂。

**修改后**: 
- TimescaleDB存储行情OHLCV和因子值（时序数据专用）
- SQLite存储策略状态、账户、交易记录（轻量、零配置）
- Redis用于缓存、消息队列、实时行情推送
- 本地CSV备份因子原语库

**Migration**: 从AIQT迁移时需重新设计表结构，保留realtime_models.py中的UnifiedPosition/RiskConfig等核心模型概念。

### Requirement: TQSDK连接管理（基于AIQT旧项目改进）

**原AIQT项目**: TQSDKCore单例模式，支持模拟账户和回测账户，硬编码账户信息。

**修改后**:
- 保留单例模式和连接池设计
- 账户信息从环境变量/config.yaml读取
- 分离回测和实盘连接逻辑
- 支持12品种同时订阅

**Migration**: 直接复用tqsdk_core.py和tqsdk_client.py，移除硬编码账号密码。

---

## REMOVED Requirements

### Requirement: AIQT旧项目的LSTM/RL预测模型

**Reason**: 新系统采用遗传编程因子挖掘替代神经网络预测，策略生成方式完全不同。

**Migration**: 旧项目的LSTMTrainer/RLTrainer/RLPredictor等模块不迁移，但FeatureBuilder中的技术指标计算函数可复用。

### Requirement: AIQT旧项目的三策略竞争架构（趋势/波段/套利）

**Reason**: 新系统的策略竞争在品种内部通过进化池自动完成，不再需要人工定义的三策略架构。

**Migration**: 旧项目的策略工厂模式（factory.py）和基类（base_strategy.py）可作为参考，但需重新设计为候选状态机模式。

---

## 技术栈总览

```
┌─────────────────────────────────────────────────────────────┐
│                      前端层 (Frontend)                        │
│  React 19 + TypeScript + Tailwind CSS + shadcn/ui           │
│  Zustand状态管理 + WebSocket + Recharts图表                   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      网关层 (Gateway)                         │
│  FastAPI (Python) + Uvicorn + WebSocket Endpoint             │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    应用服务层 (Services)                      │
│  Candidate │ Evolution │ Execution │ Regime │ Risk │ Account │
│  Feedback  │ Panel     │ Scheduler │ Manual │      │         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    计算引擎层 (Engines)                       │
│  Backtest (Numba向量化) │ Alpha Generator (DEAP)              │
│  Formula DSL (SymPy/Lark) │ IC Analysis │ Regime │ Grid      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    数据持久层 (Storage)                       │
│  TimescaleDB (行情OHLCV, 因子值) │ SQLite (策略状态, 账户)   │
│  Redis (缓存, 消息队列, 实时行情) │ 本地CSV (因子原语库备份)   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    交易接口层 (Broker)                        │
│  天勤TqSdk (CTP) │ 模拟盘撮合引擎 │ 实盘风控网关              │
└─────────────────────────────────────────────────────────────┘
```

---

## 核心模块清单

**数据层** `quant_engine/data/`
- `hub.py` — TimescaleDB连接，K线读写，主力合约映射表
- `source.py` — 天勤行情接入，历史数据下载，实时订阅
- `sqlite_dal.py` — SQLite运行时状态读写
- `aux_import.py` — 外部数据导入（现货价格、宏观数据）
- `contract_roll.py` — 主力合约自动换月，价差处理

**因子层** `quant_engine/factors/`
- `registry.py` — 因子注册表，8族原语登记
- `alpha_generator.py` — Alpha信号批量生成
- `formula_dsl.py` — 公式化因子定义语言（核心！）
- `ic_analysis.py` — 信息系数分析
- `vector_index.py` — 因子向量相似度去重
- `market_context.py` — 市场上下文（品种特性、交易时间、保证金率）

**搜索与进化层** `quant_engine/ops/`
- `evolution_center.py` — 进化中心主控，12品种独立调度
- `broad_alpha_search.py` — 单因子挖掘（Stage 1）
- `combo_search.py` — 双因子组合（Stage 2）
- `combo_search_prune.py` — 组合剪枝
- `combo_tune.py` — 组合调优
- `evolve_search.py` — 遗传编程核心（DEAP封装）
- `demo_scheduler_service.py` — 模拟盘调度
- `orchestrator.py` — 流程编排

**验证层** `quant_engine/validation/`
- `engine.py` — 向量化回测引擎（Numba加速）
- `split.py` — 样本切分（训练/验证/测试，时序严格分离）
- `tq_bridge.py` — 天勤回测桥接，交叉验证
- `grid.py` — 网格搜索 + Walk-Forward
- `math_objective.py` — 多目标适应度函数
- `pbo_dsr.py` — PBO过拟合概率 + DSR放气夏普 + BH-FDR多重检验

**候选管理层** `quant_engine/core/`
- `candidate_core.py` — 候选状态机
- `candidate_card.py` — 候选卡片生成
- `candidate_trace.py` — 候选全生命周期追踪（血缘、进化路径）
- `pipeline_model.py` — 管线状态模型
- `pipeline_diagnostics.py` — 管线诊断

**策略与风控层** `quant_engine/strategy/`
- `gate.py` — 策略准入门禁（含PBO/DSR/BH-FDR检验）
- `spec.py` — 策略规格定义
- `position_lifecycle.py` — 仓位生命周期
- `regime_engine.py` — Regime识别引擎
- `regime_features.py` — Regime特征提取
- `regime_service.py` — Regime API服务

**执行层** `quant_engine/runtime/`
- `execution_gateway.py` — 执行网关 + 熔断
- `reconciliation.py` — 仓位对账（系统持仓 vs 天勤持仓）
- `runner.py` — 策略运行器
- `risk_monitor.py` — 实时监控保证金、回撤、波动
- `manual_switch.py` — 品种手动开关控制器

**基础设施层** `quant_engine/infra/`
- `config.py` — 统一配置中心
- `event_model.py` — 事件总线（Redis Pub/Sub）
- `error_model.py` — 错误分类与告警
- `panel_server.py` — 面板HTTP服务
- `infinite_loop.py` — 无限主循环（断点续传版，期货休市时暂停）
- `scheduler.py` — APScheduler任务调度

---

## 关键风险提醒

1. **主力合约换月**: 期货有到期日，系统必须自动映射到下一主力，回测时用真实合约而非连续合约（避免换月跳空污染）
2. **夜盘跳空**: 商品期货夜盘开盘跳空是主要噪音源，必须设计`night_gap_filter`
3. **IF平今手续费陷阱**: IF平今手续费是隔日的10倍，策略必须设计为隔日平仓或持仓过夜，系统中硬编码禁止`CLOSE_TODAY`
4. **保证金实时监控**: 1.5万限额是硬约束，系统必须实时计算占用保证金，接近限额时拒绝开仓
5. **时序纪律**: 进化只能用T-1及以前的数据，T日数据只用于评估，严禁未来函数
6. **断点续传**: 期货有休市，进化引擎不是7×24，而是每晚20:30触发，休市时暂停，开盘前预热
7. **过拟合防控**: 必须集成PBO+DSR+BH-FDR统计检验，这是从"研究级"迈向"生产级"的关键门槛
8. **弱信号矩阵**: 从"挖掘强因子"转向"组合50+弱信号"，利用IR=IC×√N公式提升整体稳健性

---

## 可复用AIQT旧项目模块

| 模块 | 复用文件 | 复用程度 | 修改点 |
|------|---------|---------|--------|
| TQSDK连接管理 | `tqsdk_core.py`, `tqsdk_client.py` | 高 | 移除硬编码账户、分离回测/实盘 |
| 数据库连接池 | `database.py`, `sqlalchemy_pool.py` | 高 | 适配TimescaleDB + SQLite双库 |
| 实时数据模型 | `realtime_models.py` | 中 | 按需选取表、创建迁移脚本 |
| 回测引擎基础 | `backtest_engine.py` | 中 | 适配策略基类、提取绩效分析 |
| 风控体系 | `risk_manager.py`, `risk.py` | 高 | 抽象账户接口、适配新架构 |
| 配置管理 | `config.yaml`, `config.py` | 高 | 移除敏感信息、调整品种列表 |
| 前端布局 | `Layout.tsx`, `App.tsx` | 低 | 重写为shadcn/ui、适配新API |

---

## 网友Sirius系统方法论借鉴

1. **主产品线流程**: 候选生成 → 复现 → 验证 → 调优 → Demo → 反馈回灌
2. **验证三层门槛**: Replay（时序回测）→ Scientific（PBO/DSR/BH-FDR）→ Production（模拟盘）
3. **技术栈参考**: Python 3.14 + TimescaleDB + SQLite(strict mode) + 原生JS SPA
4. **工程健康面板**: 显示每轮drop率、验证通过率、生产通过率
5. **弱信号矩阵**: 50个弱信号胜过一个强信号，IR = IC × √N
6. **统计检验**: PBO<0.3、DSR>0.6、BH-FDR动态门槛
