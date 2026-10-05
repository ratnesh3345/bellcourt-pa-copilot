@echo off
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY=py
%PY% -m pip install --quiet -r requirements.txt
echo Starting PA Copilot in your browser... (close this window to stop it)
%PY% -m streamlit run app.py
pause
