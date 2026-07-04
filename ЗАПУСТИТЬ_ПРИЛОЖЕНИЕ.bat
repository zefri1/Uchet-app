@echo off
setlocal
cd /d "%~dp0"
title Real Estate App

if not exist ".venv\Scripts\python.exe" goto :not_installed

echo Starting application...
echo Control window and browser will open automatically.
".venv\Scripts\pythonw.exe" run.py
goto :end

:not_installed
echo Application is not installed yet.
echo Run this file first:
echo УСТАНОВИТЬ_ПРИЛОЖЕНИЕ.bat
echo.
pause

:end
exit /b 0
