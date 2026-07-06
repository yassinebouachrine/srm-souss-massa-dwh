@echo off
call venv\Scripts\activate.bat
set PYTHONPATH=%CD%
streamlit run streamlit_app/app.py
pause