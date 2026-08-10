@echo off
title Fiverr SERP Analyzer - Setup
cd /d "%~dp0"

echo ============================================
echo   Fiverr SERP Analyzer - Environment Setup
echo ============================================
echo.
echo This script creates an ISOLATED Python environment
echo just for this project. No conflicts with anything else
echo on your computer.
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.9+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo [OK] Python found:
python --version
echo.

REM Create venv
set VENV_DIR=%~dp0.venv

if exist "%VENV_DIR%\Scripts\python.exe" (
    echo Virtual environment already exists at:
    echo   %VENV_DIR%
    echo.
    choice /C YN /M "Recreate it from scratch (Y/N)?"
    if errorlevel 2 goto :skip_venv
    echo Removing old environment...
    rmdir /s /q "%VENV_DIR%"
)

echo Creating virtual environment...
python -m venv "%VENV_DIR%"
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)
echo [OK] Virtual environment created.

:skip_venv

REM Activate and install deps
call "%VENV_DIR%\Scripts\activate.bat"
echo.
echo Upgrading pip...
python -m pip install --upgrade pip --quiet
echo.
echo Installing project dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   SETUP COMPLETE!
echo ============================================
echo.
echo Your isolated environment is ready at:
echo   %VENV_DIR%
echo.
echo To run the analyzer, double-click run.bat
echo Or run from command line:
echo   "%VENV_DIR%\Scripts\activate.bat"
echo   python main.py --keyword "web scraping"
echo.
pause
