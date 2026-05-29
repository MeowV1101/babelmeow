@echo off
REM Launch RSTGameTranslation as Administrator (it requires elevation for overlay/capture)
powershell -Command "Start-Process -FilePath 'D:\claude\Tools\RST\RSTGameTranslation\rst.exe' -WorkingDirectory 'D:\claude\Tools\RST\RSTGameTranslation' -Verb RunAs"
