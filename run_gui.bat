@echo off
cd /d "%~dp0"
start "" pythonw src\gui.py > "%~dp0gui_log.txt" 2>&1
