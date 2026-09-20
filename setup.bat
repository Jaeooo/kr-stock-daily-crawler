@echo off
cd /d "%~dp0"

if "%~1"=="_child" goto :body

call "%~f0" _child > "%~dp0setup_log.txt" 2>&1
type "%~dp0setup_log.txt"
echo.
echo (Full log saved to setup_log.txt)
pause
exit /b

:body
set PY_VER=3.12.4
set PYTHON_CMD=python

python --version 2>nul | findstr /B "Python 3" >nul
if %ERRORLEVEL% EQU 0 goto :python_found

echo Python not found. Downloading and installing it now (internet required, may take a few minutes)...
set PY_INSTALLER=%TEMP%\python-installer.exe
powershell -Command "Invoke-WebRequest -Uri https://www.python.org/ftp/python/%PY_VER%/python-%PY_VER%-amd64.exe -OutFile '%PY_INSTALLER%'"

if not exist "%PY_INSTALLER%" (
    echo Download failed. Check your internet connection, or install Python manually from https://www.python.org/downloads/
    exit /b 1
)

echo Installing Python...
"%PY_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_tcltk=1
del "%PY_INSTALLER%"

set PYTHON_CMD=%LocalAppData%\Programs\Python\Python312\python.exe
if not exist "%PYTHON_CMD%" (
    echo Python was installed but could not be found at the expected path. Close this window and run setup.bat again.
    exit /b 0
)
echo Python installed.

:python_found
"%PYTHON_CMD%" -m pip install -r src\requirements.txt
echo.
echo Setup complete. From now on, just double-click run_gui.bat to run the program.
