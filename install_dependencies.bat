@echo off
setlocal EnableDelayedExpansion

echo ============================================================
echo   SRM Souss-Massa - Installation des dependances
echo   Airflow 2.8.1 + Jupyter + Streamlit + Auth
echo ============================================================
echo.

:: ══════════════════════════════════════════════════════════════
:: Verification de l'environnement virtuel
:: ══════════════════════════════════════════════════════════════
if not exist "venv\Scripts\activate.bat" (
    echo [ERREUR] Environnement virtuel introuvable : venv\
    echo.
    echo Creez-le avec : python -m venv venv
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

:: ══════════════════════════════════════════════════════════════
:: Verification de Python
:: ══════════════════════════════════════════════════════════════
python --version
if errorlevel 1 (
    echo [ERREUR] Python n'est pas accessible
    pause
    exit /b 1
)

echo.
echo ============================================================
echo.

:: ══════════════════════════════════════════════════════════════
:: ETAPE 1 - Nettoyage du cache pip
:: ══════════════════════════════════════════════════════════════
echo [1/8] Nettoyage du cache pip et mise a jour...
pip cache purge
python -m pip install --upgrade pip setuptools wheel
echo.

:: ══════════════════════════════════════════════════════════════
:: ETAPE 2 - Airflow avec contraintes officielles
:: ══════════════════════════════════════════════════════════════
echo [2/8] Installation Airflow avec contraintes officielles...
pip install "apache-airflow==2.8.1" ^
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.8.1/constraints-3.10.txt"

if errorlevel 1 (
    echo [ERREUR] Echec installation Airflow
    pause
    exit /b 1
)

echo.
echo Installation du provider PostgreSQL pour Airflow...
pip install "apache-airflow-providers-postgres==5.10.0" ^
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.8.1/constraints-3.10.txt"
echo.

:: ══════════════════════════════════════════════════════════════
:: ETAPE 3 - Data Processing
:: ══════════════════════════════════════════════════════════════
echo [3/8] Installation packages Data Processing...
pip install ^
    pandas==2.1.4 ^
    numpy==1.26.3 ^
    openpyxl==3.1.2 ^
    xlrd==2.0.1 ^
    python-dateutil==2.8.2 ^
    pytz==2023.3.post1

if errorlevel 1 (
    echo [AVERTISSEMENT] Certains packages Data ont echoue
)
echo.

:: ══════════════════════════════════════════════════════════════
:: ETAPE 4 - Database
:: ══════════════════════════════════════════════════════════════
echo [4/8] Installation Database (PostgreSQL + SQLAlchemy)...
pip install ^
    psycopg2-binary==2.9.9 ^
    sqlalchemy==1.4.51 ^
    alembic==1.13.1

if errorlevel 1 (
    echo [AVERTISSEMENT] Certains packages Database ont echoue
)
echo.

:: ══════════════════════════════════════════════════════════════
:: ETAPE 5 - Jupyter
:: ══════════════════════════════════════════════════════════════
echo [5/8] Installation Jupyter (Lab + Notebook)...
pip install ^
    jupyter==1.0.0 ^
    jupyterlab==4.0.10 ^
    notebook==7.0.6 ^
    ipykernel==6.29.0 ^
    nbconvert==7.14.1

if errorlevel 1 (
    echo [AVERTISSEMENT] Certains packages Jupyter ont echoue
)
echo.

:: ══════════════════════════════════════════════════════════════
:: ETAPE 6 - Streamlit + Visualisation
:: ══════════════════════════════════════════════════════════════
echo [6/8] Installation Streamlit et Visualisation...
pip install ^
    streamlit==1.30.0 ^
    streamlit-option-menu==0.3.6 ^
    plotly==5.18.0 ^
    altair==5.2.0

echo.
echo Installation streamlit-aggrid (tableaux avances)...
pip install streamlit-aggrid==0.3.4.post3
if errorlevel 1 (
    echo [INFO] streamlit-aggrid non installe (optionnel)
)
echo.

:: ══════════════════════════════════════════════════════════════
:: ETAPE 7 - Authentification et Securite (NOUVEAU)
:: ══════════════════════════════════════════════════════════════
echo [7/8] Installation Authentification et Securite...
pip install ^
    bcrypt==4.1.2 ^
    PyJWT==2.8.0 ^
    cryptography==41.0.7 ^
    email-validator==2.1.0

if errorlevel 1 (
    echo [ERREUR] Echec installation Auth - critique pour le login
    pause
    exit /b 1
)
echo.

:: ══════════════════════════════════════════════════════════════
:: ETAPE 8 - Utilities + Testing + Code Quality
:: ══════════════════════════════════════════════════════════════
echo [8/8] Installation Utilities, Testing et Code Quality...

echo   - Utilities...
pip install ^
    python-dotenv==1.0.0 ^
    pydantic==2.5.3 ^
    pydantic-settings==2.1.0 ^
    click==8.1.7 ^
    tqdm==4.66.1 ^
    requests==2.31.0

echo   - Testing...
pip install ^
    pytest==7.4.4 ^
    pytest-cov==4.1.0 ^
    pytest-mock==3.12.0

echo   - Code Quality...
pip install ^
    black==23.12.1 ^
    isort==5.13.2 ^
    flake8==7.0.0

echo.

:: ══════════════════════════════════════════════════════════════
:: Verification finale
:: ══════════════════════════════════════════════════════════════
echo ============================================================
echo   VERIFICATION DES PACKAGES CRITIQUES
echo ============================================================
echo.

set "PACKAGES_OK=0"
set "PACKAGES_KO=0"

call :check_package streamlit
call :check_package pandas
call :check_package numpy
call :check_package psycopg2
call :check_package bcrypt
call :check_package cryptography
call :check_package jwt
call :check_package dotenv
call :check_package airflow

echo.
echo ============================================================
echo   RESULTAT : !PACKAGES_OK! OK / !PACKAGES_KO! KO
echo ============================================================
echo.

if !PACKAGES_KO! GTR 0 (
    echo [ATTENTION] Certains packages n'ont pas ete installes correctement
    echo Relancez le script ou installez-les manuellement
) else (
    echo [SUCCES] Tous les packages critiques sont installes !
    echo.
    echo Prochaines etapes :
    echo   1. Ajouter PostgreSQL au PATH ^(si pas deja fait^)
    echo      C:\Program Files\PostgreSQL\17\bin
    echo.
    echo   2. Creer les tables auth + staging :
    echo      cd streamlit_app
    echo      python scripts\run_sql_file.py ..\database\ddl\09_auth_validation_tables.sql
    echo.
    echo   3. Initialiser les utilisateurs :
    echo      python scripts\init_passwords.py
    echo.
    echo   4. Lancer Streamlit :
    echo      streamlit run app.py
)

echo.
echo ============================================================
pause
exit /b 0


:: ══════════════════════════════════════════════════════════════
:: FONCTION : check_package
:: Verifie si un package Python est installe
:: ══════════════════════════════════════════════════════════════
:check_package
python -c "import %~1" >nul 2>&1
if errorlevel 1 (
    echo   [KO]  %~1
    set /a PACKAGES_KO+=1
) else (
    echo   [OK]  %~1
    set /a PACKAGES_OK+=1
)
exit /b 0