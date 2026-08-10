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
    echo Please install Python 3.9+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

REM ============================================================
REM Virtual Environment (Isolated - no conflicts with other projects)
REM ============================================================
set VENV_DIR=%~dp0.venv

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo Creating isolated Python environment (venv)...
    echo This keeps all libraries separate from your system Python.
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        echo Make sure Python 3.9+ is installed correctly.
        pause
        exit /b 1
    )
    echo.
    echo [OK] Virtual environment created: %VENV_DIR%
    echo.
)

REM Activate the virtual environment
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)
echo [OK] Using isolated environment: %VENV_DIR%
echo.

REM Install dependencies inside venv if needed
echo Checking dependencies...
python -c "import selenium, yaml, openpyxl" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies inside virtual environment...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies.
        echo Try: "%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed.
)

echo.
echo ============================================
echo   Starting Fiverr SERP Analyzer...
echo ============================================
echo   - Chrome browser will open in a visible window
echo   - Press Ctrl+C at any time to stop and save progress
echo   - All reports saved to this folder
echo ============================================
echo.

REM Ask user about Tier 2 deep scraping
echo.
echo ============================================
echo   Tier 2: Deep Gig Detail Scraping
echo ============================================
echo   Tier 2 visits each gig's detail page to extract:
echo     - Full description, pricing packages, FAQs
echo     - Seller bio, tags, reviews, portfolio data
echo.
echo   WARNING: Tier 2 adds 4-5 minutes per keyword.
echo   Use only when you need deep competitive research.
echo ============================================
echo.
choice /C YN /M "Enable Tier 2 deep gig detail scraping (Y/N)?"
if errorlevel 2 goto :skip_tier2
if errorlevel 1 goto :enable_tier2

:enable_tier2
echo [OK] Tier 2 ENABLED - Deep competitive intelligence
set TIER2_FLAG=--tier2
goto :run

:skip_tier2
echo [OK] Tier 2 DISABLED - SERP data only (fast mode)
set TIER2_FLAG=
goto :run

:run
REM Run the analyzer (inside venv)
python main.py %* %TIER2_FLAG%

echo.
echo ============================================
echo   Run complete! Reports saved to this folder.
echo ============================================
echo.
echo To run again, just double-click run.bat.
echo The virtual environment is already set up.
pause
