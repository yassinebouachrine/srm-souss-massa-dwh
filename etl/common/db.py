"""Connexion PostgreSQL centralisée."""
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
import pandas as pd
from etl.common.config import get_env

_engine: Engine = None


def get_engine() -> Engine:
    """Retourne un engine SQLAlchemy (singleton)."""
    global _engine
    if _engine is None:
        user = get_env("POSTGRES_USER")
        password = get_env("POSTGRES_PASSWORD")
        host = get_env("POSTGRES_HOST", "localhost")
        port = get_env("POSTGRES_PORT", "5432")
        db = get_env("POSTGRES_DB")

        url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
        _engine = create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=10)
    return _engine


def read_sql(query: str, params: dict = None) -> pd.DataFrame:
    """Exécute un SELECT et retourne un DataFrame."""
    with get_engine().connect() as conn:
        return pd.read_sql(text(query), conn, params=params)


def execute(query: str, params: dict = None) -> None:
    """Exécute un INSERT/UPDATE/DELETE."""
    with get_engine().begin() as conn:
        conn.execute(text(query), params or {})


def test_connection() -> bool:
    """Test rapide de la connexion."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"❌ Connexion échouée : {e}")
        return False