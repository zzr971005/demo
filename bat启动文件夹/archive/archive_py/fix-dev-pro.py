# -*- coding: utf-8 -*-
"""
修复 start-dev-pro.bat 的无效选项处理逻辑
"""
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 读取 GBK 编码的文件
with open(os.path.join(SCRIPT_DIR, 'start-dev-pro.bat'), 'r', encoding='gbk') as f:
    content = f.read()

# 替换无效选项处理逻辑
old_code = 'echo  %COLOR_RED%[ERR] 无效选项%COLOR_RESET%\npause\nexit /b 1'
new_code = 'echo  %COLOR_RED%[ERR] 无效选项，请重新选择%COLOR_RESET%\ntimeout /t 2 /nobreak >nul\ngoto :menu'

content = content.replace(old_code, new_code)

# 写回 GBK 编码的文件
with open(os.path.join(SCRIPT_DIR, 'start-dev-pro.bat'), 'w', encoding='gbk') as f:
    f.write(content)

print('start-dev-pro.bat 已修复')