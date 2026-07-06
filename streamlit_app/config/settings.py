"""
============================================================
SRM Souss-Massa - Configuration Streamlit
============================================================
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Charger .env
project_root = Path(__file__).parent.parent.parent
load_dotenv(project_root / '.env')


class Settings:
    """Configuration de l'application"""
    
    # PostgreSQL
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "srm_datawarehouse")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
    
    # Auth
    AUTH_MODE = os.getenv("AUTH_MODE", "simple")
    DEV_USERNAME = os.getenv("DEV_USERNAME", "admin")
    DEV_PASSWORD = os.getenv("DEV_PASSWORD", "admin123")
    
    # App
    APP_TITLE = "SRM Souss-Massa - Saisie Données"
    APP_ICON = "🌊"
    
    # Environnement
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development_local")
    
    @property
    def db_connection_string(self):
        """Retourne la chaîne de connexion PostgreSQL"""
        return (
            f"postgresql+psycopg2://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}"
            f"/{self.POSTGRES_DB}"
        )


settings = Settings()