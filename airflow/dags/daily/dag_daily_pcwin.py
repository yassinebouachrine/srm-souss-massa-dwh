"""
DAG Quotidien : Ingestion des mesures capteurs PCWIN
(SQL Server ScadaNetDb).

Fréquence : Tous les jours à 02:30 (Heure Maroc).
"""

import sys

from airflow import DAG
from airflow.operators.python import PythonOperator

sys.path.insert(0, "/opt/airflow")

from common.constants import (
    DEFAULT_ARGS,
    START_DATE,
    TAG_DAILY,
    TAG_PCWIN,
)

from common.notifications import (
    dag_success_callback,
    dag_failure_callback,
)
from etl.pipelines.pcwin.extract import run_extract
from etl.pipelines.pcwin.transform import run_transform
from etl.pipelines.pcwin.load import run_load


with DAG(
    dag_id="daily_etl_pcwin",

    description=(
        "Pipeline ETL quotidien PCWIN "
        "(Extract SQL Server -> Transform -> Load Gold DWH)"
    ),

    # Paramètres communs aux tâches
    default_args=DEFAULT_ARGS,

    start_date=START_DATE,

    schedule="30 2 * * *",

    catchup=False,

    tags=[
        TAG_DAILY,
        TAG_PCWIN,
        "capteurs",
    ],

    # ==========================================
    # NOTIFICATIONS DU DAG
    # ==========================================

    on_success_callback=dag_success_callback,
    on_failure_callback=dag_failure_callback,

) as dag:

    # 1. Extraction depuis SQL Server / ScadaNetDb
    task_extract = PythonOperator(
        task_id="extract_bronze_pcwin",
        python_callable=run_extract,
    )

    # 2. Transformation
    task_transform = PythonOperator(
        task_id="transform_silver_pcwin",
        python_callable=run_transform,
    )

    # 3. Chargement dans le DWH
    task_load = PythonOperator(
        task_id="load_gold_pcwin",
        python_callable=run_load,
    )

    # Chaînage : Extract -> Transform -> Load
    task_extract >> task_transform >> task_load

