# Checklist

## 阶段一：地基搭建

- [x] 本地 PostgreSQL + Redis 服务配置完成
- [x] init_db.py 可成功创建所有 hypertable 和 SQLite 表
- [x] SQLAlchemy 2.0 模型定义完整，含 Pydantic 类型注解
- [x] Alembic 迁移脚本可正常执行
- [x] config/system.yaml 包含 12 品种完整配置
- [x] backend/config.py 使用 Pydantic Settings 正确加载 yaml
- [x] backend/main.py FastAPI 入口含 lifespan、CORS、全局异常处理
- [x] 所有 API 路由骨架定义完成，Swagger 文档可访问

## 阶段二：因子DSL + 语义约束

- [x] factors/registry.py 定义 8 族原语，每族 5-8 个函数
- [x] 所有原语函数可独立运行并返回正确结果
- [x] factors/formula_dsl.py 支持字符串表达式解析为可执行函数
- [x] 表达式树序列化/反序列化正确
- [x] SemanticValidator 实现 10 条以上约束规则
- [x] FamilyChecker 确保每个表达式至少包含 2 个不同族
- [x] DSL 解析和约束检查性能满足实时要求

## 阶段三：遗传编程引擎

- [x] ops/evolve_search.py 使用 DEAP 按品种独立进化
- [x] PrimitiveSet 按族正确注册原语
- [x] 多目标适应度函数计算正确（sharpe/calmar/ic/max_dd/turnover/complexity）
- [x] 种子保护机制前 10 代保留 20% 种子
- [x] 早停机制连续 5 代无提升则停止
- [x] Stage 1 单因子挖掘（树深<=4，IC>0.03）可运行
- [x] Stage 2 双因子组合（跨族，夏普>0.8）可运行
- [x] Stage 3 策略填充（测试集夏普>0.6）可运行
- [x] ops/evolution_center.py 可调度 12 品种独立进化
- [x] 单品种 60 代进化可在 30 分钟内完成

## 阶段四：回测引擎 + 天勤桥接

- [x] validation/engine.py 使用 Numba JIT 加速
- [x] 向量化回测输出夏普/Calmar/回撤/换手/交易次数正确
- [x] 支持期货开平方向和保证金计算
- [x] validation/fee_model.py IF 平今手续费为隔日 10 倍
- [x] validation/tq_bridge.py 可调用天勤事件驱动回测
- [x] 向量化与天勤回测差异 < 5%
- [x] validation/split.py 严格时序分离训练/验证/测试
- [x] validation/pbo_dsr.py 实现 PBO/DSR/BH-FDR 统计检验

## 阶段五：候选管理 + 状态机

- [x] core/candidate_core.py 状态机流转正确（Seed→Backtest→Paper→Deployable→Running→Degraded→Retired）
- [x] 非法状态流转被拒绝
- [x] core/candidate_trace.py 记录完整血缘（父代ID/变异算子/交叉对象/进化代数）
- [x] Paper 挑战 Running 自动替换逻辑正确
- [x] 回撤超限（>8%）强制降级逻辑正确
- [x] Regime 不匹配暂停逻辑正确
- [x] 品种独立策略池（趋势4/波段4/反转2）竞争正确

## 阶段六：执行层 + 手动开关

- [x] runtime/execution_gateway.py 可对接天勤下单/撤单/查询持仓
- [x] 熔断机制连续 3 笔异常暂停
- [x] runtime/reconciliation.py 每秒比对系统持仓 vs 天勤持仓
- [x] runtime/risk_monitor.py 实时监控回撤/亏损/保证金
- [x] 单品种回撤>10%自动暂停
- [x] 单日亏损>5%全系统熔断
- [x] runtime/manual_switch.py 支持 OFF/PAPER/LIVE 三态
- [x] LIVE 切换 5 项自检不可跳过
- [x] 切换后策略 Pause，仓位可选"平仓"或"保持"

## 阶段七：前端界面

- [x] React 19 + TypeScript + Tailwind CSS + shadcn/ui 项目可运行
- [x] Zustand 状态管理 + WebSocket 实时推送正常
- [x] Layout 布局含侧边栏导航、顶部状态栏、暗黑模式
- [x] Dashboard 显示 12 品种矩阵卡片（状态/保证金/夏普）
- [x] Dashboard 全局资金曲线和告警日志正常
- [x] EvolutionTree 显示代际时间线和策略血缘树
- [x] SymbolDetail 显示策略列表/信号面板/持仓/Regime雷达图/交易记录
- [x] ManualSwitch 显示品种开关矩阵和全局熔断按钮
- [x] LIVE 切换弹窗含二次确认和 5 项自检结果
- [x] 保证金不足品种启动按钮灰色禁用

## 阶段八：联调 + 部署

- [x] 端到端测试：进化→回测→Paper→手动开启LIVE→自动替换→紧急停止
- [x] 主力合约换月逻辑测试通过
- [x] 夜盘跳空过滤测试通过
- [x] IF 平今手续费禁止测试通过
- [x] 保证金限额拒绝开仓测试通过
- [x] 时序纪律（未来函数检测）测试通过
- [x] 启动脚本后所有服务健康检查通过
- [x] 初始化脚本自动执行成功
- [x] 系统可直接访问完整功能

## 最终交付检查

- [x] 12 品种各 2 年 1 小时 K 线，夜盘数据完整，主力合约连续
- [x] 每晚自动进化，单品种 60 代 < 30 分钟，种群多样性 > 0.5
- [x] 训练/验证/测试严格时序分离，测试集夏普 > 0.6
- [x] 至少 3 个品种同时 Paper 运行 2 周，自动替换机制运转正常
- [x] 用户可手动开启/关闭任意品种，开启前系统自检通过
- [x] 单品种回撤>10%自动暂停，单日亏损>5%全系统熔断
- [x] 系统持仓与天勤持仓每秒比对，不一致立即告警
- [x] 一屏看全品种状态，策略血缘可追溯，手动控制无障碍
- [x] 周末自动分析各族表现，调整下一代进化偏好
- [x] PBO < 0.3、DSR > 0.6、BH-FDR 通过
