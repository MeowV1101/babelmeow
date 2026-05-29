@echo off
chcp 65001 > nul
title Ollama GPU (Vulkan) Server
echo.
echo ============================================================
echo  Starting Ollama with Vulkan GPU (AMD RX 9070 XT / RDNA4)
echo ============================================================
echo.
echo Without OLLAMA_VULKAN=1, Ollama 0.24 falls back to CPU on
echo RDNA4 cards (gfx1201) - 5x slower. This script forces GPU.
echo.

REM Kill any existing ollama to free the port
taskkill /F /IM ollama.exe >nul 2>&1
timeout /t 3 /nobreak >nul

REM GPU + parallelism settings
set OLLAMA_VULKAN=1
set OLLAMA_NUM_PARALLEL=4
set OLLAMA_KEEP_ALIVE=30m
set OLLAMA_MAX_LOADED_MODELS=1

echo Settings: VULKAN=1  NUM_PARALLEL=4  KEEP_ALIVE=30m
echo.
echo Starting server... (keep this window open)
echo Verify with: ollama ps  (PROCESSOR should say "100%% GPU")
echo.
"C:\Users\lnwza\AppData\Local\Programs\Ollama\ollama.exe" serve
pause
