"""
DAG Quotidien : Ingestion des 6 fichiers Excel Legacy
(Indicateurs & Réclamations DP).

Source : Dossier partagé OneDrive / Réseau
Fréquence : Tous les jours à 01:00 (Heure Maroc)
"""

import sys

from airflow import DAG
from airflow.operators.python import PythonOperator

sys.path.insert(0, "/opt/airflow")

from common.constants import (
    DEFAULT_ARGS,
    START_DATE,
    TAG_DAILY,
    TAG_EXCEL,
)

from common.notifications import (
    dag_success_callback,
    dag_failure_callback,
)
# Import des fonctions du pipeline Excel Legacy
from etl.pipelines.indicateurs_reclamations.extract import run_extract
from etl.pipelines.indicateurs_reclamations.transform import run_transform
from etl.pipelines.indicateurs_reclamations.load import run_load


with DAG(
    dag_id="daily_etl_excel_legacy",

    description=(
        "Pipeline ETL quotidien Excel Legacy "
        "(Indicateurs & Réclamations des 6 DP -> Gold DWH)"
    ),

    # Paramètres communs aux tâches
    default_args=DEFAULT_ARGS,

    start_date=START_DATE,

    schedule="0 1 * * *",

    catchup=False,

    tags=[
        TAG_DAILY,
        TAG_EXCEL,
        "dp_performance",
    ],

    # ==========================================
    # NOTIFICATIONS DU DAG
    # ==========================================

    on_success_callback=dag_success_callback,
    on_failure_callback=dag_failure_callback,

) as dag:

    # 1. Extraction
    task_extract = PythonOperator(
        task_id="extract_bronze_excel_legacy",
        python_callable=run_extract,
    )

    # 2. Transformation
    task_transform = PythonOperator(
        task_id="transform_silver_excel_legacy",
        python_callable=run_transform,
    )


    # 3. Chargement
    task_load = PythonOperator(
        task_id="load_gold_excel_legacy",
        python_callable=run_load,
    )

    # Chaînage
    task_extract >> task_transform >> task_load

