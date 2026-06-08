# -*- coding: utf-8 -*-
"""
修复 start-dev-pro.bat 的延迟扩展问题
"""
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
bat_path = os.path.join(SCRIPT_DIR, 'start-dev-pro.bat')

with open(bat_path, 'r', encoding='gbk') as f:
    content = f.read()

# 修复延迟扩展问题
content = content.replace(
    'if "%INFRA_NEED_START%"=="1"',
    'if "!INFRA_NEED_START!"=="1"'
)
content = content.replace(
    'if "%BACKEND_NEED_START%"=="1"',
    'if "!BACKEND_NEED_START!"=="1"'
)
content = content.replace(
    'if "%FRONTEND_NEED_START%"=="1"',
    'if "!FRONTEND_NEED_START!"=="1"'
)

with open(bat_path, 'w', encoding='gbk') as f:
    f.write(content)

print('延迟扩展问题已修复')