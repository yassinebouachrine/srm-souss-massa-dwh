# config/settings.py
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    load_dotenv()


# Environnement
ENVIRONMENT = os.getenv("ENVIRONMENT", "development_local")
TIMEZONE = os.getenv("TIMEZONE", "Africa/Agadir")
IS_PRODUCTION = ENVIRONMENT.lower().startswith("prod")


# Database
DB_CONFIG = {
    "host":     os.getenv("POSTGRES_HOST", "localhost"),
    "port":     int(os.getenv("POSTGRES_PORT", 5432)),
    "database": os.getenv("POSTGRES_DB", "srm_datawarehouse"),
    "user":     os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", ""),
}

DATABASE_URL = (
    f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)


# Application
APP_NAME = "SRM Souss-Massa - Data Platform"
APP_VERSION = "1.0.0"
REGION = "Souss-Massa"
SIEGE = "Agadir"


# Streamlit
STREAMLIT_PORT = int(os.getenv("STREAMLIT_SERVER_PORT", 8501))
STREAMLIT_HOST = os.getenv("STREAMLIT_SERVER_ADDRESS", "localhost")


# ═══════════════════════════════════════════════════
# SÉCURITÉ
# ═══════════════════════════════════════════════════
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "srm-souss-massa-secret-key-2024-change-in-production"
)

# Durée maximale d'une session (heures)
TOKEN_EXPIRY_HOURS = int(os.getenv("TOKEN_EXPIRY_HOURS", 8))

# Timeout d'inactivité (minutes) - après ce délai sans action, déconnexion auto
SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", 5))

# Tentatives de connexion échouées avant verrouillage
MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", 5))

# Durée de verrouillage du compte (minutes)
LOCKOUT_DURATION_MINUTES = int(os.getenv("LOCKOUT_DURATION_MINUTES", 30))

if IS_PRODUCTION and SECRET_KEY.startswith("srm-souss-massa-secret-key-2024"):
    import warnings
    warnings.warn(
        " SECRET_KEY par défaut utilisée en production ! "
        "Définissez SECRET_KEY dans le fichier .env"
    )


# Dossiers données
DATA_RAW_FOLDER = os.getenv("DATA_RAW_FOLDER", "./data/raw")
DATA_PROCESSED_FOLDER = os.getenv("DATA_PROCESSED_FOLDER", "./data/processed")


# Workflow
VALIDATION_STATUS = {
    "BROUILLON":        "brouillon",
    "SOUMIS":           "soumis",
    "VALIDE_DP":        "valide_dp",
    "REJETE_DP":        "rejete_dp",
    "VALIDE_REGIONAL":  "valide_regional",
    "REJETE_REGIONAL":  "rejete_regional",
}


# Matrice des rôles et pages autorisées
ROLE_PERMISSIONS = {
    "agent_dp": [
        "dashboard", "indicateurs", "reclamations", "profil"
    ],
    "admin_dp": [
        "dashboard", "indicateurs", "reclamations",
        "validation_dp", "profil"
    ],
    "admin_regional": [
        "dashboard", "validation_regionale", "administration", "profil"
    ],
    "super_admin": [
        "dashboard", "indicateurs", "reclamations",
        "validation_dp", "validation_regionale",
        "administration", "profil"
    ],
}


def print_config_summary():
    print("=" * 60)
    print(f"  {APP_NAME} v{APP_VERSION}")
    print("=" * 60)
    print(f"  Environment : {ENVIRONMENT}")
    print(f"  DB          : {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    print(f"  Session timeout : {SESSION_TIMEOUT_MINUTES} min")
    print(f"  Token expiry    : {TOKEN_EXPIRY_HOURS} h")
    print("=" * 60)


if __name__ == "__main__":
    print_config_summary()