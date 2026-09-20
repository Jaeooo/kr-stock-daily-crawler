@echo off
cd /d "%~dp0"
if not exist "logs" mkdir "logs"

call :main > "%~dp0logs\setup_log.txt" 2>&1
type "%~dp0logs\setup_log.txt"
echo.
echo (Full log saved to logs\setup_log.txt)
pause
exit /b

:main
python --version 2>nul | findstr /B "Python 3" >nul
if %ERRORLEVEL% EQU 0 goto :python_found

echo Python is not installed on this computer.
echo Opening the official Python download page in your browser.
echo.
echo IMPORTANT: On the install screen, check the box that says
echo "Add python.exe to PATH" before clicking Install.
echo.
echo After installing Python, close this window and run setup.bat again.
start https://www.python.org/downloads/
exit /b

:python_found
python -m pip install -r src\requirements.txt
echo.
echo Setup complete. From now on, just double-click run_gui.bat to run the program.
exit /b
