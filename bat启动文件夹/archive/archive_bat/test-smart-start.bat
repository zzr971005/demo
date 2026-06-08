@echo off
setlocal enabledelayedexpansion

chcp 936 >nul 2>&1

title 测试脚本

echo ========================================
echo 测试: 智能启动逻辑
echo ========================================

set INFRA_NEED_START=0
set BACKEND_NEED_START=1
set FRONTEND_NEED_START=1

echo 模拟状态:
echo   基础设施: %INFRA_NEED_START% (0=已运行, 1=需启动)
echo   后端服务: %BACKEND_NEED_START% (0=已运行, 1=需启动)
echo   前端服务: %FRONTEND_NEED_START% (0=已运行, 1=需启动)
echo.

:start_smart
echo [INFO] 智能启动模式 - 仅启动未运行的服务
if %%INFRA_NEED_START%% equ 1 (
    echo [INFO] 基础设施需要启动，跳转到 start_infra
    goto :start_infra
)
echo [INFO] 基础设施已运行，跳转到 start_services
goto :start_services

:start_infra
echo [INFO] 这里会启动基础设施...
goto :start_services

:start_services
echo.
echo [INFO] 在 start_services 中:
if %%BACKEND_NEED_START%% equ 1 (
    echo   - 将启动后端服务
)
if %%FRONTEND_NEED_START%% equ 1 (
    echo   - 将启动前端服务
)
echo.
echo [OK] 测试完成，脚本应该不会闪退
pause
exit /b 0
