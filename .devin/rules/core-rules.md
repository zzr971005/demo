# 期货自动进化因子挖掘系统 — 核心规则

> 基于 `.trae/rules/1.md` + `live-trading-safety.md` 精简合并
> 优先级：P0（必须遵守）

## 0. 开发前确认原则（最高优先级）

- **改代码前必须与用户确认方案所有细节才能开始改**
- 禁止在方案未完全确认的情况下开始编码
- 重大变更必须先有完整方案文档并获得用户确认

## 1. 数据真实性（红线）

- **禁止**虚假数据、默认数据、模拟数据
- **禁止**连接失败时提供模拟数据，必须直接报错
- 所有数据必须来自 **TQSDK** 或真实计算
- 数据库数据必须真实，禁止自动填充假数据

### 1.1 数据库规范

- **TimescaleDB** 用于行情OHLCV和因子值（时序数据专用）
- **SQLite** 用于策略状态、账户、交易记录（轻量、零配置）
- **PostgreSQL** 驱动使用 pg8000 或 psycopg2
- 表结构必须通过 SQLAlchemy 模型统一管理
- 禁止在 SQLite 中存储大量历史行情数据（>10万行）

## 2. TQSDK 使用规则

### 2.1 初始化顺序（死逻辑）
```python
# 正确
api = TqApi(auth=TqAuth(account_id, password))
quote = api.get_quote("KQ.m@SHFE.rb")

# 错误
while True:
    api.wait_update()
    quote = api.get_quote("KQ.m@SHFE.rb")  # 禁止！
```

### 2.2 wait_update() 职责
- 网络通信、任务调度、数据同步、阻塞控制
- 必须在 `wait_update()` 循环前完成初始化

### 2.3 主连合约格式
- 格式：`KQ.m@SHFE.rb`
- 获取标的合约：`quote.underlying_symbol`

### 2.4 保证金计算
- 调用 `calculate_margin()`
- 使用 `broker_margin`，非 `exchange_margin`
- 持仓序列化用 `margin_long_broker` / `margin_short_broker`

### 2.5 合约代码格式

| 类型 | 格式 | 示例 |
|------|------|------|
| 主连 | KQ.m@{交易所}.{品种} | KQ.m@SHFE.rb |
| 具体合约 | {交易所}.{合约} | SHFE.rb2505 |
| 指数 | KQ.i@{交易所}.{品种} | KQ.i@SHFE.rb |

### 2.6 下单规范
```python
order = api.insert_order(
    symbol="SHFE.rb2505",
    direction="BUY",
    offset="OPEN",
    volume=1,
    limit_price=price
)
```

### 2.7 错误处理
```python
try:
    order = api.insert_order(...)
except Exception as e:
    logger.error(f"下单失败: {e}")
    # 重试或告警
```

### 2.8 交易时间
- 日盘：09:00-10:15, 10:30-11:30, 13:30-15:00
- 夜盘：21:00-23:00（部分品种到01:00/02:30）
- 非交易时间禁止下单

## 3. 代码质量

- 修改前**必须**先读取相关文件
- 遵循现有代码风格
- 新功能必须有错误处理和日志
- 资金计算用 Decimal，必须双重验证

## 4. 前端开发

- **禁止** mock 数据
- 用 **Zustand** 状态管理
- 用 **TypeScript** 类型定义
- UI 用 **shadcn/ui**（基于 Tailwind CSS）
- 图表用 **Recharts**

## 5. 因子挖掘与进化

- 训练数据必须真实
- 特征工程代码版本化（feature_calculator_vX）
- 回测必须考虑滑点和手续费
- 新策略上线前必须通过回测 + PBO/DSR/BH-FDR 检验
- **时序纪律**：进化只能用 T-1 及以前数据，严禁未来函数

## 6. 风险控制

- 所有交易必须有止损
- 仓位控制基于动态计算
- 最大回撤限制强制执行
- 实盘前必须在模拟账户验证 >=2 周
- 最大回撤 >10% 的策略自动降级
- 单日亏损 >5% 全系统熔断

### 6.1 交易分级

| 级别 | 资金上限 | 风险敞口 | 审批 |
|------|---------|---------|------|
| Level 1 | 10万 | <5% | 自动 |
| Level 2 | 50万 | <10% | 策略负责人 |
| Level 3 | 100万 | <15% | 技术负责人 |
| Level 4 | 无上限 | <20% | 技术+业务双审批 |

### 6.2 升级条件

- L1->L2: 模拟运行>2周，夏普>1.0，PBO<0.3，DSR>0.6
- L2->L3: L2实盘>3月，回撤<10%
- L3->L4: L3实盘>6月，连续盈利>6月

### 6.3 实盘前检查

- 回测夏普比率 >1.0
- 回测最大回撤 <10%
- 测试集夏普 >0.6
- PBO < 0.3, DSR > 0.6, BH-FDR 通过
- Walk-Forward 效率 WFE > 0.7
- 模拟账户运行 >=2周
- 模拟与回测偏差 <10%
- 止损逻辑正确且强制生效
- 仓位计算正确
- 价格检查（防异常价格）
- 重复下单防护（冷却时间 5秒）
- 交易时间检查
- IF 禁止 CLOSE_TODAY
- TQSDK连接稳定
- 紧急平仓功能可用
- 熔断机制测试通过
- 保证金实时监控正常

### 6.4 熔断机制

| 等级 | 触发条件 | 响应 |
|------|---------|------|
| Level 1 | 数据延迟>10s | 切换数据源 |
| Level 2 | 日亏损>5% | 减仓30% |
| Level 3 | 单品种回撤>10% | 停止该品种新单 |
| Level 4 | 系统异常 | 全部平仓 |

### 6.5 应急响应

```python
async def handle_emergency(level, reason):
    if level >= 2: reduce_positions(0.3)
    if level >= 3: stop_symbol_strategies(symbol)
    if level >= 4: emergency_close_all()
```

## 7. 部署运维

### 7.1 PowerShell
```powershell
# 正确
command1 ; command2

# 错误
command1 && command2
```

### 7.2 HTTP 请求
```powershell
# 正确 - 使用 Invoke-RestMethod
Invoke-RestMethod -Uri http://localhost:8000/health -Method GET

# 错误 - curl 会被解析为 Invoke-WebRequest，需要额外参数
curl http://localhost:8000/health  # 可能提示输入参数
```

### 7.3 批处理文件
- 使用 **GBK (936)** 编码
- 使用 **ASCII** 字符
- 用 `.bat` 启动，禁止直接命令启动

### 7.4 调试规范（重要）

#### 7.4.1 终端使用规则
- **所有后端和前端服务必须在 IDE 自带终端面板中启动**
- **每个服务使用独立的终端标签页**，便于查看实时日志
- **禁止在后台隐藏终端中运行服务**，必须在前端可见终端中运行

#### 7.4.2 多服务调试流程
```
IDE 终端面板布局:
|-- 标签页1: 进化引擎服务 (start_evolution.bat)     端口 8001
|-- 标签页2: 执行网关服务 (start_execution.bat)     端口 8002
|-- 标签页3: 面板HTTP服务 (start_panel.bat)         端口 8000
|-- 标签页4: 前端 (start_frontend.bat)              端口 5173
```

#### 7.4.3 TQSDK 连接规则
- 每个后端服务使用**独立的 TQSDK 连接**
- 同一账户可以在不同终端中并行连接
- 各服务之间互不干扰，独立运行

## 8. 文档与语言规范

- 思考过程必须用**中文**
- 代码注释用中文
- 文档用中文
- 复杂逻辑必须注释
- API/配置变更必须更新文档
- 函数和类必须添加docstring
- Windows 批处理文件使用 **GBK (936)** 编码和 **ASCII** 字符

## 9. 实盘与虚拟盘

- account_id 是**必须有的参数**，用于虚拟盘/实盘数据隔离
- 品种手动开关三态：OFF / PAPER / LIVE
- 切换 LIVE 需二次确认，且系统自检通过

## 10. 配置文件规范

- `.env.example` - 示例配置文件（开发和测试环境参考）
- `.env` - 实际环境配置文件，**禁止提交到版本控制**
- `.env` 必须添加到 `.gitignore`

## 11. 环境管理规范（Poetry）

- **必须使用 Poetry** 管理依赖，禁止使用 pip + requirements.txt
- 项目依赖统一在 `pyproject.toml` 中定义
- **必须**提交 `poetry.lock` 到版本控制
- 生产部署使用 `poetry install --no-dev`

## 12. 因子挖掘特有规则

### 12.1 时序纪律（死逻辑）
- 进化只能用 T-1 及以前的 K 线数据
- T 日数据只用于评估 Running 策略表现
- 严禁未来函数（如使用未来信息计算当前信号）
- 每晚 20:30 进化，数据截断至昨日收盘

### 12.2 主力合约换月
- 回测必须使用真实合约，禁止用连续合约（避免换月跳空污染）
- 系统自动映射主力合约到下一主力
- 换月前 5 天停止该品种新开仓

### 12.3 IF 平今手续费
- IF 平今手续费是隔日的 10 倍
- 策略必须设计为隔日平仓或持仓过夜
- 系统中硬编码禁止 `CLOSE_TODAY` 操作

### 12.4 保证金限额
- 系统必须实时计算占用保证金
- 接近限额时拒绝开仓
- 使用 `broker_margin` 而非 `exchange_margin`

## 13. 回测与实盘一致性

| 参数 | 值 | 说明 |
|------|-----|--------|
| 手续费 | 0.0001 | 万分之一 |
| 滑点 | 0.0002 | 万分之二 |
| 保证金比例 | 0.12 | 12% |

- 收益偏差 < 10%，回撤偏差 < 20%，交易次数偏差 < 15%，胜率偏差 < 10%
- 一致性偏差 >30% 禁止实盘

## 14. 违规后果

代码审查不通过、功能回滚、实盘权限暂停、资金损失、法律责任。

---

**这是生产系统，每个变更都可能影响真实交易和资金。**
