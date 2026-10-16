@echo off
echo ========================================================
echo   Launching Aatam: The Board Game Wiki on Steroids
echo ========================================================
echo.
cd /d "%~dp0"
python -m uvicorn backend.server:app --host 0.0.0.0 --port 8000
pause

