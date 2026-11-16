@echo off
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -u main.py
) else (
    where py >nul 2>nul
    if errorlevel 1 (
        python -u main.py
    ) else (
        py -3 -u main.py
    )
)

set "exit_code=%ERRORLEVEL%"
echo.
echo Program exited.
pause
exit /b %exit_code%
