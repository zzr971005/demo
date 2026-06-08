# -*- coding: utf-8 -*-
"""
诊断批处理文件闪退问题
"""
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 创建测试脚本
test_bat = r"""@echo off
chcp 936 >nul 2>&1
echo [DEBUG] 测试脚本开始执行
echo [DEBUG] 当前目录: %cd%
echo [DEBUG] 脚本目录: %~dp0
echo.

set "PROJECT_ROOT=%~dp0.."
for %%I in ("%PROJECT_ROOT%") do set "PROJECT_ROOT=%%~fI"
echo [DEBUG] 项目根目录: %PROJECT_ROOT%

echo.
echo 测试菜单:
echo   [1] 测试选项1
echo   [2] 测试选项2  
echo   [5] 测试智能启动
echo   [0] 退出
echo.

set /p choice=请选择选项 [0-5]: 

if "%choice%"=="0" goto :exit_script
if "%choice%"=="1" goto :option1
if "%choice%"=="2" goto :option2
if "%choice%"=="5" goto :option5

echo [ERR] 无效选项
timeout /t 2 /nobreak >nul
goto :menu

:option1
echo [INFO] 执行选项1
goto :exit_script

:option2
echo [INFO] 执行选项2
goto :exit_script

:option5
echo [INFO] 执行智能启动选项
echo [DEBUG] 检查基础设施状态...
docker-compose -f "%PROJECT_ROOT%\docker-compose.yml" ps timescaledb 2>&1 | findstr "Up" >nul
if errorlevel 1 (
    echo [DEBUG] TimescaleDB 未运行
) else (
    echo [DEBUG] TimescaleDB 运行中
)
goto :exit_script

:exit_script
echo.
echo [DEBUG] 脚本执行完成
pause
exit /b 0
"""

with open(os.path.join(SCRIPT_DIR, 'debug-test.bat'), 'w', encoding='gbk') as f:
    f.write(test_bat)

print('调试脚本已创建: debug-test.bat')