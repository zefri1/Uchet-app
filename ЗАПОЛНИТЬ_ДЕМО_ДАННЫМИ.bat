@echo off
setlocal
cd /d "%~dp0"
title Demo Data

if not exist ".venv\Scripts\python.exe" goto :not_installed

echo Loading demo data...
".venv\Scripts\python.exe" seed_demo.py
echo.
pause
exit /b 0

:not_installed
echo Application is not installed yet.
echo Run this file first:
echo УСТАНОВИТЬ_ПРИЛОЖЕНИЕ.bat
echo.
pause
exit /b 1
