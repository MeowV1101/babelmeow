@echo off
title BabelMeow - Claude Code Remote Control
cd /d "%~dp0"
echo.
echo ====================================================
echo  Starting Claude Code Remote Control for BabelMeow
echo ====================================================
echo.
echo Once running:
echo   1. Press SPACEBAR to show QR code
echo   2. Scan with Claude app on phone (iOS/Android)
echo      Or open the session URL in any browser
echo   3. Keep this window OPEN to maintain the session
echo.
echo ====================================================
echo.
"C:\Users\lnwza\AppData\Roaming\Claude\claude-code\2.1.149\claude.exe" remote-control --name "BabelMeow"
pause
