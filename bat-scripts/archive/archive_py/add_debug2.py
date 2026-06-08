# -*- coding: utf-8 -*-
"""
在 start-dev-pro.bat 的智能启动部分添加调试输出
"""
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
bat_path = os.path.join(SCRIPT_DIR, 'start-dev-pro.bat')

with open(bat_path, 'r', encoding='gbk') as f:
    content = f.read()

# 在 :start_smart 标签后添加调试代码
old_start_smart = '''
:start_smart
echo.
echo  %COLOR_YELLOW%[INFO]%COLOR_RESET% 智能启动模式，仅启动缺失的服务     
goto :start_process
'''

new_start_smart = '''
:start_smart
echo.
echo [DEBUG] 进入 :start_smart
echo  %COLOR_YELLOW%[INFO]%COLOR_RESET% 智能启动模式，仅启动缺失的服务     
echo [DEBUG] 当前 INFRA_NEED_START=%INFRA_NEED_START%
echo [DEBUG] 当前 BACKEND_NEED_START=%BACKEND_NEED_START%
echo [DEBUG] 当前 FRONTEND_NEED_START=%FRONTEND_NEED_START%
echo [DEBUG] 按任意键继续...
pause >nul
goto :start_process
'''

content = content.replace(old_start_smart, new_start_smart)

# 在 :start_process 标签后添加调试代码
old_start_process = '''
:start_process
echo.

REM 启动基础设施
'''

new_start_process = '''
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

content = content.replace(old_start_process, new_start_process)

with open(bat_path, 'w', encoding='gbk') as f:
    f.write(content)

print('智能启动部分调试代码已添加')