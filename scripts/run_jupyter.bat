@echo off
echo ============================================================
echo   Lancement Jupyter Lab - SRM Souss-Massa
echo ============================================================

call venv\Scripts\activate.bat
jupyter lab --notebook-dir=notebooks --port=8888

pause
