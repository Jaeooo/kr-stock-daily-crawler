@echo off
cd /d "%~dp0"

if "%~1"=="_child" goto :body

call "%~f0" _child > "%~dp0update_log.txt" 2>&1
type "%~dp0update_log.txt"
echo.
pause
exit /b

:body
python src\update_cli.py
