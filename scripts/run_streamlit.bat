@echo off
echo ============================================================
echo   Lancement Streamlit - SRM Souss-Massa
echo ============================================================

call venv\Scripts\activate.bat
streamlit run streamlit_app/app.py

pause
