---
description: 添加开发进展记录的标准流程
---

# 添加开发进展记录

## 步骤

1. **创建新文件**
   ```powershell
   $date = Get-Date -Format "yyyy-MM-dd"
   New-Item "docs/development-logs/$date-简短描述.md" -ItemType File
   ```

2. **按模板填写内容**
   - 参考 `docs/development-logs/README.md` 中的模板
   - 必须包含：日期、任务、新增/修改文件列表、测试结果

3. **更新索引**
   - 在 `docs/development-logs/INDEX.md` 中按时间和模块添加记录

4. **更新规格书（如完成新功能）**
   - 在 `docs/specs/v1.0-working.md` 中标记功能为已完成
   - 在 `docs/specs/CHANGELOG.md` 记录变更

## 禁止行为

- 修改已有的进展记录文件
- 遗漏 INDEX.md 更新
