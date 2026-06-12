@echo off
chcp 936 >nul 2>&1
echo 测试 pause 命令
echo 您应该看到下面的 '按任意键继续...'
pause
echo 测试完成
exit /b 0
