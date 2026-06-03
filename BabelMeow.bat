@echo off
REM BabelMeow control panel (GUI). Uses pythonw so there's no console window.
cd /d "%~dp0"
set PYW=C:\Users\lnwza\AppData\Local\Programs\Python\Python312\pythonw.exe
if not exist "%PYW%" set PYW=pythonw
start "" "%PYW%" -m babelmeow.gui
