# -*- coding: utf-8 -*-
"""
修复 start-dev-pro.bat 的虚拟环境检测逻辑
"""
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
bat_path = os.path.join(SCRIPT_DIR, 'start-dev-pro.bat')

# 读取文件
with open(bat_path, 'r', encoding='gbk') as f:
    content = f.read()

# 定义旧代码和新代码
old_code = '''REM 检查 Python 虚拟环境
echo    - Python 虚拟环境...
for /f "delims=" %%i in ('cd /d "%BACKEND_PATH%" ^& poetry env info --path 2^>nul') do set "VENV_PATH=%%i"
if not defined VENV_PATH (
    set "VENV_PATH=%BACKEND_PATH%\.venv"
)
set "PYTHON=%VENV_PATH%\\Scripts\\python.exe"

if not exist "%PYTHON%" (
    echo      %COLOR_YELLOW%[INFO] Poetry 虚拟环境未找到，正在创建...%COLOR_RESET%
    cd /d "%BACKEND_PATH%"
    poetry install
    if errorlevel 1 (
        echo      %COLOR_RED%[ERR] 虚拟环境创建失败%COLOR_RESET%
        pause
        exit /b 1
    )
    for /f "delims=" %%i in ('cd /d "%BACKEND_PATH%" ^& poetry env info --path 2^>nul') do set "VENV_PATH=%%i"
    set "PYTHON=%VENV_PATH%\\Scripts\\python.exe"
)'''

new_code = '''REM 检查 Python 虚拟环境
echo    - Python 虚拟环境...
for /f "delims=" %%i in ('cd /d "%BACKEND_PATH%" ^& poetry env info --path 2^>nul') do set "VENV_PATH=%%i"

if not defined VENV_PATH (
    echo      %COLOR_YELLOW%[INFO] Poetry 虚拟环境未找到，正在创建...%COLOR_RESET%
    cd /d "%BACKEND_PATH%"
    poetry install --no-interaction
    if errorlevel 1 (
        echo      %COLOR_RED%[ERR] 虚拟环境创建失败%COLOR_RESET%
        pause
        exit /b 1
    )
    for /f "delims=" %%i in ('cd /d "%BACKEND_PATH%" ^& poetry env info --path 2^>nul') do set "VENV_PATH=%%i"
)

if not defined VENV_PATH (
    echo      %COLOR_RED%[ERR] 无法获取虚拟环境路径%COLOR_RESET%
    pause
    exit /b 1
)

set "PYTHON=%VENV_PATH%\\Scripts\\python.exe"

if not exist "%PYTHON%" (
    echo      %COLOR_RED%[ERR] Python 可执行文件不存在: %PYTHON%%COLOR_RESET%
    pause
    exit /b 1
)'''

# 替换代码
if old_code in content:
    content = content.replace(old_code, new_code)
    with open(bat_path, 'w', encoding='gbk') as f:
        f.write(content)
    print('修复成功')
else:
    print('未找到需要替换的代码块')
    # 输出文件前80行看看实际内容
    print('\n文件前80行:')
    lines = content.split('\n')[:80]
    for i, line in enumerate(lines, 1):
        print(f'{i}: {line}')