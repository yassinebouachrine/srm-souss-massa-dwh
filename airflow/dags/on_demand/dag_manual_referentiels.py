from common.constants import (
    DEFAULT_ARGS,
    START_DATE,
    SCHEDULE_DAILY_2AM,
)

from common.notifications import (
    dag_success_callback,
    dag_failure_callback,
)




"""
DAG À la Demande : Rechargement des référentiels (Matrice, Linéaires, Canaux...) + Rendements.
Déclenchement : Manuel (quand l'encadrant modifie un fichier dans /referentiels/).
"""
import sys
from airflow import DAG
from airflow.operators.python import PythonOperator

sys.path.insert(0, "/opt/airflow")

from common.constants import DEFAULT_ARGS, START_DATE, TAG_MANUAL, TAG_REFERENTIELS
# Imports des scripts de peuplement référentiels
from etl.setup.initialization.seed_dim_point_mesure import main as seed_pmac
from etl.setup.initialization.seed_dim_point_mesure_pcwin import main as seed_pcwin
from etl.setup.initialization.seed_dim_canal_label import main as seed_canal
from etl.setup.initialization.seed_bridge_groupe_point_pcwin import main as seed_bridge_pcwin
from etl.setup.initialization.seed_dim_loc_sec_bridge import main as seed_locsec
from etl.setup.initialization.update_dim_etage_lineaire import main as update_lineaire_etage
from etl.setup.initialization.update_dim_secteur_lineaire import main as update_lineaire_secteur

# Pipeline Rendements
from etl.pipelines.rendements.extract import run_extract as extract_rend
from etl.pipelines.rendements.transform import run_transform as transform_rend
from etl.pipelines.rendements.load import run_load as load_rend

with DAG(
    dag_id="on_demand_update_referentiels_rendements",
    description="Mise à jour manuelle des référentiels réseau & recalcul des rendements",

    # Paramètres communs
    default_args=DEFAULT_ARGS,

    # Notifications email du DAG
    on_success_callback=dag_success_callback,
    on_failure_callback=dag_failure_callback,
    start_date=START_DATE,
    schedule=None,  # Manuel uniquement (aucun déclenchement automatique)
    catchup=False,
    tags=[TAG_MANUAL, TAG_REFERENTIELS, "rendements"],
) as dag:

    task_seed_pmac = PythonOperator(
        task_id="seed_dim_point_mesure_pmac",
        python_callable=seed_pmac,
    )

    task_seed_pcwin = PythonOperator(
        task_id="seed_dim_point_mesure_pcwin",
        python_callable=seed_pcwin,
    )

    task_seed_canal = PythonOperator(
        task_id="seed_dim_canal_label",
        python_callable=seed_canal,
    )

    task_seed_bridge_pcwin = PythonOperator(
        task_id="seed_bridge_groupe_point_pcwin",
        python_callable=seed_bridge_pcwin,
    )
    task_seed_locsec = PythonOperator(
        task_id="seed_dim_loc_sec_bridge",
        python_callable=seed_locsec,
    )

    task_update_lin_etage = PythonOperator(
        task_id="update_lineaire_etage",
        python_callable=update_lineaire_etage,
    )

    task_update_lin_secteur = PythonOperator(
        task_id="update_lineaire_secteur",
        python_callable=update_lineaire_secteur,
    )

    # Rendements
    task_extract_rend = PythonOperator(
        task_id="extract_rendements",
        python_callable=extract_rend,
    )

    task_transform_rend = PythonOperator(
        task_id="transform_rendements",
        python_callable=transform_rend,
    )

    task_load_rend = PythonOperator(
        task_id="load_rendements",
        python_callable=load_rend,
    )

    # Dépendances : Référentiels d'abord (en parallèle puis séquentiel), puis Rendements
    [task_seed_pmac, task_seed_pcwin, task_seed_canal] >> task_seed_bridge_pcwin
    [task_seed_locsec, task_update_lin_etage, task_update_lin_secteur] >> task_extract_rend
    task_extract_rend >> task_transform_rend >> task_load_rend

