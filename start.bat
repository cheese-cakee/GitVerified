@echo off
echo.
echo ========================================
echo   GitVerified - Local AI Evaluation
echo   100%% Free, 100%% Private
echo ========================================
echo.

REM Check if Ollama is installed
where ollama >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] Ollama not found. Please install from https://ollama.ai
    echo.
    pause
    exit /b 1
)

echo [1/4] Starting Ollama...
start /min ollama serve

echo [2/4] Waiting for Ollama to start...
timeout /t 3 /nobreak >nul

echo [3/4] Checking for model...
ollama list | findstr "qwen2:1.5b" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo      Downloading qwen2:1.5b model (1GB)...
    ollama pull qwen2:1.5b
)

echo [4/4] Starting API Server...
echo.
echo ========================================
echo   Ready! Open http://localhost:3000
echo ========================================
echo.

python api_server.py