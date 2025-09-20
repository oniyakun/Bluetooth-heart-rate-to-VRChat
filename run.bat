@echo off
chcp 65001 >nul
title Bluetooth Heart Rate to VRChat OSC

echo ========================================
echo Bluetooth Heart Rate to VRChat OSC
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found, please install Python 3.7+
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check if in correct directory
if not exist "main.py" (
    echo Error: main.py not found
    echo Please run this script in bluetooth-heartrate folder
    pause
    exit /b 1
)

REM Check dependencies
echo Checking Python dependencies...
python -c "import bleak, pythonosc" >nul 2>&1
if errorlevel 1 (
    echo Installing Python dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo Error: Failed to install dependencies
        pause
        exit /b 1
    )
)

echo Dependencies check completed
echo.

REM Run main program
echo Starting Bluetooth Heart Rate forwarder...
echo Press Ctrl+C to exit
echo.
python main.py

echo.
echo Program exited
pause