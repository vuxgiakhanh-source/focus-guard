@echo off
:: FocusGuard PRO - Dọn dẹp & Khởi động lại phiên làm việc
title FocusGuard PRO (Restart & Clean)
cd /d "%~dp0"
echo [*] Dang don dep tien trinh cu va khoi dong lai FocusGuard PRO...
set "PYTHONW=%~dp0venv\Scripts\pythonw.exe"
if not exist "%PYTHONW%" set "PYTHONW=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
if not exist "%PYTHONW%" set "PYTHONW=pythonw"
start "" "%PYTHONW%" "%~dp0main.py" --restart
