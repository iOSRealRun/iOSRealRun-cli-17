@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" -u main.py
echo.
echo Program exited.
pause
