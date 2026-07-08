# config/settings.py
import os
from pathlib import Path
from dotenv import load_dotenv

# ─── Load .env from project root ───
# Structure attendue :
#   srm-souss-massa-dwh/
#   ├── .env
#   └── streamlit_app/
#       └── config/settings.py
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    # Fallback : chercher un .env local au projet streamlit
    load_dotenv()


# ════════════════════════════════════════════════════════════════
# Environnement
# ════════════════════════════════════════════════════════════════
ENVIRONMENT = os.getenv("ENVIRONMENT", "development_local")
TIMEZONE = os.getenv("TIMEZONE", "Africa/Agadir")
IS_PRODUCTION = ENVIRONMENT.lower().startswith("prod")


# ════════════════════════════════════════════════════════════════
# Database Configuration (PostgreSQL)
# ════════════════════════════════════════════════════════════════
DB_CONFIG = {
    "host":     os.getenv("POSTGRES_HOST", "localhost"),
    "port":     int(os.getenv("POSTGRES_PORT", 5432)),
    "database": os.getenv("POSTGRES_DB", "srm_datawarehouse"),
    "user":     os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", ""),
}

# Connection string (utile pour SQLAlchemy si besoin plus tard)
DATABASE_URL = (
    f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)


# ════════════════════════════════════════════════════════════════
# Application Configuration
# ════════════════════════════════════════════════════════════════
APP_NAME = "SRM Souss-Massa - Data Platform"
APP_VERSION = "1.0.0"
REGION = "Souss-Massa"
SIEGE = "Agadir"


# ════════════════════════════════════════════════════════════════
# Streamlit Configuration
# ════════════════════════════════════════════════════════════════
STREAMLIT_PORT = int(os.getenv("STREAMLIT_SERVER_PORT", 8501))
STREAMLIT_HOST = os.getenv("STREAMLIT_SERVER_ADDRESS", "localhost")


# ════════════════════════════════════════════════════════════════
# Security Configuration
# ════════════════════════════════════════════════════════════════
# ⚠️ En production, ajoutez SECRET_KEY à votre .env
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "srm-souss-massa-secret-key-2024-change-in-production"
)
TOKEN_EXPIRY_HOURS = int(os.getenv("TOKEN_EXPIRY_HOURS", 8))
MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", 5))
LOCKOUT_DURATION_MINUTES = int(os.getenv("LOCKOUT_DURATION_MINUTES", 30))

# Warning si en production avec la clé par défaut
if IS_PRODUCTION and SECRET_KEY.startswith("srm-souss-massa-secret-key-2024"):
    import warnings
    warnings.warn(
        "⚠️ SECRET_KEY par défaut utilisée en production ! "
        "Définissez SECRET_KEY dans le fichier .env"
    )


# ════════════════════════════════════════════════════════════════
# Data Folders
# ════════════════════════════════════════════════════════════════
DATA_RAW_FOLDER = os.getenv("DATA_RAW_FOLDER", "./data/raw")
DATA_PROCESSED_FOLDER = os.getenv("DATA_PROCESSED_FOLDER", "./data/processed")


# ════════════════════════════════════════════════════════════════
# Validation Workflow
# ════════════════════════════════════════════════════════════════
VALIDATION_STATUS = {
    "BROUILLON":        "brouillon",
    "SOUMIS":           "soumis",
    "VALIDE_DP":        "valide_dp",
    "REJETE_DP":        "rejete_dp",
    "VALIDE_REGIONAL":  "valide_regional",
    "REJETE_REGIONAL":  "rejete_regional",
}


# ════════════════════════════════════════════════════════════════
# Helper : afficher la config au démarrage (utile en debug)
# ════════════════════════════════════════════════════════════════
def print_config_summary():
    """Print a summary of the configuration (without sensitive data)."""
    print("=" * 60)
    print(f"  {APP_NAME} v{APP_VERSION}")
    print("=" * 60)
    print(f"  Environment : {ENVIRONMENT}")
    print(f"  Timezone    : {TIMEZONE}")
    print(f"  DB Host     : {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"  DB Name     : {DB_CONFIG['database']}")
    print(f"  DB User     : {DB_CONFIG['user']}")
    print(f"  Streamlit   : http://{STREAMLIT_HOST}:{STREAMLIT_PORT}")
    print(f"  .env path   : {ENV_PATH}  (exists: {ENV_PATH.exists()})")
    print("=" * 60)


if __name__ == "__main__":
    print_config_summary()