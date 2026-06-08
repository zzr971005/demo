@echo off
chcp 936 >nul
title Evolution Engine - Port 8001
cd /d "%~dp0\backend"
poetry run python -m quant_engine.ops.evolution_center
