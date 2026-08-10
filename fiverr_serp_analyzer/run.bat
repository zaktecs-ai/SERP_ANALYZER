@echo off
title Fiverr SERP Analyzer
cd /d "%~dp0"

echo ============================================
echo   Fiverr SERP Analyzer
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Install dependencies if needed
echo Checking dependencies...
python -c "import selenium, yaml, openpyxl" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies.
        pause
        exit /b 1
    )
)

echo.
echo Starting Fiverr SERP Analyzer...
echo The browser will open in a visible window.
echo You can press Ctrl+C at any time to stop and save progress.
echo.

REM Run the analyzer
python main.py %*

echo.
echo ============================================
echo   Run complete. Reports saved to this folder.
echo ============================================
pause