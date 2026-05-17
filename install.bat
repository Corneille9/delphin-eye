@echo off
setlocal enabledelayedexpansion

set VENV_DIR=.venv

echo ==^> Verification de Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo Erreur : Python introuvable. Installez Python 3.10+ et relancez.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set PY_VERSION=%%i
echo     Python !PY_VERSION! detecte.

python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if errorlevel 1 (
    echo Erreur : Python 3.10 ou superieur requis ^(version actuelle : !PY_VERSION!^).
    pause
    exit /b 1
)

echo ==^> Creation du virtualenv dans %VENV_DIR%...
python -m venv "%~dp0%VENV_DIR%"

echo ==^> Installation des dependances...
"%~dp0%VENV_DIR%\Scripts\pip" install --upgrade pip
"%~dp0%VENV_DIR%\Scripts\pip" install -r "%~dp0requirements.txt"

echo.
echo Installation terminee.
echo.
echo Pour lancer l'application :
echo     run.bat
echo.
pause
