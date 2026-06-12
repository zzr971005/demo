@echo off
chcp 936 >nul
title Execution Gateway - Port 8002
cd /d "%~dp0\backend"
poetry run python -m quant_engine.runtime.execution_gateway
