@echo off
cd /d "%~dp0"
call venv\Scripts\activate
rem open the browser after a short delay so the server is ready first
start "" /b cmd /c "%SystemRoot%\System32\timeout.exe /t 4 /nobreak >nul & start "" http://localhost:8000"
python -m uvicorn backend.main:app --reload --reload-dir backend --port 8000
