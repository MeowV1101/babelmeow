@echo off
chcp 65001 > nul
title BabelMeow Bridge (port 11435)
cd /d "%~dp0\.."
echo.
echo ============================================================
echo  BabelMeow Bridge — Thai translation server for RST
echo ============================================================
echo.
echo  Bridge listens on:  http://localhost:11435
echo  Point RSTGameTranslation Ollama URL here, model 'babelmeow-th'
echo.
echo  Keep this window open while playing.
echo ============================================================
echo.
"C:\Users\lnwza\AppData\Local\Programs\Python\Python312\python.exe" -m babelmeow.overlay_bridge.server
pause
