"""
DAG Quotidien : Ingestion des 6 fichiers Excel Legacy (Indicateurs & Réclamations DP).
Source : Dossier partagé OneDrive / Réseau avec les 6 fichiers Excel des DP.
Fréquence : Tous les jours à 01:00 (Heure Maroc) — avant le traitement PMAC/PCWIN.
"""
import sys
from airflow import DAG
from airflow.operators.python import PythonOperator

sys.path.insert(0, "/opt/airflow")

from common.constants import DEFAULT_ARGS, START_DATE, TAG_DAILY, TAG_EXCEL
from common.notifications import task_failure_callback, task_success_callback

# Import des fonctions du pipeline Excel Legacy
from etl.pipelines.indicateurs_reclamations.extract import run_extract
from etl.pipelines.indicateurs_reclamations.transform import run_transform
from etl.pipelines.indicateurs_reclamations.load import run_load

with DAG(
    dag_id="daily_etl_excel_legacy",
    description="Pipeline ETL quotidien Excel Legacy (Indicateurs & Réclamations des 6 DP -> Gold DWH)",
    default_args={
        **DEFAULT_ARGS,
        "on_failure_callback": task_failure_callback,
        "on_success_callback": task_success_callback,
    },
    start_date=START_DATE,
    schedule="0 1 * * *",  # Tous les jours à 01h00 du matin
    catchup=False,
    tags=[TAG_DAILY, TAG_EXCEL, "dp_performance"],
) as dag:

    # 1. Extraction des 6 fichiers Excel (Agadir, Chtouka, Inezgane, Taroudant, Tata, Tiznit)
    task_extract = PythonOperator(
        task_id="extract_bronze_excel_legacy",
        python_callable=run_extract,
    )

    # 2. Unpivot, normalisation des périodes (ex: jan_25 -> id_temps) et mapping libellés
    task_transform = PythonOperator(
        task_id="transform_silver_excel_legacy",
        python_callable=run_transform,
    )

    # 3. Résolution des SK et UPSERT dans dwh.fait_indicateurs_performance_dp & dwh.fait_reclamation
    task_load = PythonOperator(
        task_id="load_gold_excel_legacy",
        python_callable=run_load,
    )

    # Chaînage : Extract -> Transform -> Load
    task_extract >> task_transform >> task_load