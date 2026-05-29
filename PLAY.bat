@echo off
chcp 65001 > nul
title BabelMeow - Play Mode
echo ============================================================
echo  BabelMeow - Starting everything for a play session
echo ============================================================
echo.

set OLLAMA=C:\Users\lnwza\AppData\Local\Programs\Ollama\ollama.exe
set PY=C:\Users\lnwza\AppData\Local\Programs\Python\Python312\python.exe

echo [1/3] Stopping old instances...
taskkill /F /IM ollama.exe >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":11434 .*LISTENING"') do taskkill /F /PID %%a >nul 2>&1
timeout /t 3 /nobreak >nul

echo [2/3] Starting Ollama (GPU/Vulkan) on port 11435...
set OLLAMA_VULKAN=1
set OLLAMA_NUM_PARALLEL=2
set OLLAMA_KEEP_ALIVE=30m
set OLLAMA_HOST=127.0.0.1:11435
start "" /B "%OLLAMA%" serve
timeout /t 6 /nobreak >nul
REM warm-load the 4B translate model so the first in-game miss isn't slow
curl -s http://127.0.0.1:11435/api/generate -d "{\"model\":\"scb10x/typhoon-translate1.5-4b\",\"prompt\":\"hi\",\"stream\":false,\"options\":{\"num_predict\":3,\"num_ctx\":2048}}" >nul 2>&1

echo [3/3] Starting BabelMeow Bridge on port 11434 (live fallback ON)...
cd /d "%~dp0"
set BABELMEOW_LIVE=1
set BABELMEOW_PORT=11434
set BABELMEOW_REAL_OLLAMA=http://127.0.0.1:11435
start "BabelMeow Bridge" "%PY%" -m babelmeow.overlay_bridge.server

echo.
echo ============================================================
echo  READY. Now:
echo   1. Open Diablo IV (Borderless Windowed)
echo   2. Open RST as admin (start_rst_admin.bat)
echo      - Translation: Ollama, URL http://127.0.0.1:11434, model babelmeow-th
echo   3. Alt+Q select area, Alt+F overlay, Alt+G translate
echo.
echo  Keep this window open. Close it to stop everything.
echo ============================================================
echo.
echo  Bridge stats: http://localhost:11434/stats
echo.
pause
