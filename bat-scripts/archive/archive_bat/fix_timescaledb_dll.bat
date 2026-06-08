@echo off
echo [INFO] Fixing TimescaleDB DLL naming...

cd /d "C:\Program Files\PostgreSQL\17\lib"
copy /Y "timescaledb-tsl-2.27.0.dll" "timescaledb-2.27.0.dll" >nul 2>&1
echo [INFO] Copied timescaledb-tsl-2.27.0.dll -> timescaledb-2.27.0.dll

REM Restart PostgreSQL
echo [INFO] Restarting PostgreSQL service...
net stop postgresql-x64-17 >nul 2>&1
net start postgresql-x64-17 >nul 2>&1
echo [SUCCESS] PostgreSQL restarted!
pause