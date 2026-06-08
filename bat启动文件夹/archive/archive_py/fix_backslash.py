# -*- coding: utf-8 -*-
"""
修复 start-dev-pro.bat 的反斜杠问题
"""
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
bat_path = os.path.join(SCRIPT_DIR, 'start-dev-pro.bat')

with open(bat_path, 'r', encoding='gbk') as f:
    content = f.read()

# 修复反斜杠问题
content = content.replace('%PROJECT_ROOTackend', '%PROJECT_ROOT%\\backend')
content = content.replace('%PROJECT_ROOT%\nrontend', '%PROJECT_ROOT%\\frontend')

# 修复其他可能的路径问题
content = content.replace('%PROJECT_ROOT%\\docker-compose.yml', '%PROJECT_ROOT%\\docker-compose.yml')

with open(bat_path, 'w', encoding='gbk') as f:
    f.write(content)

print('反斜杠问题已修复')
