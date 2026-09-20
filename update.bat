@echo off
cd /d "%~dp0"
if not exist "logs" mkdir "logs"

call :main > "%~dp0logs\update_log.txt" 2>&1
type "%~dp0logs\update_log.txt"
echo.
pause
exit /b

:main
python src\update_cli.py
exit /b
