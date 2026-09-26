@echo off
setlocal
if exist "%~dp0Snap Extract.exe" (
    start "" "%~dp0Snap Extract.exe"
    exit /b
)
if exist "%~dp0dist\Snap Extract\Snap Extract.exe" (
    start "" "%~dp0dist\Snap Extract\Snap Extract.exe"
    exit /b
)
if exist "%~dp0.venv\Scripts\pythonw.exe" (
    start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0run_app.py"
    exit /b
)
where pyw.exe >nul 2>&1
if not errorlevel 1 (
    start "" pyw.exe -3 "%~dp0run_app.py"
    exit /b
)
where pythonw.exe >nul 2>&1
if not errorlevel 1 (
    start "" pythonw.exe "%~dp0run_app.py"
    exit /b
)
echo Snap Extract could not find its Windows executable or Python.
echo Extract the Windows ZIP and open Snap Extract.exe, or install Python 3.10+ with Tcl/Tk.
echo See README.md in this folder for setup instructions.
pause
exit /b 1
