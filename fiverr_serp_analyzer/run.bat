@echo off
title Fiverr SERP Analyzer
cd /d "%~dp0"

echo ============================================
echo   Fiverr SERP Analyzer
echo ============================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.9+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

set VENV_DIR=%~dp0.venv
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo Creating isolated Python environment...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
    echo.
)

call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)
echo [OK] Using isolated environment: %VENV_DIR%
echo.

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
    echo [OK] Dependencies installed.
)

echo.
echo ============================================
echo   Tier 2: Deep Gig Detail Scraping
echo ============================================
echo   Extracts full description, packages, FAQs
echo   seller bio, tags, reviews, portfolio data
echo.
echo   WARNING: Adds 4-5 minutes per keyword.
echo   Use only for deep competitive research.
echo ============================================
echo.
choice /C YN /M "Enable Tier 2 deep scraping?"
if errorlevel 2 goto skip_t2
if errorlevel 1 goto enable_t2

:enable_t2
echo [OK] Tier 2 ENABLED
set T2=--tier2
goto run

:skip_t2
echo [OK] Tier 2 DISABLED (fast mode)
set T2=
goto run

:run
echo.
echo ============================================
echo   Starting Fiverr SERP Analyzer...
echo ============================================
echo   Chrome will open in a visible window.
echo   Press Ctrl+C to stop and save progress.
echo ============================================
echo.

python main.py %* %T2%

echo.
echo ============================================
echo   Run complete.
echo ============================================
pause
