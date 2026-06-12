
"""修复 Numba cache 问题"""
import re
from pathlib import Path

files_to_fix = [
    Path("quant_engine/validation/engine.py"),
    Path("quant_engine/validation/grid.py"),
    Path("quant_engine/factors/vector_index.py"),
    Path("quant_engine/factors/registry.py"),
]

pattern = re.compile(r'@jit\(nopython=True, cache=True\)')
replacement = '@jit(nopython=True, cache=False)'

for file_path in files_to_fix:
    if file_path.exists():
        content = file_path.read_text(encoding='utf-8')
        new_content = pattern.sub(replacement, content)
        file_path.write_text(new_content, encoding='utf-8')
        print(f"✓ 已修复: {file_path}")
    else:
        print(f"✗ 文件不存在: {file_path}")

print("\n修复完成!")
