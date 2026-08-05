"""Connexion SQL Server (PCWIN ScadaNetDb) centralisée."""
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
import pandas as pd
from etl.common.config import get_env
from etl.common.logger import get_logger

logger = get_logger(__name__)

_engine_pcwin: Engine = None


def get_pcwin_engine() -> Engine:
    """Retourne un engine SQLAlchemy pour PCWIN (singleton)."""
    global _engine_pcwin
    if _engine_pcwin is None:
        host = get_env("PCWIN_HOST")
        port = get_env("PCWIN_PORT", "51433")
        db   = get_env("PCWIN_DATABASE", "ScadaNetDb")
        user = get_env("PCWIN_USER")
        pwd  = get_env("PCWIN_PASSWORD")
        driver = get_env("PCWIN_DRIVER", "pymssql")

        if not user or not pwd:
            raise ValueError(
                "❌ PCWIN_USER et PCWIN_PASSWORD requis dans .env pour la connexion PCWIN"
            )

        if driver == "pymssql":
            url = f"mssql+pymssql://{user}:{pwd}@{host}:{port}/{db}"
        elif driver == "pyodbc":
            # Nécessite driver ODBC installé
            url = (
                f"mssql+pyodbc://{user}:{pwd}@{host}:{port}/{db}"
                f"?driver=ODBC+Driver+17+for+SQL+Server"
            )
        else:
            raise ValueError(f"Driver PCWIN inconnu : {driver}")

        logger.info(f"🔌 Connexion PCWIN : {user}@{host}:{port}/{db} (driver={driver})")
        _engine_pcwin = create_engine(url, pool_pre_ping=True, pool_size=2, max_overflow=5)
    return _engine_pcwin


def test_pcwin_connection() -> bool:
    """Test rapide de la connexion PCWIN."""
    try:
        with get_pcwin_engine().connect() as conn:
            result = conn.execute(text("SELECT @@VERSION AS version")).fetchone()
            logger.info(f"✅ PCWIN connecté : {result[0][:80]}...")
        return True
    except Exception as e:
        logger.error(f"❌ Connexion PCWIN échouée : {e}")
        return False


def read_pcwin_sql(query: str, params: dict = None, chunksize: int = None) -> pd.DataFrame:
    """
    Exécute un SELECT sur PCWIN.
    Si chunksize précisé, retourne un iterator (pour gros volumes).
    """
    engine = get_pcwin_engine()
    if chunksize:
        return pd.read_sql(text(query), engine, params=params, chunksize=chunksize)
    else:
        return pd.read_sql(text(query), engine, params=params)


if __name__ == "__main__":
    # Test rapide
    if test_pcwin_connection():
        df = read_pcwin_sql("SELECT TOP 5 station_id, label FROM dbo.Stations")
        print(df.to_string(index=False))