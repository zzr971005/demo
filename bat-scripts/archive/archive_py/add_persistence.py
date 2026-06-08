# -*- coding: utf-8 -*-
"""
在 start-dev-pro.bat 中添加窗口持久化命令，防止闪退
"""
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
bat_path = os.path.join(SCRIPT_DIR, 'start-dev-pro.bat')

with open(bat_path, 'r', encoding='gbk') as f:
    content = f.read()

# 在 :start_process 的 timeout 之后添加持久化保护
# 将可能导致闪退的代码用 pause 包围
old_code = '''echo [DEBUG] pause 完成，继续执行...
echo [DEBUG] 即将检查基础设施...
timeout /t 1 /nobreak >nul

REM 启动基础设施
if "!INFRA_NEED_START!"=="1" ('''

new_code = '''echo [DEBUG] pause 完成，继续执行...
echo [DEBUG] 即将检查基础设施...
timeout /t 1 /nobreak >nul
echo [DEBUG] 开始检查基础设施...
echo [DEBUG] 按任意键继续（防止闪退）...
pause >nul

REM 启动基础设施
if "!INFRA_NEED_START!"=="1" ('''

content = content.replace(old_code, new_code)

# 在文件末尾添加持久化保护
if 'pause >nul' in content and content.endswith('pause >nul\n'):
    # 在最后一个 pause >nul 前添加更多保护
    content = content.replace(
        'echo  按任意键关闭此窗口（服务将继续运行...\npause >nul',
        'echo  按任意键关闭此窗口（服务将继续运行...\necho [DEBUG] 脚本执行完成，窗口即将关闭...\npause >nul'
    )

with open(bat_path, 'w', encoding='gbk') as f:
    f.write(content)

print('窗口持久化命令已添加')