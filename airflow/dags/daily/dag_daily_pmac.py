"""
DAG Quotidien : Ingestion et traitement des mesures capteurs PMAC.
Fréquence : Tous les jours à 02:00 (Heure Maroc).
"""
import sys
from datetime import datetime, timedelta
from pendulum import timezone

from airflow import DAG
from airflow.operators.python import PythonOperator

# Assurer l'accès au projet
sys.path.insert(0, "/opt/airflow")

from common.constants import DEFAULT_ARGS, START_DATE, SCHEDULE_DAILY_2AM, TAG_DAILY, TAG_PMAC
from common.notifications import task_failure_callback, task_success_callback

# Import des fonctions métier du pipeline PMAC
from etl.pipelines.pmac.extract import run_extract
from etl.pipelines.pmac.transform import run_transform
from etl.pipelines.pmac.load import run_load

TZ_MAROC = timezone("Africa/Casablanca")

with DAG(
    dag_id="daily_etl_pmac",
    description="Pipeline ETL quotidien PMAC (Extract CSV -> Transform Silver -> Load Gold DWH)",
    default_args={
        **DEFAULT_ARGS,
        "on_failure_callback": task_failure_callback,
        "on_success_callback": task_success_callback,
    },
    start_date=START_DATE,
    schedule=SCHEDULE_DAILY_2AM,
    catchup=False,
    tags=[TAG_DAILY, TAG_PMAC, "capteurs"],
) as dag:

    # 1. Extraction (Bronze)
    task_extract = PythonOperator(
        task_id="extract_bronze_pmac",
        python_callable=run_extract,
    )

    # 2. Transformation (Silver)
    task_transform = PythonOperator(
        task_id="transform_silver_pmac",
        python_callable=run_transform,
    )

    # 3. Chargement (Gold DWH)
    task_load = PythonOperator(
        task_id="load_gold_pmac",
        python_callable=run_load,
    )

    # Chaînage des tâches : Extract -> Transform -> Load
    task_extract >> task_transform >> task_load