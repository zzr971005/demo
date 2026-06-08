@echo off
setlocal

title Evolution Mode Comparison Test

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"
set "BACKEND_PATH=%PROJECT_ROOT%\backend"

cls
echo.
echo ========================================
echo  Evolution Mode Comparison Test
echo ========================================
echo.
echo This mode runs comparison tests between:
echo - Single-symbol evolution
echo - Joint evolution (multi-symbol)
echo - Hybrid evolution (universal + specific)
echo.

REM Check Python environment
for /f "delims=" %%i in ('cd /d "%BACKEND_PATH%" ^&^& poetry env info --path 2^>nul') do set "VENV_PATH=%%i"
if not defined VENV_PATH (
    echo [ERROR] Poetry virtual environment not found
    pause
    exit /b 1
)
set "PYTHON=%VENV_PATH%\Scripts\python.exe"
echo [OK] Python environment ready

REM Check if backend is running
curl -s http://localhost:8000/health >nul 2>&1
if errorlevel 1 (
    echo [INFO] Backend is not running. Please start backend first.
    echo [INFO] Run: start-backend-only.bat
    pause
    exit /b 1
)
echo [OK] Backend is running

REM Run comparison test
echo.
echo [INFO] Starting evolution mode comparison test...
echo.

cd /d "%BACKEND_PATH%"
"%PYTHON%" -c "
import requests
import json

# Test single-symbol evolution
print('Testing single-symbol evolution...')
response = requests.post('http://localhost:8000/api/evolution/start', json={
    'symbol': 'RB',
    'population_size': 50,
    'max_generations': 10
})
print(f'Single-symbol: {response.status_code}')

# Test joint evolution
print('Testing joint evolution...')
response = requests.post('http://localhost:8000/api/evolution/joint-start', json={
    'symbols': ['RB', 'MA', 'CU'],
    'population_size': 50,
    'max_generations': 10
})
print(f'Joint: {response.status_code}')

# Test hybrid evolution
print('Testing hybrid evolution...')
response = requests.post('http://localhost:8000/api/evolution/hybrid-start', json={
    'symbols': ['RB', 'MA', 'CU'],
    'population_size': 50,
    'max_generations': 10
})
print(f'Hybrid: {response.status_code}')

print('Comparison test completed.')
"

pause
