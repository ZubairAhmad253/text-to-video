@echo off
cd /d "%~dp0"

echo [1/4] Creating virtual environment...
if not exist venv python -m venv venv || goto :error
call venv\Scripts\activate

echo [2/4] Installing Python packages...
python -m pip install --upgrade pip
pip install -r requirements.txt || goto :error

echo [3/4] Downloading English voice (about 60 MB)...
set VOICE_URL=https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium
if not exist voices mkdir voices
if not exist voices\en_US-lessac-medium.onnx curl -L -o voices\en_US-lessac-medium.onnx %VOICE_URL%/en_US-lessac-medium.onnx || goto :error
if not exist voices\en_US-lessac-medium.onnx.json curl -L -o voices\en_US-lessac-medium.onnx.json %VOICE_URL%/en_US-lessac-medium.onnx.json || goto :error

echo [4/4] Story mode: downloading the story model with Ollama (about 2 GB)...
where ollama >nul 2>nul || winget install --id Ollama.Ollama -e --accept-source-agreements --accept-package-agreements
if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" ("%LOCALAPPDATA%\Programs\Ollama\ollama.exe" pull qwen2.5:3b) else (echo Ollama not found - story mode will be turned off.)

echo.
echo Setup complete. Double-click run.bat to start the website.
pause
exit /b 0

:error
echo.
echo Setup failed - see the message above.
pause
exit /b 1
