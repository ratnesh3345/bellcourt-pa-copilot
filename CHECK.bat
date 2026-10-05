@echo off
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY=py
echo Installing what is needed (only slow the first time)...
%PY% -m pip install --quiet -r requirements.txt
echo.
%PY% run_all_checks.py
echo.
pause
