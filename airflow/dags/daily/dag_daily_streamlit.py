"""
DAG Quotidien : Ingestion des saisies Streamlit validées au niveau régional.
Fréquence : Tous les jours à 03:00 (Heure Maroc).
"""
import sys
from airflow import DAG
from airflow.operators.python import PythonOperator

sys.path.insert(0, "/opt/airflow")

from common.constants import DEFAULT_ARGS, START_DATE, TAG_DAILY, TAG_STREAMLIT
from common.notifications import task_failure_callback

from etl.pipelines.streamlit_indicateurs_reclamations.extract import run_extract
from etl.pipelines.streamlit_indicateurs_reclamations.transform import run_transform
from etl.pipelines.streamlit_indicateurs_reclamations.load import run_load

with DAG(
    dag_id="daily_etl_streamlit",
    description="Pipeline ETL quotidien Streamlit (statut=valide_regional -> Gold DWH)",
    default_args={
        **DEFAULT_ARGS,
        "on_failure_callback": task_failure_callback,
    },
    start_date=START_DATE,
    schedule="0 3 * * *",  # 03h00
    catchup=False,
    tags=[TAG_DAILY, TAG_STREAMLIT, "saisie"],
) as dag:

    task_extract = PythonOperator(
        task_id="extract_bronze_streamlit",
        python_callable=run_extract,
    )

    task_transform = PythonOperator(
        task_id="transform_silver_streamlit",
        python_callable=run_transform,
    )

    task_load = PythonOperator(
        task_id="load_gold_streamlit",
        python_callable=run_load,
    )

    task_extract >> task_transform >> task_load