# 清理脚本

本目录包含各种数据清理脚本。

## 脚本说明

### clean_all_data.py
原始的清理脚本，功能较简单。

### clean_all_data_complete.py
完整版清理脚本，包含级联删除逻辑。

### clean_all_data_enhanced.py
增强版清理脚本，支持更多数据表和完整性检查。

### clean_data_simple.py
简化版清理脚本，只清理核心数据表，避免数据库字段问题。

### clear_and_restart.py
快速清理并重启的脚本。

### clean_dirty_data.py
清理脏数据的脚本。

## 使用方法

```bash
# 使用统一入口
python scripts/run.py cleanup clean_data_simple.py

# 直接运行
python scripts/cleanup/clean_data_simple.py
```

## 注意事项

1. 清理数据前请确认是否需要备份
2. 建议先运行 summary 查看数据量
3. 清理后可以运行 validate 验证完整性
