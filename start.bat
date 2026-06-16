@echo off
echo ============================================
echo   Local Translation Service - Startup
echo ============================================
echo.

cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo Virtual environment not found. Creating one...
    python -m venv venv
    if errorlevel 1 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo Virtual environment created.
    echo.
    echo Installing dependencies...
    call venv\Scripts\pip install -r requirements.txt
    if errorlevel 1 (
        echo Failed to install dependencies.
        pause
        exit /b 1
    )
    echo Dependencies installed.
    echo.
)

echo Starting translation service on port %PORT% (default: 8330)...
echo.
call venv\Scripts\python app.py

pause
