@echo off
setlocal

title Test

set "SCRIPT_DIR=%~dp0"

echo Hello World
echo SCRIPT_DIR=%SCRIPT_DIR%
pause

endlocal
exit /b 0