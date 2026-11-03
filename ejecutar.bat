@echo off
REM Instala dependencias (primera vez) y ejecuta Emily QA.
cd /d "%~dp0"
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
pip install -q -r requirements.txt
python -m emily_qa %*
pause
