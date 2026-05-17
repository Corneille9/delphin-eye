@echo off
setlocal

set VENV_DIR=.venv

if not exist "%~dp0%VENV_DIR%\Scripts\python.exe" (
    echo ==^> Installation non detectee, lancement de install.bat...
    call "%~dp0install.bat"
    if errorlevel 1 exit /b 1
)

"%~dp0%VENV_DIR%\Scripts\python.exe" "%~dp0src\main.py"

if errorlevel 1 (
    echo.
    echo L'application s'est arretee avec une erreur.
    pause
)
