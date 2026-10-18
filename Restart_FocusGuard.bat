@echo off
:: FocusGuard PRO - Dọn dẹp & Khởi động lại phiên làm việc
title FocusGuard PRO (Restart & Clean)
cd /d "%~dp0"
echo [*] Dang don dep tien trinh cu va khoi dong lai FocusGuard PRO...
start "" "C:\Users\LOQ\AppData\Local\Programs\Python\Python312\pythonw.exe" "%~dp0main.py" --restart
