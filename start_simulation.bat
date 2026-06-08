@echo off
chcp 936 >nul
title Simulation Engine - Port 8002
cd /d "%~dp0\backend"
poetry run python -m quant_engine.runtime.simulation_engine
