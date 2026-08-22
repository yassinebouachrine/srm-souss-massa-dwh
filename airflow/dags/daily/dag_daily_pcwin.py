"""
DAG Quotidien : Ingestion des mesures capteurs PCWIN (SQL Server ScadaNetDb).
Fréquence : Tous les jours à 02:30 (Heure Maroc).
"""
import sys
from airflow import DAG
from airflow.operators.python import PythonOperator

sys.path.insert(0, "/opt/airflow")

from common.constants import DEFAULT_ARGS, START_DATE, TAG_DAILY, TAG_PCWIN
from common.notifications import task_failure_callback

from etl.pipelines.pcwin.extract import run_extract
from etl.pipelines.pcwin.transform import run_transform
from etl.pipelines.pcwin.load import run_load

with DAG(
    dag_id="daily_etl_pcwin",
    description="Pipeline ETL quotidien PCWIN (Extract SQL Server -> Transform -> Load Gold DWH)",
    default_args={
        **DEFAULT_ARGS,
        "on_failure_callback": task_failure_callback,
    },
    start_date=START_DATE,
    schedule="30 2 * * *",  # 02h30
    catchup=False,
    tags=[TAG_DAILY, TAG_PCWIN, "capteurs"],
) as dag:

    task_extract = PythonOperator(
        task_id="extract_bronze_pcwin",
        python_callable=run_extract,
    )

    task_transform = PythonOperator(
        task_id="transform_silver_pcwin",
        python_callable=run_transform,
    )

    task_load = PythonOperator(
        task_id="load_gold_pcwin",
        python_callable=run_load,
    )

    task_extract >> task_transform >> task_load