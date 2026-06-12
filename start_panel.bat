@echo off
chcp 936 >nul
title Panel HTTP Service - Port 8000
cd /d "%~dp0\backend"
poetry run python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
