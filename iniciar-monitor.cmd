@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0iniciar-monitor.ps1"
if errorlevel 1 pause
