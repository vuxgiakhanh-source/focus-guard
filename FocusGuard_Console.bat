@echo off
:: FocusGuard PRO - Debug / Console Launcher
chcp 65001 >nul
title FocusGuard PRO (Console Mode)
cd /d "%~dp0"

set "PYTHON=%~dp0venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"

where %PYTHON% >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [!] Khong tim thay Python! Vui long cai dat Python 3.10 - 3.12 tu python.org
    pause
    exit /b 1
)

:: Preflight check dependencies
%PYTHON% -c "import cv2, mediapipe, ultralytics, pygame, torch" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [*] Dang kiem tra va tu dong cai dat thu vien can thiet...
    %PYTHON% -m pip install -r requirements.txt
)

echo [*] Dang khoi dong FocusGuard PRO...
"%PYTHON%" "%~dp0main.py"
pause
