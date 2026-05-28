@echo off
chcp 65001 > nul
title BabelMeow Remote Control Setup
cd /d D:\claude\BabelMeow
cls
echo.
echo ============================================================
echo  STEP 1 of 2: Accept Workspace Trust (one-time setup)
echo ============================================================
echo.
echo Claude will open an interactive prompt.
echo When asked "Do you trust this workspace?" — answer YES (1)
echo Then type /quit and press Enter to exit Claude.
echo.
echo After Claude exits, this script will continue automatically.
echo.
pause
echo.
echo Starting Claude...
echo.
"C:\Users\lnwza\AppData\Roaming\Claude\claude-code\2.1.149\claude.exe"
echo.
echo ============================================================
echo  STEP 2 of 2: Start Remote Control Server
echo ============================================================
echo.
echo Press SPACEBAR in the terminal below to show QR code
echo Scan with Claude app on phone, or use the session URL
echo Keep this window OPEN to maintain the session
echo.
pause
echo.
"C:\Users\lnwza\AppData\Roaming\Claude\claude-code\2.1.149\claude.exe" remote-control --name "BabelMeow"
echo.
echo ============================================================
echo  Session ended
echo ============================================================
pause
