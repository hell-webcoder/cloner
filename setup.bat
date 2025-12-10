@echo off
REM =============================================================================
REM Website Cloner Pro - One-Click Setup Script for Windows
REM =============================================================================
REM This script installs all requirements for Website Cloner Pro
REM 
REM Usage: Double-click setup.bat or run from Command Prompt
REM =============================================================================

echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║            WEBSITE CLONER PRO - SETUP SCRIPT                  ║
echo ║           One-Click Installation ^& Configuration              ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.

REM Check Python installation
echo [*] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Python is not installed or not in PATH
    echo     Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
)

python --version
echo [✓] Python found

REM Check pip
echo [*] Checking pip installation...
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] pip is not installed
    pause
    exit /b 1
)
echo [✓] pip found

REM Install Python dependencies
echo [*] Installing Python dependencies...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [X] Failed to install Python dependencies
    pause
    exit /b 1
)
echo [✓] Python dependencies installed

REM Install package
echo [*] Installing Website Cloner package...
pip install -e . --quiet
if %errorlevel% neq 0 (
    echo [X] Failed to install package
    pause
    exit /b 1
)
echo [✓] Website Cloner package installed

REM Install Playwright browser
echo [*] Installing Playwright Chromium browser...
playwright install chromium
if %errorlevel% neq 0 (
    echo [!] Warning: Failed to install Playwright browser
    echo     You may need to run: playwright install chromium
)
echo [✓] Playwright browser installed

echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║              INSTALLATION COMPLETED SUCCESSFULLY!             ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.
echo Usage:
echo.
echo   Command Line Interface:
echo     website-cloner --url https://example.com --output ./cloned
echo     website-cloner --url https://example.com --full-analysis
echo.
echo   Web User Interface:
echo     website-cloner-web
echo     Then open: http://localhost:5000
echo.
echo For more options, run: website-cloner --help
echo.
pause
