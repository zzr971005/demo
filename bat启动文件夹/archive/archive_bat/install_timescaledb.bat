@echo off
echo [INFO] Installing TimescaleDB for PostgreSQL 17...

set PG_LIB="C:\Program Files\PostgreSQL\17\lib"
set PG_EXT="C:\Program Files\PostgreSQL\17\share\extension"
set SRC="%TEMP%\timescaledb\timescaledb"

if not exist %SRC% (
    echo [ERROR] TimescaleDB source not found at %SRC%
    exit /b 1
)

echo [INFO] Copying DLL files...
copy /Y "%SRC%\timescaledb.dll" %PG_LIB% >nul 2>&1
copy /Y "%SRC%\timescaledb-tsl-2.27.0.dll" %PG_LIB% >nul 2>&1

echo [INFO] Copying extension files...
copy /Y "%SRC%\timescaledb.control" %PG_EXT% >nul 2>&1
copy /Y "%SRC%\timescaledb--*.sql" %PG_EXT% >nul 2>&1
copy /Y "%SRC%\timescaledb--*--*.sql" %PG_EXT% >nul 2>&1

echo [INFO] TimescaleDB files installed successfully!
echo [INFO] Now configure postgresql.conf to enable TimescaleDB.

pause