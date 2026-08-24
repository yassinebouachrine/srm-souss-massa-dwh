"""
Constantes partagées par tous les DAGs Airflow.
Centralise les schedules, chemins et paramètres métier.
"""
from datetime import datetime, timedelta
from pendulum import timezone

# ═══════════════════════════════════════════════════════════════
# TIMEZONE
# ═══════════════════════════════════════════════════════════════

TZ_MAROC = timezone("Africa/Casablanca")

# ═══════════════════════════════════════════════════════════════
# DATES DE RÉFÉRENCE
# ═══════════════════════════════════════════════════════════════

# Date de début pour les DAGs (pas de backfill avant cette date)
START_DATE = datetime(2026, 8, 1, tzinfo=TZ_MAROC)

# ═══════════════════════════════════════════════════════════════
# SCHEDULES (cron format)
# ═══════════════════════════════════════════════════════════════
# Quotidien à 2h du matin (heure Maroc)
SCHEDULE_DAILY_2AM = "0 2 * * *"

# Quotidien à 4h du matin
SCHEDULE_DAILY_4AM = "0 4 * * *"

# Mensuel : 1er du mois à 3h
SCHEDULE_MONTHLY_1ST = "0 3 1 * *"

# Toutes les heures (pour refresh vues matérialisées)
SCHEDULE_HOURLY = "0 * * * *"

# À la demande (déclenchement manuel)
SCHEDULE_MANUAL = None

# ═══════════════════════════════════════════════════════════════
# CHEMINS (dans le conteneur Docker)
# ═══════════════════════════════════════════════════════════════

PROJECT_ROOT = "/opt/airflow"
ETL_ROOT = f"{PROJECT_ROOT}/etl"
DATA_ROOT = f"{PROJECT_ROOT}/data"
SCRIPTS_ROOT = f"{PROJECT_ROOT}/scripts"

# ═══════════════════════════════════════════════════════════════
# DEFAULT ARGS pour les DAGs
# ═══════════════════════════════════════════════════════════════

DEFAULT_ARGS = {
    "owner": "airflow_admin",
    "depends_on_past": False,

    "email": ["bouachrinyassin0@gmail.com"],
    "email_on_failure": False,
    "email_on_retry": False,

    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=2),
}

# ═══════════════════════════════════════════════════════════════
# TAGS pour organiser les DAGs dans l'UI
# ═══════════════════════════════════════════════════════════════

TAG_DAILY = "daily"
TAG_MONTHLY = "monthly"
TAG_MANUAL = "on_demand"
TAG_TEST = "test"

TAG_PMAC = "pmac"
TAG_PCWIN = "pcwin"
TAG_GSTCOM = "gstcom"
TAG_STREAMLIT = "streamlit"
TAG_EXCEL = "excel_legacy"
TAG_REFERENTIELS = "referentiels"
TAG_DWH = "dwh"


