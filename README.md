# 期货自动进化因子挖掘系统

基于遗传编程的期货多品种因子自动进化与实盘交易系统。

## 系统架构

```
┌─────────────┐     ┌─────────────────┐
│   Frontend  │────▶│  FastAPI Backend│
│  (React)    │     │   (Python 3.11) │
└─────────────┘     └─────────────────┘
                           │
                    ┌──────┴──────┐
                    │ PostgreSQL  │
                    │ (业务数据)   │
                    └─────────────┘
                           │
                    ┌──────▼──────┐
                    │   Redis     │
                    │  (缓存)     │
                    └─────────────┘
```

## 技术栈

- **后端**: FastAPI + SQLAlchemy 2.0 + Numba + DEAP
- **前端**: React 19 + TypeScript + Tailwind CSS + shadcn/ui
- **数据库**: PostgreSQL (本地服务)
- **缓存**: Redis (本地服务)
- **交易系统**: TQSDK (天勤量化) - 模拟交易与实盘交易
- **市场数据**: TQSDK实时行情

## 🚀 快速开始

### 环境要求

- PostgreSQL 17 (本地服务)
- Redis (本地服务)
- Python 3.11+ (后端开发)
- Node.js >= 18.0 (前端开发)
- Poetry (Python依赖管理)

### 启动方式

项目使用本地服务模式，通过启动中心统一管理：

#### 🎯 启动中心（推荐）

```bash
# 进入项目目录
cd d:\期货自动进化因子挖掘系统

# 双击运行启动中心
bat启动文件夹\启动中心_增强版.bat
```

启动中心选项：
- [1] 基础开发模式 - 启动基础设施+前后端
- [2] 增强版开发模式 - 智能检测、彩色输出
- [3] 仅启动基础设施 - PostgreSQL + Redis
- [4] 仅启动后端
- [5] 仅启动前端
- [6] 数据初始化 - 下载历史K线数据
- [7] 检查服务状态
- [8] 检查数据库状态

### 启动脚本说明

#### 📂 bat启动文件夹（推荐使用）

| 脚本 | 用途 | 说明 |
|------|------|------|
| `启动中心.bat` | **主入口，推荐** | 统一菜单，包含所有启动选项 |
| `start-dev-pro.bat` | 增强版开发模式 | 智能检测、彩色输出 |
| `start-dev.bat` | 基础开发模式 | 一键启动基础设施+前后端 |
| `start-backend-only.bat` | 仅启动后端 | 后端开发专用 |
| `start-frontend-only.bat` | 仅启动前端 | 前端开发专用 |
| `init-data.bat` | 数据初始化 | 下载历史K线数据 |
| `check-status.bat` | 检查服务状态 | 一键检查所有服务 |
| `check-db-status.bat` | 检查数据库状态 | 检查PostgreSQL连接 |
| `restart-all.bat` | 一键重启 | 停止-清理-重启一条龙 |
| `stop-all.bat` | 停止所有服务 | 开发结束后清理 |
| `clean-ports.bat` | 清理端口占用 | 端口冲突时使用 |

### 首次使用流程

```
1. 确保PostgreSQL和Redis服务已安装并启动
2. 配置TQSDK账户信息（在.env文件中设置TQSDK_ACCOUNT和TQSDK_PASSWORD）
3. 运行 bat启动文件夹\启动中心_增强版.bat
4. 选择 [3] 仅启动基础设施（启动PostgreSQL和Redis）
5. 选择 [6] 数据初始化，下载历史K线数据（首次使用必须）
6. 选择启动模式：
   - [1] 基础开发模式
   - [2] 增强版开发模式
7. 访问前端界面开始使用
```

### TQSDK配置

系统使用TQSDK进行实时交易和市场数据获取：

1. **获取TQSDK账户**：
   - 访问天勤量化官网注册账户
   - 获取账户ID和密码

2. **配置环境变量**：
   在项目根目录的`.env`文件中配置：
   ```
   TQSDK_ACCOUNT=your_account_id
   TQSDK_PASSWORD=your_password
   TQSDK_SIM=true  # 模拟交易模式，设为false启用实盘
   ```

3. **交易模式**：
   - 模拟交易（TQKQ）：使用TQSDK模拟账户进行测试
   - 实盘交易：配置真实期货公司账户进行实盘交易

### 访问地址

| 服务 | 地址 |
|------|------|
| 前端界面 | http://localhost:5173 |
| 后端 API | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/health |

## 服务说明

### 核心服务

| 服务名 | 说明 | 端口 |
|--------|------|------|
| `PostgreSQL` | 业务数据库 | 5432 |
| `Redis` | 缓存与消息队列 | 6379 |
| `Backend` | FastAPI 后端服务 | 8000 |
| `Frontend` | React 开发服务器 | 5173 |

## API 路由

### 已注册路由

| 前缀 | 功能 |
|------|------|
| `/api/evolution/*` | 进化任务管理 |
| `/api/candidates/*` | 候选策略生命周期 |
| `/api/symbols/*` | 品种管理与切换 |
| `/api/dashboard/*` | 监控面板数据 |
| `/api/risk/*` | 风控事件与配置 |
| `/api/trades/*` | 交易记录与统计 |
| `/ws` | WebSocket 实时推送 |
| `/health` | 健康检查 |

## 开发指南

### 本地开发

```bash
# 设置 PYTHONPATH
$env:PYTHONPATH="d:\期货自动进化因子挖掘系统"

# 安装依赖
cd backend
poetry install --with dev

# 运行测试
poetry run pytest tests/ -v

# 启动开发服务器
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端开发

```bash
cd frontend
npm install
npm run dev
```

### 运行测试

```bash
# 设置 PYTHONPATH
$env:PYTHONPATH="d:\期货自动进化因子挖掘系统"

# 运行所有测试
python -m pytest backend/tests/ -v

# 运行特定测试
python -m pytest backend/tests/test_dsl.py -v
```

## 项目结构

```
.
├── backend/
│   ├── app/
│   │   ├── api/routes/      # API 路由
│   │   ├── main.py          # FastAPI 入口
│   │   ├── models.py        # SQLAlchemy 模型
│   │   └── config.py        # 配置管理
│   ├── quant_engine/        # 量化引擎
│   │   ├── factors/         # 因子 DSL / 注册表 / 验证器
│   │   ├── validation/      # 回测引擎
│   │   ├── core/            # 候选策略状态机
│   │   └── ...
│   ├── tests/               # 测试套件
│   ├── pyproject.toml       # Poetry 依赖
│   └── scripts/maintenance/ # 维护脚本
├── frontend/
│   ├── src/                 # React 源码
│   └── package.json
├── bat启动文件夹/            # 启动脚本（推荐）
│   ├── 启动中心.bat         # 统一启动入口
│   └── ...
└── README.md
```

## 测试覆盖

| 测试文件 | 覆盖内容 | 用例数 |
|----------|----------|--------|
| `test_dsl.py` | DSL 词法/语法/编译 | 28 |
| `test_validator.py` | 语义约束引擎 | 34 |
| `test_backtest.py` | 向量化回测引擎 | 11 |
| `test_candidate.py` | 候选策略状态机 | 22 |
| `test_deap.py` | DEAP遗传编程 | 20 |

## 常用命令

```bash
# 检查服务状态
运行 bat启动文件夹\启动中心_增强版.bat
选择 [7] 检查服务状态

# 检查数据库状态
运行 bat启动文件夹\启动中心_增强版.bat
选择 [8] 检查数据库状态

# 重启所有服务
运行 bat启动文件夹\启动中心_增强版.bat
选择 [9] 重启所有服务

# 停止所有服务
运行 bat启动文件夹\启动中心_增强版.bat
选择 [10] 停止所有服务

# 清理端口占用
运行 bat启动文件夹\启动中心_增强版.bat
选择 [11] 清理端口占用
```

## 配置说明

### 环境变量

环境变量通过 `.env` 文件管理，主要配置项：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | PostgreSQL/TimescaleDB 连接 | `postgresql+psycopg2://postgres:postgres@localhost:5432/quant_db` |
| `REDIS_URL` | Redis 连接 | `redis://localhost:6379/0` |
| `TQSDK_ACCOUNT` | 天勤账号 | - |
| `TQSDK_PASSWORD` | 天勤密码 | - |
| `CORS_ORIGINS` | 跨域来源 | `http://localhost` |

### 因子池管理配置

因子池管理配置文件位于 `backend/config/factor_pool_config.yaml`，用于控制因子挖掘和淘汰策略。

**配置项说明：**

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `factor_pool_size` | 因子池大小（保留的最佳因子数量） | 20 |
| `rolling_window.enabled` | 是否启用滚动窗口评估 | true |
| `rolling_window.size` | 滚动窗口大小（代数） | 50 |
| `decay_evaluation.enabled` | 是否启用因子衰减评估 | true |
| `decay_evaluation.threshold` | 衰减阈值（最近表现比历史最佳下降比例） | 0.3 |
| `rebalancing.enabled` | 是否启用定期重新平衡 | true |
| `rebalancing.period` | 重新平衡周期（代数） | 10 |
| `niche_mechanism.enabled` | 是否启用小生境机制（保持多样性） | false |
| `composite_score_weights` | 综合评分权重配置 | - |
| `normalization` | 评分归一化参数配置 | - |

**综合评分权重：**

- `sharpe`: 夏普比率权重（默认 0.4）
- `calmar`: 卡玛比率权重（默认 0.2）
- `drawdown`: 最大回撤权重（默认 0.2）
- `win_rate`: 胜率权重（默认 0.1）
- `trades`: 交易次数权重（默认 0.1）

**新综合评分公式（IC优化后）：**

- 验证评分 × 0.4（基于夏普、卡玛、回撤、胜率、交易次数）
- IC评分 × 0.4（基于多窗口IC均值和IC信息比率）
- 稳定性评分 × 0.2（基于IC半衰期）

## IC计算优化与策略轮换

### 验证流程扩展

系统新增IC计算层作为验证流程的第五阶段：

```
Search → Replay → Validation → Demo → IC筛选
```

### 新增功能

1. **因子值序列生成** (`factor_value_generator.py`)
   - 只对通过Demo阶段的因子生成因子值序列
   - 存储在 `FactorValueHistory` 表中
   - 避免对所有因子生成序列，节省计算资源

2. **IC计算模块** (`ic_calculator.py`)
   - 计算多窗口IC指标（4h, 24h, 168h）
   - 计算IC信息比率（IC IR）
   - 计算IC半衰期作为稳定性指标
   - 基于综合IC评分筛选前50个因子

3. **策略评估扩展**
   - 相关性矩阵计算：使用因子值序列计算Pearson相关性
   - 策略生成：从前50个IC筛选因子中选择5个低相关性策略
   - 新增API端点：
     - `/strategy/correlation-matrix` - 计算相关性矩阵
     - `/strategy/generate-strategies` - 生成策略组合

4. **策略轮换调度器**
   - 每14天自动执行策略轮换
   - 使用 `EvolutionScheduler` 框架
   - 在应用启动时自动注册和启动

### 数据库变更

新增表：
- `factor_value_history` - 存储因子值序列

扩展表：
- `validation_pipeline_data` - 添加IC计算层字段（ic_input, ic_output, ic_drop）
- `candidates` - 添加IC指标字段（ic_mean_4h, ic_mean_24h, ic_mean_168h, ic_ir, ic_half_life）
- `evolution_factors` - 添加IC指标字段

### 前端变更

1. **验证监控页面** (`ValidationMonitor.tsx`)
   - 调整为5层筛选卡片布局（一行一个）
   - 添加IC计算层卡片显示

2. **因子库页面** (`FactorLibrary.tsx`)
   - 新增"IC筛选因子"标签页
   - 显示前50个IC筛选因子及其IC指标

3. **策略评估页面** (`StrategyEvaluation.tsx`)
   - 新增"相关性验证"标签页
   - 新增"策略生成"标签页

4. **进化中心页面** (`EvolutionCenter.tsx`)
   - 更新最佳因子表，显示IC指标
   - 使用新的综合评分公式

### 数据库迁移

项目使用SQLAlchemy的`Base.metadata.create_all()`方式创建表，新表已在`app/models.py`中定义。

执行数据库初始化：

```bash
# 方法1：通过启动中心
运行 bat启动文件夹\启动中心_增强版.bat
选择 [8] 检查数据库状态

# 方法2：手动执行
cd backend
poetry run python -m app.init_db
```

新表自动创建：
- `factor_value_history` - 存储因子值序列
- `validation_pipeline_data` - 扩展IC计算层字段
- `candidates` - 扩展IC指标字段
- `evolution_factors` - 扩展IC指标字段

**评分归一化参数：**

- `sharpe.min/max`: 夏普比率归一化范围（默认 -2 到 5）
- `calmar.min/max`: 卡玛比率归一化范围（默认 0 到 5）
- `trades.max`: 交易次数归一化最大值（默认 100）

**工作原理：**

1. **竞争淘汰**：新因子与现有因子按综合评分竞争，保留评分最高的 N 个因子
2. **定期重新平衡**：每 N 代（默认 10 代）进行一次竞争淘汰，其他代只累积新因子
3. **因子衰减评估**：检测因子是否衰减（sharpe_val 比 sharpe_train 低 30%），衰减因子评分减半
4. **滚动窗口评估**：使用最近 N 代（默认 50 代）的表现评估因子，而非全局历史

**配置示例：**

```yaml
# 因子池大小
factor_pool_size: 20

# 滚动窗口配置
rolling_window:
  enabled: true
  size: 50

# 因子衰减评估
decay_evaluation:
  enabled: true
  threshold: 0.3

# 定期重新平衡
rebalancing:
  enabled: true
  period: 10

# 综合评分权重
composite_score_weights:
  sharpe: 0.4
  calmar: 0.2
  drawdown: 0.2
  win_rate: 0.1
  trades: 0.1
```

## GitHub配置

### Personal Access Token

GitHub Personal Access Token: `<YOUR_GITHUB_PERSONAL_ACCESS_TOKEN>`

**注意**: 此Token用于推送代码到GitHub仓库，请妥善保管，不要泄露。

## 许可证

MIT License
