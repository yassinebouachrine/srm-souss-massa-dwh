"""
DAG Mensuel : Ingestion de la clientèle & consommations GSTCOM + Refresh Vues PBI.
Fréquence : Le 1er du mois à 04:00 (Heure Maroc).
"""
import sys
from airflow import DAG
from airflow.operators.python import PythonOperator

sys.path.insert(0, "/opt/airflow")

from common.constants import DEFAULT_ARGS, START_DATE, SCHEDULE_MONTHLY_1ST, TAG_MONTHLY, TAG_GSTCOM
from common.notifications import task_failure_callback

from etl.pipelines.gstcom.extract import run_extract
from etl.pipelines.gstcom.transform import run_transform
from etl.pipelines.gstcom.load import run_load
from scripts.refresh_pbi_views import main as refresh_views

with DAG(
    dag_id="monthly_etl_gstcom",
    description="Pipeline ETL mensuel GSTCOM + Rafraîchissement des vues matérialisées Power BI",
    default_args={
        **DEFAULT_ARGS,
        "on_failure_callback": task_failure_callback,
    },
    start_date=START_DATE,
    schedule=SCHEDULE_MONTHLY_1ST,
    catchup=False,
    tags=[TAG_MONTHLY, TAG_GSTCOM, "clientele"],
) as dag:

    task_extract = PythonOperator(
        task_id="extract_bronze_gstcom",
        python_callable=run_extract,
    )

    task_transform = PythonOperator(
        task_id="transform_silver_gstcom",
        python_callable=run_transform,
    )

    task_load = PythonOperator(
        task_id="load_gold_gstcom",
        python_callable=run_load,
    )

    task_refresh_pbi = PythonOperator(
        task_id="refresh_materialized_views_pbi",
        python_callable=refresh_views,
    )

    # Flux : Extract -> Transform -> Load -> Refresh PBI
    task_extract >> task_transform >> task_load >> task_refresh_pbi