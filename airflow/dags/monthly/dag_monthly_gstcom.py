"""
DAG Mensuel : Ingestion de la clientèle & consommations GSTCOM
+ Rafraîchissement des vues pour Power BI.

Fréquence : Le 1er du mois à 03:00 (Heure Maroc).
"""

import sys

from airflow import DAG
from airflow.operators.python import PythonOperator

# Assurer l'accès au projet
sys.path.insert(0, "/opt/airflow")

from common.constants import (
    DEFAULT_ARGS,
    START_DATE,
    SCHEDULE_MONTHLY_1ST,
    TAG_MONTHLY,
    TAG_GSTCOM,
)

from common.notifications import (
    dag_success_callback,
    dag_failure_callback,
)

from etl.pipelines.gstcom.extract import run_extract
from etl.pipelines.gstcom.transform import run_transform
from etl.pipelines.gstcom.load import run_load

from scripts.refresh_pbi_views import run_refresh_views


with DAG(
    dag_id="monthly_etl_gstcom",

    description=(
        "Pipeline ETL mensuel GSTCOM + "
        "Rafraîchissement des vues matérialisées Power BI"
    ),

    # Paramètres communs aux tâches
    default_args=DEFAULT_ARGS,

    start_date=START_DATE,

    schedule=SCHEDULE_MONTHLY_1ST,

    catchup=False,

    tags=[
        TAG_MONTHLY,
        TAG_GSTCOM,
        "clientele",
    ],

    # ==========================================
    # NOTIFICATIONS DU DAG
    # ==========================================

    on_success_callback=dag_success_callback,
    on_failure_callback=dag_failure_callback,

) as dag:

    # 1. Extraction GSTCOM
    task_extract = PythonOperator(
        task_id="extract_bronze_gstcom",
        python_callable=run_extract,
    )
    # 2. Transformation
    task_transform = PythonOperator(
        task_id="transform_silver_gstcom",
        python_callable=run_transform,
    )

    # 3. Chargement dans le Gold DWH
    task_load = PythonOperator(
        task_id="load_gold_gstcom",
        python_callable=run_load,
    )

    # 4. Rafraîchissement des vues
    task_refresh_pbi = PythonOperator(
        task_id="refresh_materialized_views_pbi",
        python_callable=run_refresh_views,
    )

    # Chaînage :
    # Extract -> Transform -> Load -> Refresh PBI
    task_extract >> task_transform >> task_load >> task_refresh_pbi
