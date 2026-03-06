@echo off
setlocal enabledelayedexpansion

echo =======================================
echo PrismDB Studio - Windows Startup Script
echo =======================================

:: Check OS
if not "%OS%"=="Windows_NT" (
    echo [ERROR] This script is designed for Windows. For Linux/Mac, please use run_app.sh instead.
    pause
    exit /b 1
)
echo [INFO] Operating System: %OS%

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] Python is not installed or not in PATH.
    echo [INFO] Attempting to install Python via winget...
    winget install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements
    
    :: Re-check Python after install
    python --version >nul 2>&1
    if !errorlevel! neq 0 (
        echo [ERROR] Python installation failed or requires a terminal restart to apply PATH changes. 
        echo Please close this window, or install Python manually from https://www.python.org/downloads/
        pause
        exit /b 1
    )
) else (
    echo [INFO] Python is already installed.
)

:: Check if venv exists
IF NOT EXIST "venv\Scripts\activate.bat" (
    echo [INFO] Virtual environment not found. Creating one...
    python -m venv venv
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to create virtual environment. Please check your Python installation.
        pause
        exit /b 1
    )
    echo [INFO] Virtual environment created successfully.
)

:: Activate the virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

:: Install/Upgrade dependencies
echo [INFO] Ensuring pip is up to date...
python -m pip install pip >nul 2>&1
echo [INFO] Installing/Verifying dependencies from requirements.txt...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo =======================================
echo Starting PrismDB Studio...
echo =======================================
python main.py

pause
