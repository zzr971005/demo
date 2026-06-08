# 项目开发进度管理规则

> 基于 `.trae/rules/project-progress-management.md` 迁移
> 优先级：P0（最高）
> 适用范围：所有开发任务

## 核心原则

### 1. 文档只读原则

**开发进展记录时，必须新建md文件，禁止在旧md上修改。**

这是为了确保：
- 历史记录完整可追溯
- 避免误删或覆盖重要信息
- 便于审计和复盘

### 2. 开发前必读

**每次执行任务前，AI必须阅读以下文档：**

#### 必读书籍（按优先级排序）

| 优先级 | 文档路径 | 用途 | 何时阅读 |
|--------|----------|------|----------|
| P0 | `docs/specs/v1.0-working.md` | 当前开发规格书，包含需求、进度、待办 | **每次任务前必须阅读** |
| P0 | `docs/development-logs/INDEX.md` | 开发进展索引，了解已完成工作 | 任务前阅读 |
| P1 | `docs/README.md` | 文档中心入口，了解文档结构 | 首次接触项目时 |
| P1 | `docs/specs/CHANGELOG.md` | 规格书变更历史 | 需要了解变更时 |
| P2 | `.windsurf/rules/README.md` | 开发规则总览 | 首次接触项目时 |

#### 禁止行为

- 不阅读规格书直接开始编码
- 凭记忆推断项目进度
- 修改任何 `*-archived.md` 文件
- 修改任何开发进展记录文件

## 开发流程规范

### 阶段一：任务前准备（必须）

```
[ ] 1. 阅读 docs/specs/v1.0-working.md
   - 查看"与当前项目状态对比"了解已实现功能
   - 查看"待开发功能详细计划"确认本次任务
   - 记录任务对应的规格书章节

[ ] 2. 阅读 docs/development-logs/INDEX.md
   - 了解最新进展
   - 确认是否有相关历史记录

[ ] 3. 确认任务范围
   - 对照规格书确认需求
   - 确认验收标准
   - 预估工时
```

### 阶段二：开发执行

```
[ ] 1. 按照规格书实现功能
[ ] 2. 遵循代码规范（见 .windsurf/rules/core-rules.md）
[ ] 3. 添加必要的错误处理和日志
[ ] 4. 进行本地测试
```

### 阶段三：进展记录（必须）

```
[ ] 1. 创建新的进展记录文件
   文件名格式: docs/development-logs/YYYY-MM-DD-简短描述.md
   示例: docs/development-logs/2026-05-18-Regime引擎实现.md

[ ] 2. 按模板记录进展（见下方模板）

[ ] 3. 更新 docs/development-logs/INDEX.md
   - 在"按时间排序"表格添加新记录
   - 在"按模块分类"相应类别添加记录

[ ] 4. 更新 docs/specs/v1.0-working.md（如完成新功能）
   - 在"已实现功能"表格添加新条目
   - 在"待实现功能"表格标记为已完成
   - 更新"总体进度"可视化

[ ] 5. 在 docs/specs/CHANGELOG.md 记录变更
```

## 进展记录模板

### 文件命名

```
docs/development-logs/YYYY-MM-DD-简短中文描述.md

示例:
- 2026-05-18-Regime状态识别引擎实现.md
- 2026-05-19-验证流程监控页面开发.md
- 2026-05-20-实时信号生成逻辑完成.md
```

### 文件内容模板

```markdown
# 开发进展记录: [标题]

> **日期**: YYYY-MM-DD
> **任务**: [对应v1.0-working.md中的任务编号和名称]
> **规格书章节**: [第X章 X.X节]
> **开发者**: AI Assistant
> **工时**: X天
> **状态**: 已完成 / 部分完成 / 遇到问题

---

## 本次开发内容

### 功能描述
[简要描述本次开发的功能]

### 新增/修改文件

| 文件路径 | 类型 | 说明 |
|----------|------|------|
| backend/.../xxx.py | 新增 | 功能说明 |
| frontend/.../xxx.tsx | 修改 | 修改说明 |

### 关键技术点

1. [技术点1]
2. [技术点2]
3. [技术点3]

---

## 测试结果

### 测试方法
[描述如何测试的]

### 测试结果
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 手动测试通过

### 发现的问题
[如有问题，记录问题和解决方案]

---

## 与规格书对比

| 规格书要求 | 实现状态 | 备注 |
|------------|----------|------|
| 要求1 | 已实现 | |
| 要求2 | 部分实现 | 原因... |
| 要求3 | 未实现 | 计划... |

---

## 待办事项

- [ ] [后续任务1]
- [ ] [后续任务2]

---

## 相关文档

- [规格书相关章节](../specs/v1.0-working.md#章节)
- [相关代码文件](../../backend/...)

---

*记录创建时间: YYYY-MM-DD HH:MM*
*最后更新: YYYY-MM-DD HH:MM*
```

## 文档目录结构

```
docs/
├── README.md                          # 文档中心入口
├── PROJECT_DOCUMENTATION_PLAN.md      # 文档管理方案
├── GP_EVOLUTION_SYSTEM.md             # GP系统技术文档
├── specs/                             # 规格书目录
│   ├── README.md                      # 规格书使用指南
│   ├── v1.0-archived.md               # 原始规格书存档
│   ├── v1.0-working.md                # 工作规格书
│   └── CHANGELOG.md                   # 规格书变更历史
├── development-logs/                  # 开发进展记录
│   ├── README.md                      # 进展记录规则
│   ├── INDEX.md                       # 进展索引
│   └── YYYY-MM-DD-标题.md             # 具体进展记录
├── plans/                             # 开发计划
│   ├── 开发总结报告.md
│   └── 完整开发计划.md
├── logs/                              # 调试日志
│   └── 调试日志.md
└── archive/                           # 存档文件
    └── 期货自动进化因子挖掘系统_最终版开发规格书_v2.md
```

## 检查清单（AI自检用）

### 任务开始前

- [ ] 已阅读 `docs/specs/v1.0-working.md`
- [ ] 已阅读 `docs/development-logs/INDEX.md`
- [ ] 已确认任务对应的规格书章节
- [ ] 已了解相关历史进展

### 任务完成后

- [ ] 已创建新的进展记录文件（`docs/development-logs/YYYY-MM-DD-标题.md`）
- [ ] 已更新 `docs/development-logs/INDEX.md`
- [ ] 已更新 `docs/specs/v1.0-working.md`（如完成新功能）
- [ ] 已在 `docs/specs/CHANGELOG.md` 记录变更
- [ ] 已确认没有修改任何旧文件

## 违规后果

违反本规则的后果：
- 开发方向偏离需求
- 重复开发已完成功能
- 覆盖重要历史记录
- 项目进度混乱

**严重违规将导致代码审查不通过。**

## 附录：快速参考

### 常用文档路径

```
# 规格书
docs/specs/v1.0-working.md              # 工作规格书（必读）
docs/specs/v1.0-archived.md             # 存档规格书（只读）
docs/specs/CHANGELOG.md                 # 变更历史

# 进展记录
docs/development-logs/INDEX.md          # 进展索引（必读）
docs/development-logs/YYYY-MM-DD-*.md   # 具体进展

# 文档入口
docs/README.md                          # 文档中心
```

### 常用命令

```powershell
# 查看最新进展
cat docs/development-logs/INDEX.md

# 查看最新规格书
cat docs/specs/v1.0-working.md

# 创建新的进展记录（示例）
New-Item "docs/development-logs/2026-05-18-标题.md" -ItemType File
```
