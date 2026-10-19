@echo off
:: FocusGuard PRO - 1-Click App Launcher
chcp 65001 >nul
title FocusGuard PRO Launcher
cd /d "%~dp0"

set "PYTHON=%~dp0venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"

:: Check Python installation
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
    if %ERRORLEVEL% neq 0 (
        echo [!] Co loi khi cai dat thu vien. Vui long kiem tra ket noi mang.
        pause
        exit /b 1
    )
)

:: Run FocusGuard in background mode
set "PYTHONW=%~dp0venv\Scripts\pythonw.exe"
if not exist "%PYTHONW%" (
    set "PYTHONW=pythonw"
    where pythonw >nul 2>&1 || set "PYTHONW=%PYTHON%"
)

start "" "%PYTHONW%" "%~dp0main.py"
exit
