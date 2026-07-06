@echo off
echo ============================================================
echo   Lancement Streamlit - SRM Souss-Massa
echo ============================================================

call venv\Scripts\activate.bat

REM Definir PYTHONPATH pour que les imports fonctionnent
set PYTHONPATH=%CD%

streamlit run streamlit_app/app.py

pause