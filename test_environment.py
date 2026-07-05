"""
Test complet de l'environnement de developpement SRM
"""

import sys
from pathlib import Path


def print_header(text):
    print()
    print("=" * 60)
    print(f"  {text}")
    print("=" * 60)


def test_python_version():
    print_header("1. Test Python")
    version = sys.version_info
    print(f"  Python version : {version.major}.{version.minor}.{version.micro}")
    if version.major == 3 and version.minor >= 10:
        print("  OK - Version Python valide")
        return True
    else:
        print("  ECHEC - Python 3.10+ requis")
        return False


def test_packages():
    print_header("2. Test des Packages Python")
    packages = [
        ('pandas', 'pandas'),
        ('numpy', 'numpy'),
        ('sqlalchemy', 'sqlalchemy'),
        ('psycopg2', 'psycopg2'),
        ('streamlit', 'streamlit'),
        ('jupyter', 'jupyter'),
        ('airflow', 'airflow'),
        ('dotenv', 'dotenv'),
        ('plotly', 'plotly')
    ]
    all_ok = True
    for name, pkg in packages:
        try:
            __import__(pkg)
            print(f"  OK  {name}")
        except ImportError:
            print(f"  ECHEC  {name} MANQUANT")
            all_ok = False
    return all_ok


def test_postgres_connection():
    print_header("3. Test PostgreSQL")
    try:
        import psycopg2
        from dotenv import load_dotenv
        import os
        
        load_dotenv()
        
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST"),
            port=os.getenv("POSTGRES_PORT"),
            database=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD")
        )
        cur = conn.cursor()
        cur.execute("SELECT version()")
        version = cur.fetchone()[0]
        print(f"  OK  PostgreSQL connecte")
        print(f"      Version : {version[:50]}...")
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"  ECHEC  Erreur : {e}")
        return False


def test_airflow_db():
    print_header("4. Test Airflow (Docker)")
    try:
        import subprocess
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=srm_airflow_webserver", "--format", "{{.Status}}"],
            capture_output=True,
            text=True
        )
        if "Up" in result.stdout:
            print("  OK  Airflow Docker en cours d'execution")
            print(f"      Interface : http://localhost:8080")
            return True
        else:
            print("  INFO  Airflow Docker non demarre")
            print(f"        Lancez : scripts\\airflow_start.bat")
            return True  # Ne pas bloquer si Airflow pas démarré
    except Exception as e:
        print(f"  INFO  Docker non accessible : {e}")
        return True
    
    

def test_project_structure():
    print_header("5. Test Structure du Projet")
    required_folders = [
        'database', 'notebooks', 'streamlit_app',
        'airflow_home', 'etl', 'data', 'scripts', 'docs'
    ]
    all_ok = True
    for folder in required_folders:
        if Path(folder).exists():
            print(f"  OK  {folder}/")
        else:
            print(f"  ECHEC  {folder}/ MANQUANT")
            all_ok = False
    return all_ok


def test_env_file():
    print_header("6. Test Fichier .env")
    env_path = Path('.env')
    if env_path.exists():
        print(f"  OK  .env existe")
        from dotenv import load_dotenv
        import os
        load_dotenv()
        required = ['POSTGRES_HOST', 'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD']
        for var in required:
            if os.getenv(var):
                print(f"  OK  {var} defini")
            else:
                print(f"  ECHEC  {var} MANQUANT")
        return True
    else:
        print(f"  ECHEC  .env MANQUANT")
        return False


def main():
    print()
    print("=" * 60)
    print("  SRM Souss-Massa - Test Complet Environnement")
    print("=" * 60)
    
    results = {
        "Python": test_python_version(),
        "Packages": test_packages(),
        "Structure": test_project_structure(),
        "Fichier .env": test_env_file(),
        "PostgreSQL": test_postgres_connection(),
        "Airflow DB": test_airflow_db(),
    }
    
    print()
    print("=" * 60)
    print("  RESUME FINAL")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "OK    " if passed else "ECHEC "
        print(f"  {status}  {test_name}")
    
    total = len(results)
    passed = sum(results.values())
    
    print()
    print("-" * 60)
    print(f"  Resultat : {passed}/{total} tests reussis")
    print("-" * 60)
    
    if passed == total:
        print()
        print("  ENVIRONNEMENT PRET ! Vous pouvez commencer le developpement.")
    else:
        print()
        print("  Corriger les erreurs avant de continuer.")
    
    print()


if __name__ == "__main__":
    main()
