# 项目文档中心

> **项目**: 期货自动进化因子挖掘系统  
> **最后更新**: 2026-05-18  
> **版本**: v1.0-working

---

## 文档导航

### 📋 规格书与计划

| 文档 | 用途 | 链接 |
|------|------|------|
| **开发规格书（工作版）** | 当前开发参考，包含进度追踪 | [specs/v1.0-working.md](./specs/v1.0-working.md) |
| **开发规格书（存档版）** | 原始需求，只读 | [specs/v1.0-archived.md](./specs/v1.0-archived.md) |
| **变更历史** | 规格书变更记录 | [specs/CHANGELOG.md](./specs/CHANGELOG.md) |
| **规格书使用指南** | 如何使用规格书 | [specs/README.md](./specs/README.md) |

### 📈 开发进展

| 文档 | 用途 | 链接 |
|------|------|------|
| **进展记录规则** | 如何记录开发进展 | [development-logs/README.md](./development-logs/README.md) |
| **进展索引** | 所有进展记录索引 | [development-logs/INDEX.md](./development-logs/INDEX.md) |
| **最新进展** | 2026-05-17 交易执行系统完成 | [development-logs/2026-05-17-完整交易执行系统.md](./development-logs/2026-05-17-完整交易执行系统.md) |

### 🔧 技术文档

| 文档 | 用途 | 链接 |
|------|------|------|
| **GP系统实现** | 遗传编程系统详细说明 | [GP_EVOLUTION_SYSTEM.md](./GP_EVOLUTION_SYSTEM.md) |
| **文档管理方案** | MD文件管理规则 | [PROJECT_DOCUMENTATION_PLAN.md](./PROJECT_DOCUMENTATION_PLAN.md) |

### 📁 其他目录

| 目录 | 用途 |
|------|------|
| `plans/` | 开发计划文档 |
| `logs/` | 调试日志 |

---

## 🚀 快速开始

### 系统启动方式

项目使用本地服务模式，通过启动中心统一管理。

#### 🎯 快速启动

```bash
# 进入项目目录
cd d:\期货自动进化因子挖掘系统

# 使用启动中心（推荐）
双击运行：bat-scripts\启动中心_增强版.bat
```

**访问地址：**
- 前端界面: http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

#### 🛠️ 手动安装依赖（首次使用）

```bash
# 1. 安装后端依赖
cd backend
poetry install

# 2. 安装前端依赖
cd ../frontend
npm install

# 3. 使用启动中心启动
双击运行：bat-scripts\启动中心_增强版.bat
选择 [1] 增强版开发模式 或 [2] 基础开发模式
```

### 启动脚本说明

项目提供了多个启动脚本，整理如下：

#### 📂 bat-scripts（推荐使用）

| 脚本 | 用途 | 说明 |
|------|------|------|
| `启动中心_增强版.bat` | **主入口，推荐** | 统一菜单，包含所有启动选项 |
| `start-dev-pro.bat` | 增强版开发模式 | 智能检测、彩色输出 |
| `start-dev.bat` | 基础开发模式 | 一键启动基础设施+前后端 |
| `start-backend-only.bat` | 仅启动后端 | 后端开发专用 |
| `start-frontend-only.bat` | 仅启动前端 | 前端开发专用 |
| `init-data.bat` | 数据初始化 | 下载历史K线数据 |
| `check-status.bat` | 检查服务状态 | 一键检查所有服务 |
| `restart-all.bat` | 一键重启 | 停止-清理-重启一条龙 |
| `stop-all.bat` | 停止所有服务 | 开发结束后清理 |
| `clean-ports.bat` | 清理端口占用 | 端口冲突时使用 |

#### 📂 根目录启动脚本（独立调试用）

| 脚本 | 用途 | 端口 | 说明 |
|------|------|------|------|
| `start_evolution.bat` | 启动进化引擎 | 8001 | 独立调试进化服务 |
| `start_execution.bat` | 启动执行网关 | 8002 | 独立调试执行服务 |
| `start_panel.bat` | 启动后端面板 | 8000 | 独立调试后端API |
| `start_frontend.bat` | 启动前端 | 5173 | 独立调试前端 |

> **调试模式**: 根据调试规范，每个服务应在独立的终端标签页中运行。根目录的 `start_*.bat` 脚本专门用于此目的，可在 IDE 终端面板的不同标签页中分别运行各服务，便于查看实时日志。

#### 🔄 脚本关系说明

| 场景 | 推荐使用 | 原因 |
|------|---------|------|
| 日常启动 | `bat-scripts\启动中心_增强版.bat` | 统一菜单，操作简单 |
| 多服务调试 | 根目录 `start_*.bat` | 每个服务独立终端，日志清晰 |

### 首次使用流程

```
1. 确保本地 PostgreSQL 和 Redis 服务已启动
2. 运行 bat-scripts\启动中心_增强版.bat
3. 选择 [7] 数据初始化，下载历史K线数据
4. 选择 [1] 或 [3] 启动系统
5. 访问 http://localhost 查看前端界面
```

---

## 项目状态概览（2026-05-18）

```
总体完成度: ██████████ 100%

核心引擎:   ██████████ 100% ✅
├── 遗传编程引擎
├── 因子DSL+8族原语
├── 向量化回测引擎
└── 天勤桥接验证

交易执行:   ██████████ 100% ✅
├── 订单管理
├── 仓位跟踪
├── 风险控制
├── TQSDK对接
└── 执行网关

前端界面:   ██████████ 100% ✅
├── Dashboard ✅
├── EvolutionTree ✅
├── SymbolDetail ✅
├── ManualSwitch ✅
├── Trading ✅
├── LiveTrading ✅
├── EvolutionCenter ✅
└── 验证流程监控 ✅

自动化:     ████████░░ 80%  ⚠️
├── 候选状态机 ✅
├── 自动策略替换 ⚠️
├── 进化调度器 ⚠️
└── Regime引擎 ⚠️
```

### 当前优先级

**P0 - 核心缺失（阻塞实盘）**:
1. Regime状态识别引擎
2. 实时信号生成逻辑
3. 自动策略替换逻辑

**P1 - 重要增强**:
4. 进化调度器
5. WebSocket完整实现
6. 仓位对账

---

## 相关链接

- [项目根目录](../README.md)
- [项目进度](../PROGRESS.md)
- [技术债务](../TECH_DEBT.md)
- [开发规则](../.windsurf/rules/)（兼容 .trae/rules/）

---

*文档中心创建时间: 2026-05-17*  
*维护人: AI Assistant*
