@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM ��������Բ��Խű�
REM ============================================================

REM ��⵱ǰ���л���
if defined PSModulePath (
    echo [���] PowerShell ����
    echo [INFO] �л��� UTF-8 ����...
    chcp 65001 >nul 2>&1
) else (
    echo [���] cmd ����
    echo [INFO] �л��� GBK ����...
    chcp 936 >nul 2>&1
)

echo.
echo ����������ʾ: ��ã����磡
echo ���Բ˵�ѡ��: [1] ѡ��һ [2] ѡ���
echo.
echo ��ǰ����ҳ:
chcp
echo.
pause
