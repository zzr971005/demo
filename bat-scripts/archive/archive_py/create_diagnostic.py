# -*- coding: utf-8 -*-
"""
创建诊断批处理文件
"""
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

bat_content = """@echo off
chcp 936 >nul 2>&1
title 诊断测试 - 期货自动进化因子挖掘系统

echo [诊断] 测试脚本开始
echo.

REM 测试1：检查菜单选项
echo [诊断1] 测试菜单选项
echo.
echo 选项菜单:
echo   [1] 选项1
echo   [5] 智能启动
echo   [0] 退出
echo.

set /p choice=请选择选项 [0-5]:

if "%choice%"=="0" goto :exit
if "%choice%"=="1" goto :option1
if "%choice%"=="5" goto :option5

echo [ERR] 无效选项，请重新选择
timeout /t 2 /nobreak >nul
goto :menu

:menu
cls
echo [诊断] 返回菜单
timeout /t 1 /nobreak >nul
goto :diagnostic_menu

:diagnostic_menu
cls
echo [诊断] 新的菜单
echo.
echo   [5] 智能启动
echo   [0] 退出
echo.
set /p choice2=请选择 [0-5]:
if "%choice2%"=="0" goto :exit
if "%choice2%"=="5" goto :option5
echo [ERR] 无效
timeout /t 2 /nobreak >nul
goto :menu

:option1
echo [INFO] 执行选项1
echo [测试] 暂停3秒...
timeout /t 3 /nobreak >nul
goto :exit

:option5
echo.
echo [INFO] 执行智能启动选项
echo [诊断] 模拟智能启动逻辑...
echo [诊断] 检查服务状态...
echo [诊断] 这部分执行完后应该返回菜单
timeout /t 2 /nobreak >nul
echo [诊断] 即将返回菜单
goto :menu

:exit
echo.
echo [诊断] 脚本执行完成
pause
exit /b 0
"""

with open(os.path.join(SCRIPT_DIR, 'diagnostic.bat'), 'w', encoding='gbk') as f:
    f.write(bat_content)

print('diagnostic.bat 已创建')