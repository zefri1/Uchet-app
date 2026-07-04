@echo off
setlocal
cd /d "%~dp0"
title Real Estate App Setup

echo ==========================================
echo            APP INSTALLATION
echo ==========================================
echo Please wait. Do not close this window.
echo.

call :create_venv
if errorlevel 1 goto :python_not_found

echo [2/4] Upgrading pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :install_failed

echo.
echo [3/4] Installing required packages...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :install_failed

echo.
echo [4/4] Checking application...
".venv\Scripts\python.exe" -c "from app.main import app; print(app.title)"
if errorlevel 1 goto :install_failed

echo.
echo ==========================================
echo Installation completed successfully.
echo.
echo Next time use:
echo ЗАПУСТИТЬ_ПРИЛОЖЕНИЕ.bat
echo ==========================================
echo.
pause
exit /b 0

:create_venv
echo [1/4] Checking Python and virtual environment...
if exist ".venv\Scripts\python.exe" (
    echo Virtual environment already exists.
    exit /b 0
)

where py >nul 2>nul
if not errorlevel 1 (
    echo Creating virtual environment with py -3 ...
    py -3 -m venv .venv
    exit /b %errorlevel%
)

where python >nul 2>nul
if not errorlevel 1 (
    echo Creating virtual environment with python ...
    python -m venv .venv
    exit /b %errorlevel%
)

exit /b 1

:python_not_found
echo.
echo ERROR: Python 3 was not found on this computer.
echo.
echo Please do this:
echo 1. Install Python 3 from https://www.python.org/downloads/
echo 2. Enable the option "Add Python to PATH"
echo 3. Run this file again
echo.
pause
exit /b 1

:install_failed
echo.
echo ERROR: Installation failed.
echo Please read the messages above and try again.
echo.
pause
exit /b 1
