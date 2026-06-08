@echo off
title Start Frontend as Admin

:: Request administrator privileges
echo Requesting administrator privileges...
powershell -Command "Start-Process cmd -ArgumentList '/k cd /d \"d:\鏈熻揣鑷姩杩涘寲鍥犲瓙鎸栨帢绯荤粺\frontend\" && npm run dev' -Verb RunAs"
