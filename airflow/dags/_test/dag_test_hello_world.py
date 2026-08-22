"""
DAG de test : Validation de l'environnement Airflow.
Vérifie que tout est bien configuré avant de créer les vrais DAGs.
"""
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
import sys

# Import des constantes communes
sys.path.insert(0, "/opt/airflow/dags")
from common.constants import DEFAULT_ARGS, START_DATE, TAG_TEST


# ═══════════════════════════════════════════════════════════════
# FONCTIONS DE TEST
# ═══════════════════════════════════════════════════════════════

def hello_world():
    """Test 1 : Python fonctionne."""
    print("🎉 Hello World from Airflow!")
    print(f"⏰ Executed at: {datetime.now()}")
    return "Python OK"


def test_environnement():
    """Test 2 : Vérifier les variables d'environnement."""
    import os
    
    print("═══ Variables d'environnement ═══")
    variables = [
        "POSTGRES_HOST",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "ETL_LOG_LEVEL",
        "TIMEZONE",
    ]
    
    for var in variables:
        value = os.getenv(var, "❌ NON DÉFINIE")
        # Masquer les mots de passe
        if "PASSWORD" in var and value != "❌ NON DÉFINIE":
            value = "***" + value[-3:]
        print(f"   {var} : {value}")
    
    return "Environment OK"


def test_import_etl():
    """Test 3 : Vérifier que les modules ETL sont importables."""
    try:
        from etl.common.config import CONFIG
        from etl.common.logger import get_logger
        from etl.common.db import get_engine
        
        print("✅ Import etl.common.config OK")
        print("✅ Import etl.common.logger OK")
        print("✅ Import etl.common.db OK")
        print(f"📋 Config chargée : {list(CONFIG.keys())}")
        
        return "ETL modules OK"
    except Exception as e:
        print(f"❌ Erreur import : {e}")
        raise


def test_connexion_dwh():
    """Test 4 : Vérifier la connexion au DWH PostgreSQL."""
    try:
        from etl.common.db import get_engine
        from sqlalchemy import text
        
        engine = get_engine()
        with engine.connect() as conn:
            # Test 1 : Version PostgreSQL
            result = conn.execute(text("SELECT version()")).fetchone()
            print(f"✅ Connecté à PostgreSQL")
            print(f"   Version : {result[0][:80]}...")
            
            # Test 2 : Compter les tables du DWH
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'dwh'
            """)).fetchone()
            print(f"✅ Nombre de tables dans schéma 'dwh' : {result[0]}")
            
            # Test 3 : Compter les vues Power BI
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.views 
                WHERE table_schema = 'dwh' 
                AND table_name LIKE 'vw_pbi_%'
            """)).fetchone()
            print(f"✅ Nombre de vues PBI : {result[0]}")
        
        return "Connexion DWH OK"
    except Exception as e:
        print(f"❌ Erreur connexion DWH : {e}")
        raise


def test_lecture_dim_temps():
    """Test 5 : Lire quelques données depuis DIM_TEMPS."""
    try:
        from etl.common.db import read_sql
        
        df = read_sql("SELECT * FROM dwh.dim_temps ORDER BY date_complete DESC LIMIT 5")
        print(f"✅ Lecture DIM_TEMPS : {len(df)} lignes")
        print(df.to_string(index=False))
        
        return "Read DWH OK"
    except Exception as e:
        print(f"❌ Erreur lecture : {e}")
        raise


# ═══════════════════════════════════════════════════════════════
# DÉFINITION DU DAG
# ═══════════════════════════════════════════════════════════════

with DAG(
    dag_id="test_hello_world",
    description="DAG de validation de l'environnement Airflow + DWH",
    default_args=DEFAULT_ARGS,
    start_date=START_DATE,
    schedule=None,   # Manuel uniquement
    catchup=False,
    tags=[TAG_TEST, "validation"],
) as dag:
    
    # Test 1 : Python
    task_hello = PythonOperator(
        task_id="1_hello_world",
        python_callable=hello_world,
    )
    
    # Test 2 : Variables d'env
    task_env = PythonOperator(
        task_id="2_test_environnement",
        python_callable=test_environnement,
    )
    
    # Test 3 : Imports ETL
    task_imports = PythonOperator(
        task_id="3_test_import_etl",
        python_callable=test_import_etl,
    )
    
    # Test 4 : Connexion DWH
    task_dwh = PythonOperator(
        task_id="4_test_connexion_dwh",
        python_callable=test_connexion_dwh,
    )
    
    # Test 5 : Lecture données
    task_read = PythonOperator(
        task_id="5_test_lecture_dim_temps",
        python_callable=test_lecture_dim_temps,
    )
    
    # Test 6 : Commande bash simple
    task_bash = BashOperator(
        task_id="6_test_bash",
        bash_command='echo "✅ Bash OK - $(date)"',
    )
    
    # Chaînage des tâches (séquentiel)
    task_hello >> task_env >> task_imports >> task_dwh >> task_read >> task_bash