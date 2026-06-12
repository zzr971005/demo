# -*- coding: utf-8 -*-
"""
在 pause 之后立即添加调试输出
"""
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
bat_path = os.path.join(SCRIPT_DIR, 'start-dev-pro.bat')

with open(bat_path, 'r', encoding='gbk') as f:
    content = f.read()

# 在 :start_process 的 pause >nul 之后添加调试输出
old_pause = '''
:start_process
echo.
echo [DEBUG] 进入 :start_process
echo [DEBUG] INFRA_NEED_START=%INFRA_NEED_START%
echo [DEBUG] BACKEND_NEED_START=%BACKEND_NEED_START%
echo [DEBUG] FRONTEND_NEED_START=%FRONTEND_NEED_START%
echo [DEBUG] 按任意键继续...
pause >nul

REM 启动基础设施
'''

new_pause = '''
:start_process
echo.
echo [DEBUG] 进入 :start_process
echo [DEBUG] INFRA_NEED_START=%INFRA_NEED_START%
echo [DEBUG] BACKEND_NEED_START=%BACKEND_NEED_START%
echo [DEBUG] FRONTEND_NEED_START=%FRONTEND_NEED_START%
echo [DEBUG] 按任意键继续...
pause >nul
echo [DEBUG] pause 完成，继续执行...
echo [DEBUG] 即将检查基础设施...
timeout /t 1 /nobreak >nul

REM 启动基础设施
'''

content = content.replace(old_pause, new_pause)

with open(bat_path, 'w', encoding='gbk') as f:
    f.write(content)

print('pause 后调试代码已添加')