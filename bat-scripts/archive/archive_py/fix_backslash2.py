# -*- coding: utf-8 -*-
"""
修复 start-dev-pro.bat 的反斜杠问题 - 使用原始字符串
"""
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
bat_path = os.path.join(SCRIPT_DIR, 'start-dev-pro.bat')

# 读取文件为字节
with open(bat_path, 'rb') as f:
    content_bytes = f.read()

# 转换为字符串
try:
    content = content_bytes.decode('gbk')
except:
    content = content_bytes.decode('utf-8')

# 修复反斜杠问题 - 使用原始字符串
old_backend = r'set "BACKEND_PATH=%PROJECT_ROOTackend"'
new_backend = r'set "BACKEND_PATH=%PROJECT_ROOT%\backend"'

old_frontend = 'set "FRONTEND_PATH=%PROJECT_ROOT%\nrontend"'
new_frontend = r'set "FRONTEND_PATH=%PROJECT_ROOT%\frontend"'

content = content.replace(old_backend, new_backend)
content = content.replace(old_frontend, new_frontend)

# 写回文件
with open(bat_path, 'w', encoding='gbk') as f:
    f.write(content)

print('反斜杠问题已修复')
print('检查第13-14行:')
lines = content.split('\n')
for i in range(12, 14):
    print(f'{i+1}: {lines[i]}')
