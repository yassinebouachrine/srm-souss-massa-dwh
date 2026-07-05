@echo off
echo ============================================================
echo   SRM Souss-Massa - Installation des dependances
echo ============================================================
echo.

call venv\Scripts\activate.bat

echo [1/7] Nettoyage du cache pip...
pip cache purge

echo.
echo [2/7] Installation Airflow avec contraintes...
pip install "apache-airflow==2.8.1" --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.8.1/constraints-3.10.txt"

echo.
echo [3/7] Installation packages Data...
pip install pandas==2.1.4 numpy==1.26.3 openpyxl==3.1.2 xlrd==2.0.1 python-dateutil==2.8.2

echo.
echo [4/7] Installation PostgreSQL driver...
pip install psycopg2-binary==2.9.9

echo.
echo [5/7] Installation Jupyter...
pip install jupyter==1.0.0 jupyterlab==4.0.10 notebook==7.0.6 ipykernel==6.29.0 nbconvert==7.14.1

echo.
echo [6/7] Installation Streamlit...
pip install streamlit==1.30.0 streamlit-option-menu==0.3.6 plotly==5.18.0 altair==5.2.0

echo.
echo [7/7] Installation Utilities et Tests...
pip install python-dotenv==1.0.0 pydantic==2.5.3 pydantic-settings==2.1.0 click==8.1.7 tqdm==4.66.1 requests==2.31.0
pip install pytest==7.4.4 pytest-cov==4.1.0 pytest-mock==3.12.0
pip install black==23.12.1 isort==5.13.2 flake8==7.0.0

echo.
echo ============================================================
echo   INSTALLATION TERMINEE !
echo ============================================================

pause
