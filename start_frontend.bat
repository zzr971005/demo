@echo off
chcp 936 >nul
title Frontend - Port 5173
cd /d "%~dp0\frontend"
npm run dev
