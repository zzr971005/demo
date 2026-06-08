# 技术债务清单

> 每个TODO必须在此登记，并在解决后更新状态

## 债务统计

- 总债务数：6
- 待解决：0
- 已解决：6

## 债务明细

| ID | 位置 | 问题描述 | 引入时间 | 解决期限 | 状态 | 依赖任务 |
|---|---|---|---|---|---|---|
| TD001 | backend/app/api/routes/dashboard.py:77 | dashboard/summary 需从数据库查询真实数据 | 2025-05-16 | Task 9 完成时 | **已解决** | Task 9 |
| TD002 | backend/app/api/routes/dashboard.py:101 | dashboard/equity-curve 返回 501 Not Implemented | 2025-05-16 | Task 9 完成时 | **已解决** | Task 9 |
| TD003 | backend/app/api/routes/dashboard.py:127 | dashboard/alerts 返回 501 Not Implemented | 2025-05-16 | Task 9 完成时 | **已解决** | Task 9 |
| TD004 | backend/app/api/routes/symbols.py:116 | symbols/{symbol}/mode 切换逻辑返回 501 Not Implemented | 2025-05-16 | Task 10 完成时 | **已解决** | Task 10 |
| TD005 | backend/app/api/routes/symbols.py:69-90 | symbols/{symbol} 品种详情查询，部分字段为默认值 | 2025-05-16 | Task 9 完成时 | **已解决** | Task 9 |
| TD006 | backend/app/api/routes/symbols.py:41-61 | symbols 品种列表查询，部分字段为默认值 | 2025-05-16 | Task 9 完成时 | **已解决** | Task 9 |

## 解决记录

| ID | 解决时间 | 解决方式 | 验证人 |
|---|---|---|---|
| TD001-TD006 | 2026-05-18 | 创建 crud.py 数据库访问层，实现所有API端点从数据库查询真实数据 | 系统验证 |

---
**规则：每个TODO必须在引入后24小时内登记到此清单**
