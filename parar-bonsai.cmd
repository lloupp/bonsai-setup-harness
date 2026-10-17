@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0parar-bonsai.ps1"
if errorlevel 1 pause
