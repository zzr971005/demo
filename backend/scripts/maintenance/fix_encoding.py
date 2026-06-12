
"""修复文件编码问题"""
import re
from pathlib import Path

file_path = Path("quant_engine/factors/registry.py")
content = file_path.read_text(encoding='utf-8')

# 替换所有被破坏的 UTF-8 字符
# \ufffd 是替换字符，表示编码错误
content = content.replace('\ufffd?""', '"""')
content = content.replace('\ufffd?', '')
content = content.replace('\ufffd', '')

file_path.write_text(content, encoding='utf-8')
print("✓ 已修复 registry.py 编码问题")
