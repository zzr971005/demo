# -*- coding: utf-8 -*-
"""
在 start-dev-pro.bat 的启动后端部分添加详细调试
"""
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
bat_path = os.path.join(SCRIPT_DIR, 'start-dev-pro.bat')

with open(bat_path, 'r', encoding='gbk') as f:
    content = f.read()

# 在启动后端之前添加详细调试
old_backend_start = '''REM 启动后端
if "%BACKEND_NEED_START%"=="1" (
    echo.
    echo  %COLOR_CYAN%[8/9]%COLOR_RESET% 启动后端服务...'''

new_backend_start = '''REM 启动后端
if "%BACKEND_NEED_START%"=="1" (
    echo.
    echo [DEBUG] 准备启动后端服务
    echo [DEBUG] BACKEND_PATH=%BACKEND_PATH%
    echo [DEBUG] PYTHON=%PYTHON%
    echo [DEBUG] BACKEND_PORT=%BACKEND_PORT%
    echo [DEBUG] 检查 PYTHON 是否存在...
    if exist "%PYTHON%" (
        echo [DEBUG] PYTHON 路径有效
    ) else (
        echo [DEBUG] PYTHON 路径不存在！
    )
    echo [DEBUG] 按任意键继续启动后端...
    pause >nul
    echo.
    echo  %COLOR_CYAN%[8/9]%COLOR_RESET% 启动后端服务...'''

content = content.replace(old_backend_start, new_backend_start)

with open(bat_path, 'w', encoding='gbk') as f:
    f.write(content)

print('后端启动部分调试代码已添加')