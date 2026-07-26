"""
Résolution des Surrogate Keys (SK) depuis les dimensions du DWH.
Met en cache les mappings pour éviter des requêtes répétées.
"""
from functools import lru_cache
import pandas as pd
from etl.common.db import read_sql
from etl.common.logger import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_dp_mapping() -> dict:
    """Retourne {code_dp: id_dp}."""
    df = read_sql("SELECT id_dp, code_dp FROM dwh.dim_dp")
    return dict(zip(df["code_dp"], df["id_dp"]))


@lru_cache(maxsize=1)
def get_centre_mapping() -> dict:
    """Retourne {code_centre: id_centre}."""
    df = read_sql("SELECT id_centre, code_centre FROM dwh.dim_centre")
    return dict(zip(df["code_centre"], df["id_centre"]))


@lru_cache(maxsize=1)
def get_indicateur_mapping() -> dict:
    """Retourne {code_indicateur: id_type_indicateur}."""
    df = read_sql(
        "SELECT id_type_indicateur, code_indicateur FROM dwh.dim_type_indicateur_dp"
    )
    return dict(zip(df["code_indicateur"], df["id_type_indicateur"]))


@lru_cache(maxsize=1)
def get_reclamation_mapping() -> dict:
    """Retourne {code: id_type}."""
    df = read_sql("SELECT id_type, code FROM dwh.dim_type_reclamation")
    return dict(zip(df["code"], df["id_type"]))


def date_to_id_temps(date_value) -> int:
    """
    Convertit une date en id_temps (format YYYYMMDD).
    Ex: 2025-01-01 → 20250101
    """
    d = pd.to_datetime(date_value)
    return int(d.strftime("%Y%m%d"))


def clear_cache():
    """Vide le cache (à appeler après un rechargement des dimensions)."""
    get_dp_mapping.cache_clear()
    get_centre_mapping.cache_clear()
    get_indicateur_mapping.cache_clear()
    get_reclamation_mapping.cache_clear()
    logger.info("🔄 Cache des mappings de dimensions vidé")