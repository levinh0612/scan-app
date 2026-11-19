@echo off
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\scripts\stop.ps1" %*
if "%~1"=="" pause
