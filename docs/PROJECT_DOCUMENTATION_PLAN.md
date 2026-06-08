# 项目文档管理方案

> **制定日期**: 2026-05-17  
> **版本**: v1.0  
> **状态**: 待评审

---

## 一、当前MD文件现状分析

### 1.1 现有MD文件清单

| 路径 | 文件名 | 当前用途 | 问题 |
|------|--------|----------|------|
| `/` | `README.md` | 项目根说明 | ✅ 保留 |
| `/` | `PROGRESS.md` | 项目进度追踪 | ⚠️ 内容过长，需拆分 |
| `/` | `TECH_DEBT.md` | 技术债务 | ✅ 保留 |
| `/` | `期货自动进化因子挖掘系统_最终版开发规格书_v2.md` | **主规格书** | ⚠️ 需存档保护 |
| `/doc/` | `开发总结报告.md` | 开发总结 | ⚠️ 位置不当，应移至docs |
| `/doc/` | `完整开发计划.md` | 开发计划 | ⚠️ 与规格书内容重复 |
| `/doc/` | `调试日志.md` | 调试记录 | ⚠️ 应移至docs/logs |
| `/docs/` | `GP_EVOLUTION_SYSTEM.md` | GP系统文档 | ✅ 保留 |
| `/docs/development-logs/` | `README.md` | 进展记录规则 | ✅ 保留 |
| `/docs/development-logs/` | `INDEX.md` | 进展索引 | ✅ 保留 |
| `/docs/development-logs/` | `2026-05-17-完整交易执行系统.md` | 进展记录 | ✅ 保留 |
| `/.windsurf/specs/auto-evolve-factor-mining/` | `spec.md` | AI开发规格 | ✅ 保留（AI专用，Windsurf） |
| `/.windsurf/specs/auto-evolve-factor-mining/` | `tasks.md` | 任务清单 | ✅ 保留（AI专用，Windsurf） |
| `/.windsurf/specs/auto-evolve-factor-mining/` | `tasks-with-acceptance.md` | 验收标准 | ✅ 保留（AI专用，Windsurf） |
| `/.windsurf/specs/auto-evolve-factor-mining/` | `checklist.md` | 检查清单 | ✅ 保留（AI专用，Windsurf） |
| `/.windsurf/specs/auto-evolve-factor-mining/` | `execution-rules.md` | 执行规则 | ✅ 保留（AI专用，Windsurf） |
| `/.windsurf/rules/` | `*.md` (3个) | 开发规则 | ✅ 保留（AI专用，Windsurf） |
| `/.trae/specs/auto-evolve-factor-mining/` | `spec.md` | AI开发规格 | ✅ 保留（AI专用，Trae） |
| `/.trae/specs/auto-evolve-factor-mining/` | `tasks.md` | 任务清单 | ✅ 保留（AI专用，Trae） |
| `/.trae/specs/auto-evolve-factor-mining/` | `tasks-with-acceptance.md` | 验收标准 | ✅ 保留（AI专用，Trae） |
| `/.trae/specs/auto-evolve-factor-mining/` | `checklist.md` | 检查清单 | ✅ 保留（AI专用，Trae） |
| `/.trae/specs/auto-evolve-factor-mining/` | `execution-rules.md` | 执行规则 | ✅ 保留（AI专用，Trae） |
| `/.trae/rules/` | `*.md` (6个) | 开发规则 | ✅ 保留（AI专用，Trae） |

### 1.2 核心问题识别

1. **规格书分散**: 根目录和 `.trae/specs/` 都有规格书，内容有重叠
2. **文档位置混乱**: `doc/` 和 `docs/` 并存，用途不明确
3. **无版本控制**: 规格书修改后无历史存档
4. **缺失待办追踪**: 已完成/待完成内容分散在各文件中

---

## 二、MD文件重组方案

### 2.1 目标目录结构

```
d:\期货自动进化因子挖掘系统\
├── README.md                          # 项目入口（精简版）
├── PROGRESS.md                        # 当前进度总览（精简版）
├── docs\
│   ├── README.md                      # 文档中心入口
│   ├── ARCHITECTURE.md                # 系统架构文档
│   ├── API.md                         # API接口文档
│   ├── DEPLOYMENT.md                  # 部署指南
│   ├── specs\
│   │   ├── README.md                  # 规格书说明
│   │   ├── v1.0-archived.md           # 原始规格书（只读存档）
│   │   ├── v1.0-working.md            # 工作副本（可修改）
│   │   ├── v1.1-draft.md              # 下一版本草稿（可选）
│   │   └── CHANGELOG.md               # 规格书变更历史
│   ├── development-logs\
│   │   ├── README.md                  # 进展记录规则
│   │   ├── INDEX.md                   # 进展索引
│   │   └── YYYY-MM-DD-标题.md         # 进展记录文件
│   ├── plans\
│   │   └── YYYY-MM-DD-功能名.md       # 开发计划
│   └── logs\
│       └── YYYY-MM-DD-调试.md         # 调试日志
├── .windsurf\
│   ├── specs\                         # AI开发规格（Windsurf）
│   ├── rules\                         # 开发规则（Windsurf）
│   └── workflows\                     # 开发工作流（Windsurf）
├── .trae\
│   ├── specs\                         # AI开发规格（Trae，保留不动）
│   └── rules\                         # 开发规则（Trae，保留不动）
└── [其他代码目录]
```

### 2.2 文件用途定义

| 目录 | 用途 | 写入规则 |
|------|------|----------|
| `docs/specs/` | 项目规格书 | 存档版只读，工作版可修改 |
| `docs/development-logs/` | 开发进展记录 | 每次开发后新建文件，禁止修改旧文件 |
| `docs/plans/` | 开发计划 | 每个功能一个文件，可更新 |
| `docs/logs/` | 调试日志 | 按日期新建 |
| `.windsurf/specs/` | AI开发规格 | 保留给AI使用，人工不直接修改 |
| `.windsurf/rules/` | 开发规则 | 保留给AI使用 |
| `.windsurf/workflows/` | 开发工作流 | 保留给AI使用 |
| `.trae/specs/` | AI开发规格（Trae兼容） | 保留给AI使用，人工不直接修改 |
| `.trae/rules/` | 开发规则（Trae兼容） | 保留给AI使用 |

---

## 三、规格书管理规则

### 3.1 版本命名规范

```
版本号格式: v{主版本}.{次版本}-{状态}

示例:
- v1.0-archived    # 已存档的正式版本
- v1.0-working     # 当前工作版本
- v1.1-draft       # 草稿版本
- v2.0-beta        # 测试版本
```

### 3.2 规格书文件头模板

```markdown
# 期货自动进化因子挖掘系统 — 开发规格书

> **版本**: v1.0-working  
> **状态**: 工作中（基于v1.0-archived修改）  
> **最后更新**: 2026-05-17 14:30:00  
> **变更人**: AI Assistant  
> **变更说明**: 添加缺失功能清单和开发计划  
> **父版本**: v1.0-archived  

---

## 文档用途

本文档是项目开发的**权威参考规格书**，包含：
- 系统功能需求
- 技术架构设计
- 开发验收标准
- 待办事项追踪

**使用规则**:
1. 开发前必须对照本文档确认需求
2. 任何变更必须在CHANGELOG.md中记录
3. 完成的功能需标记✅并注明完成日期

---

## 与当前项目状态对比（2026-05-17）

### 已实现功能 ✅

| 功能 | 规格书章节 | 实现状态 | 完成日期 |
|------|-----------|----------|----------|
| 遗传编程引擎 | 第4章 | ✅ 100% | 2026-05-15 |
| 交易执行系统 | 第6章 | ✅ 100% | 2026-05-17 |
| ... | ... | ... | ... |

### 待实现功能 ❌

| 功能 | 规格书章节 | 优先级 | 计划完成日期 |
|------|-----------|--------|-------------|
| 验证流程监控 | 第8章 | P0 | 待定 |
| Regime状态识别 | 第5章 | P0 | 待定 |
| ... | ... | ... | ... |

---
```

### 3.3 变更记录规则（CHANGELOG.md）

```markdown
# 规格书变更历史

## 变更记录格式

| 日期 | 版本 | 变更人 | 变更类型 | 变更内容摘要 | 影响范围 |
|------|------|--------|----------|-------------|----------|
| 2026-05-17 | v1.0-working | AI Assistant | 新增 | 添加缺失功能清单 | 第9章 |
| 2026-05-17 | v1.0-working | AI Assistant | 修改 | 更新交易执行API | 第6章 |

## 变更类型定义

- **新增**: 添加新功能/章节
- **修改**: 修改现有内容
- **删除**: 删除过时内容
- **修正**: 修正错误
- **存档**: 版本存档

## 详细变更记录

### 2026-05-17 14:30:00 - v1.0-working 创建

**变更人**: AI Assistant  
**父版本**: v1.0-archived  
**变更原因**: 基于原始规格书创建工作副本，添加进度追踪  

**具体变更**:
1. 添加"与当前项目状态对比"章节
2. 添加"待实现功能清单"章节
3. 标记所有已实现功能

**影响文件**: v1.0-working.md
```

---

## 四、实施步骤

### Step 1: 存档原始规格书（只读保护）

**操作**:
1. 将 `期货自动进化因子挖掘系统_最终版开发规格书_v2.md` 复制到 `docs/specs/v1.0-archived.md`
2. 在文件头添加存档标记：

```markdown
> **⚠️ 存档版本 - 禁止修改 ⚠️**  
> **存档日期**: 2026-05-17  
> **存档原因**: 原始规格书，作为后续版本基准  
> **原始路径**: /期货自动进化因子挖掘系统_最终版开发规格书_v2.md  
> **状态**: 只读存档  
```

### Step 2: 创建工作副本

**操作**:
1. 复制 `v1.0-archived.md` 到 `docs/specs/v1.0-working.md`
2. 添加工作副本文件头（见3.2模板）
3. 添加"与当前项目状态对比"章节

### Step 3: 整理现有文档

**操作**:
1. 将 `doc/开发总结报告.md` 移动到 `docs/` 根目录
2. 将 `doc/完整开发计划.md` 内容合并到 `v1.0-working.md`
3. 将 `doc/调试日志.md` 移动到 `docs/logs/`
4. 删除空 `doc/` 目录

### Step 4: 更新PROGRESS.md

**操作**:
1. 精简 `PROGRESS.md` 为摘要版本
2. 添加指向详细文档的链接
3. 保留核心统计信息

### Step 5: 创建文档入口

**操作**:
1. 创建 `docs/README.md` 作为文档中心入口
2. 创建 `docs/specs/README.md` 说明规格书使用方法

---

## 五、后续维护规则

### 5.1 每日维护

- 开发完成后在 `development-logs/` 新建进展记录
- 更新 `PROGRESS.md` 中的完成状态

### 5.2 每周维护

- 更新 `v1.0-working.md` 中的进度对比章节
- 在 `CHANGELOG.md` 记录本周变更

### 5.3 版本升级

当需要发布新版本时：
1. 将 `v1.0-working.md` 复制为 `v1.0-archived.md`（覆盖旧存档）
2. 或创建 `v1.1-working.md` 开始新版本
3. 在 `CHANGELOG.md` 记录版本发布

---

## 六、待讨论事项

1. **`.windsurf/` 和 `.trae/` 双IDE配置管理**
   - 建议：同时保留，Windsurf 为主用，Trae 为备选
   - `.windsurf/rules/` 精简合并为3个核心规则文件
   - `.trae/rules/` 保持原样不动作为历史备份

2. **如何处理 `GP_EVOLUTION_SYSTEM.md`？**
   - 建议：移动到 `docs/architecture/` 作为技术架构文档

3. **是否需要删除原始根目录规格书？**
   - 建议：删除，保留存档在 `docs/specs/v1.0-archived.md`

---

**方案制定**: 2026-05-17  
**制定人**: AI Assistant  
**状态**: 待用户评审
