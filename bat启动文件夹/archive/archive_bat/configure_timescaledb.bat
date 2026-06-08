@echo off
echo [INFO] Configuring TimescaleDB for PostgreSQL 17...

set PG_CONF="C:\Program Files\PostgreSQL\17\data\postgresql.conf"
set PG_HBA="C:\Program Files\PostgreSQL\17\data\pg_hba.conf"

REM Add shared_preload_libraries to postgresql.conf
powershell -Command "(Get-Content '%PG_CONF%') -replace '#shared_preload_libraries = .*', 'shared_preload_libraries = ''timescaledb''' | Set-Content '%PG_CONF%' -Encoding ASCII"

REM Change local auth to trust for postgres user (easier setup)
powershell -Command "(Get-Content '%PG_HBA%') -replace 'local\s+all\s+all\s+scram-sha-256', 'local   all             all                                     trust' | Set-Content '%PG_HBA%' -Encoding ASCII"
powershell -Command "(Get-Content '%PG_HBA%') -replace 'host\s+all\s+all\s+127.0.0.1/32\s+scram-sha-256', 'host    all             all             127.0.0.1/32            trust' | Set-Content '%PG_HBA%' -Encoding ASCII"

echo [INFO] Configuration updated!

REM Restart PostgreSQL
echo [INFO] Restarting PostgreSQL service...
net stop postgresql-x64-17
net start postgresql-x64-17

echo [SUCCESS] PostgreSQL restarted with TimescaleDB enabled!
pause