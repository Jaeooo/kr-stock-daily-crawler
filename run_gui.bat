@echo off
cd /d "%~dp0"
if not exist "logs" mkdir "logs"
start "" pythonw src\gui.py > "%~dp0logs\gui_log.txt" 2>&1
