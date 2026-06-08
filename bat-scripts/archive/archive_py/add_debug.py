# -*- coding: utf-8 -*-
"""
在 start-dev-pro.bat 开头添加调试输出
"""
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
bat_path = os.path.join(SCRIPT_DIR, 'start-dev-pro.bat')

with open(bat_path, 'r', encoding='gbk') as f:
    content = f.read()

# 在 title 行后添加调试输出
debug_code = '''
REM ====== 调试代码 ======
echo [DEBUG] start-dev-pro.bat 开始执行
echo [DEBUG] SCRIPT_DIR=%SCRIPT_DIR%
echo [DEBUG] PROJECT_ROOT=%PROJECT_ROOT%
echo [DEBUG] BACKEND_PATH=%BACKEND_PATH%
echo [DEBUG] FRONTEND_PATH=%FRONTEND_PATH%
echo [DEBUG] 按任意键继续...
pause >nul
REM ====== 调试代码结束 ======
'''

# 在 "title 开发模式 - 期货自动进化因子挖掘系统" 后插入调试代码
old_title = 'title 开发模式 - 期货自动进化因子挖掘系统'
new_title = 'title 开发模式 - 期货自动进化因子挖掘系统\n' + debug_code

content = content.replace(old_title, new_title, 1)

with open(bat_path, 'w', encoding='gbk') as f:
    f.write(content)

print('调试代码已添加')