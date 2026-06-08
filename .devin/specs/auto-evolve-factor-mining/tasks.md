# Tasks

## 阶段一：地基搭建（第1-2天）

- [x] Task 1: 本地环境 + 数据库Schema
  - [x] SubTask 1.1: 配置本地 PostgreSQL + Redis 服务
  - [x] SubTask 1.2: 编写init_db.py初始化脚本（创建hypertable、种子数据）
  - [x] SubTask 1.3: 编写SQLAlchemy 2.0模型定义（Pydantic完整类型注解）
  - [x] SubTask 1.4: 编写Alembic迁移脚本
  - [x] SubTask 1.5: 验证本地服务可正常启动

- [x] Task 2: 配置中心 + FastAPI骨架
  - [x] SubTask 2.1: 编写config/system.yaml（12品种完整配置、进化参数、风控参数）
  - [x] SubTask 2.2: 编写backend/config.py（Pydantic Settings加载yaml，支持环境变量覆盖）
  - [x] SubTask 2.3: 编写backend/main.py（FastAPI入口、lifespan、CORS、全局异常处理）
  - [x] SubTask 2.4: 编写backend/api/deps.py（依赖注入：数据库/Redis/配置/天勤客户端）
  - [x] SubTask 2.5: 编写backend/api/routes/下所有路由骨架（只写接口定义和Pydantic模型）
    - /api/evolution/run（触发进化）
    - /api/candidates（获取候选列表）
    - /api/symbols/{symbol}/switch（切换品种状态）
    - /api/symbols/{symbol}/detail（品种详情）
    - /api/dashboard/summary（全局监控数据）
    - /api/risk/events（风控事件）
    - /api/trades（交易记录）
  - [x] SubTask 2.6: 验证Swagger文档可访问

## 阶段二：因子DSL + 语义约束（第2-3天）

- [x] Task 3: 因子注册表 + 原语族定义
  - [x] SubTask 3.1: 编写factors/registry.py（8族原语登记：动量/均值回归/波动率/价量/期限结构/持仓量/微观结构/宏观映射）
  - [x] SubTask 3.2: 每族实现5-8个具体原语函数（ts_return, zscore, atr, basis, oi_change等）
  - [x] SubTask 3.3: 编写factors/market_context.py（品种特性、交易时间、保证金率）
  - [x] SubTask 3.4: 验证所有原语函数可独立运行

- [x] Task 4: 公式DSL + 语义约束引擎
  - [x] SubTask 4.1: 编写factors/formula_dsl.py（Lark/SymPy表达式解析器，字符串→可执行函数）
  - [x] SubTask 4.2: 实现表达式树序列化/反序列化
  - [x] SubTask 4.3: 编写SemanticValidator类（10条以上约束规则）
    - C001: ts_mean只能接收价格/成交量/持仓量
    - C101: 禁止close/volume
    - C102: 禁止log负数
    - C201: 树深度>8，适应度x0.8
    - C202: 同一族连续嵌套>2层，适应度x0.9
    - C301: night_gap必须配vol_regime
    - C302: basis必须配trend_strength
    - C303: IF禁止CLOSE_TODAY
  - [x] SubTask 4.4: 编写FamilyChecker（确保每个表达式至少包含2个不同族）
  - [x] SubTask 4.5: 验证DSL解析和约束检查可实时运行

## 阶段三：遗传编程引擎（第3-5天）

- [x] Task 5: DEAP遗传编程核心
  - [x] SubTask 5.1: 编写ops/evolve_search.py（DEAP封装，按品种独立进化）
  - [x] SubTask 5.2: 实现PrimitiveSet按族注册原语
  - [x] SubTask 5.3: 实现多目标适应度函数（0.4*sharpe + 0.3*calmar + 0.2*ic_mean - 0.5*max_dd - 0.3*turnover - 0.2*complexity）
  - [x] SubTask 5.4: 实现种子保护机制（前10代保留20%种子）
  - [x] SubTask 5.5: 实现早停机制（连续5代无提升则停止）
  - [x] SubTask 5.6: 验证单品种进化可运行

- [x] Task 6: 分层进化三阶段
  - [x] SubTask 6.1: 编写ops/broad_alpha_search.py（Stage 1: 单因子挖掘，树深<=4，IC>0.03）
  - [x] SubTask 6.2: 编写ops/combo_search.py（Stage 2: 双因子组合，跨族，夏普>0.8）
  - [x] SubTask 6.3: 编写ops/combo_search_prune.py（组合剪枝）
  - [x] SubTask 6.4: 编写ops/combo_tune.py（Stage 3: 组合调优，参数进化）
  - [x] SubTask 6.5: 编写ops/evolution_center.py（进化中心主控，12品种调度）
  - [x] SubTask 6.6: 验证三阶段进化流水线可运行

## 阶段四：回测引擎 + 天勤桥接（第5-7天）

- [x] Task 7: 向量化回测引擎
  - [x] SubTask 7.1: 编写validation/engine.py（Numba JIT加速）
  - [x] SubTask 7.2: 输入因子值序列和参数，输出夏普/Calmar/回撤/换手/交易次数
  - [x] SubTask 7.3: 支持期货开平方向（OPEN/CLOSE/CLOSE_TODAY）和保证金计算
  - [x] SubTask 7.4: 编写validation/fee_model.py（手续费分层，IF平今10倍）
  - [x] SubTask 7.5: 验证向量化回测结果正确

- [x] Task 8: 天勤桥接 + 样本切分
  - [x] SubTask 8.1: 编写validation/tq_bridge.py（调用天勤TqSdk事件驱动回测）
  - [x] SubTask 8.2: 与向量化结果交叉验证，差异>5%时告警
  - [x] SubTask 8.3: 编写validation/split.py（严格时序分离训练/验证/测试，6个月/6个月/6个月）
  - [x] SubTask 8.4: 编写validation/pbo_dsr.py（PBO过拟合概率 + DSR放气夏普 + BH-FDR多重检验）
  - [x] SubTask 8.5: 验证天勤桥接可运行

## 阶段五：候选管理 + 状态机（第7-8天）

- [x] Task 9: 候选策略全生命周期管理
  - [x] SubTask 9.1: 编写core/candidate_core.py（状态机：Seed→Backtest→Paper→Deployable→Running→Degraded→Retired）
  - [x] SubTask 9.2: 实现状态转换验证（非法流转拒绝）
  - [x] SubTask 9.3: 编写core/candidate_trace.py（血缘追踪：父代ID、变异算子、交叉对象、进化代数）
  - [x] SubTask 9.4: 实现自动替换逻辑（Paper挑战Running、回撤超限降级、Regime不匹配暂停）
  - [x] SubTask 9.5: 实现品种独立策略池（趋势池4/波段池4/反转池2）
  - [x] SubTask 9.6: 验证状态机流转正确

## 阶段六：执行层 + 手动开关（第8-9天）

- [x] Task 10: 执行网关 + 风控监控
  - [x] SubTask 10.1: 编写runtime/execution_gateway.py（对接天勤TqSdk，下单/撤单/查询持仓）
  - [x] SubTask 10.2: 实现熔断机制（连续3笔异常暂停）
  - [x] SubTask 10.3: 编写runtime/reconciliation.py（每秒比对系统持仓vs天勤持仓）
  - [x] SubTask 10.4: 编写runtime/risk_monitor.py（实时监控：单品种回撤/单日亏损/总保证金/交割月警告）
  - [x] SubTask 10.5: 验证可连接天勤模拟盘

- [x] Task 11: 品种手动开关
  - [x] SubTask 11.1: 编写runtime/manual_switch.py（品种三态：OFF/PAPER/LIVE）
  - [x] SubTask 11.2: 实现LIVE切换5项自检（Deployable/保证金/天勤/熔断/交割月）
  - [x] SubTask 11.3: 实现切换后策略Pause，仓位可选"平仓"或"保持"
  - [x] SubTask 11.4: 验证手动开关可控制品种状态

## 阶段七：前端界面（第9-12天）

- [x] Task 12: 前端项目搭建 + 全局组件
  - [x] SubTask 12.1: 初始化React 19 + TypeScript + Tailwind CSS + shadcn/ui项目
  - [x] SubTask 12.2: 配置Zustand状态管理 + WebSocket客户端
  - [x] SubTask 12.3: 实现Layout布局（侧边栏导航、顶部状态栏、暗黑模式切换）
  - [x] SubTask 12.4: 实现全局组件（品种状态徽章、保证金进度条、夏普显示）

- [x] Task 13: Dashboard全局监控视图
  - [x] SubTask 13.1: 实现12品种矩阵卡片（颜色编码状态/保证金进度条/近5日夏普/操作按钮）
  - [x] SubTask 13.2: 实现全局指标卡（资金/收益/回撤/夏普/交易数/运行品种）
  - [x] SubTask 13.3: 实现全局资金曲线图（Recharts）
  - [x] SubTask 13.4: 实现告警日志列表
  - [x] SubTask 13.5: 验证WebSocket实时推送

- [x] Task 14: 进化树 + 品种详情视图
  - [x] SubTask 14.1: 实现EvolutionTree页（代际时间线/策略血缘树/适应度曲线/原语族饼图）
  - [x] SubTask 14.2: 实现SymbolDetail页（左侧策略列表/右侧信号面板+持仓面板+Regime雷达图+交易记录+研究基线）
  - [x] SubTask 14.3: 验证数据绑定正确

- [x] Task 15: 手动控制视图
  - [x] SubTask 15.1: 实现ManualSwitch页（品种开关矩阵/全局熔断按钮）
  - [x] SubTask 15.2: 实现LIVE切换确认弹窗（策略表现/保证金/天勤状态/熔断状态）
  - [x] SubTask 15.3: 实现保证金不足品种灰色禁用
  - [x] SubTask 15.4: 验证控制功能完整

## 阶段八：联调 + 部署（第12-14天）

- [x] Task 16: 系统联调
  - [x] SubTask 16.1: 端到端测试：进化→回测→Paper→手动开启LIVE→自动替换→紧急停止
  - [x] SubTask 16.2: 测试主力合约换月逻辑
  - [x] SubTask 16.3: 测试夜盘跳空过滤
  - [x] SubTask 16.4: 测试IF平今手续费禁止
  - [x] SubTask 16.5: 测试保证金限额拒绝开仓
  - [x] SubTask 16.6: 测试时序纪律（未来函数检测）

- [x] Task 17: 部署与启动脚本
  - [x] SubTask 17.1: 编写bat启动脚本（健康检查、一键启动）
  - [x] SubTask 17.2: 编写.env.example（数据库密码/天勤账号/Redis密码）
  - [x] SubTask 17.3: 编写初始化脚本（自动创建表/导入种子数据）
  - [x] SubTask 17.4: 验证启动脚本后可直接访问完整系统

---

# Task Dependencies

- Task 2 depends on Task 1
- Task 4 depends on Task 3
- Task 5 depends on Task 4
- Task 6 depends on Task 5
- Task 7 depends on Task 2
- Task 8 depends on Task 7
- Task 9 depends on Task 6 and Task 8
- Task 10 depends on Task 2
- Task 11 depends on Task 9 and Task 10
- Task 13 depends on Task 12
- Task 14 depends on Task 12
- Task 15 depends on Task 12
- Task 16 depends on Task 9, Task 11, Task 13, Task 14, Task 15
- Task 17 depends on Task 16

**可并行任务**:
- Task 1 和 Task 3 可并行
- Task 5 和 Task 7 可并行（在Task 4完成后）
- Task 10 和 Task 12 可并行
- Task 13, Task 14, Task 15 可并行（在Task 12完成后）
