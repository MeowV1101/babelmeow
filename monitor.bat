@echo off
chcp 65001 > nul
title BabelMeow Translation Monitor
cd /d "%~dp0"
"C:\Users\lnwza\AppData\Local\Programs\Python\Python312\python.exe" scripts\monitor_progress.py
pause
