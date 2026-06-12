# -*- coding: utf-8 -*-
"""
修复 start-dev-pro.bat 的颜色变量定义
"""
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
bat_path = os.path.join(SCRIPT_DIR, 'start-dev-pro.bat')

with open(bat_path, 'r', encoding='gbk') as f:
    content = f.read()

# 找到颜色变量定义部分并替换
old_colors = '''set "ESC=
set "COLOR_GREEN=%ESC%[32m"
set "COLOR_YELLOW=%ESC%[33m"
set "COLOR_CYAN=%ESC%[36m"
set "COLOR_RED=%ESC%[31m"
set "COLOR_RESET=%ESC%[0m"'''

# 正确的 ESC 变量定义（使用 ANSI 转义字符）
# 在批处理中，可以用以下方式定义 ESC：
new_colors = '''REM 定义颜色变量
for /F %%a in ('echo prompt $E ^| cmd') do set "ESC=%%a"
set "COLOR_GREEN=%ESC%[32m"
set "COLOR_YELLOW=%ESC%[33m"
set "COLOR_CYAN=%ESC%[36m"
set "COLOR_RED=%ESC%[31m"
set "COLOR_RESET=%ESC%[0m"'''

if old_colors in content:
    content = content.replace(old_colors, new_colors)
    with open(bat_path, 'w', encoding='gbk') as f:
        f.write(content)
    print('颜色变量已修复')
else:
    print('未找到需要修复的颜色变量定义')
    # 输出第40-50行看看实际内容
    lines = content.split('\n')[39:50]
    for i, line in enumerate(lines, 40):
        print(f'{i+1}: {repr(line)}')