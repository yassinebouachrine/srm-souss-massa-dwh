"""
ETL - PCWIN (SQL Server ScadaNetDb)
Étape : EXTRACT (Bronze)

Rôle :
- Se connecter au SQL Server PCWIN
- Exécuter la requête (jointure Stations × NumericInformations × internal_numeric_archives)
- Extraire par chunk pour économiser la mémoire (volumétrie potentiellement énorme)
- Ajouter les métadonnées de traçabilité
- Sauvegarder en Parquet dans data/bronze/pcwin/

Filtre incrémental :
- Par défaut : depuis date_min_default du config
- Peut être surchargé par argument (pour reload full ou daily)
"""
from datetime import datetime, date
import pandas as pd

from etl.common.config import CONFIG
from etl.common.logger import get_logger
from etl.common.db_pcwin import get_pcwin_engine, test_pcwin_connection, read_pcwin_sql
from etl.common.io_utils import save_parquet

logger = get_logger(__name__)

SOURCE_NAME = "pcwin"
SOURCE_CFG = CONFIG["sources"][SOURCE_NAME]


# ═══════════════════════════════════════════════════════════════
# REQUÊTE SQL — Alignée sur le code de l'encadrant
# ═══════════════════════════════════════════════════════════════

SQL_QUERY_PCWIN = """
SELECT
    s.station_id AS station_id,
    s.label AS nom_station,
    ni.numericInformation_id AS variable_id,
    ni.label AS libelle_mesure,
    ni.unit AS unite,
    ina.[date] AS datehe,
    CAST(ina.[date] AS date) AS date,
    ina.value AS valeur
FROM dbo.internal_numeric_archives ina
INNER JOIN dbo.NumericInformations ni
    ON ina.numericInformation_id = ni.numericInformation_id
INNER JOIN dbo.NumericInformationStation nis
    ON ni.numericInformation_id = nis.numericInformation_id
INNER JOIN dbo.Stations s
    ON nis.station_id = s.station_id
WHERE ina.[date] >= :date_min
ORDER BY ina.[date] ASC;
"""


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _resolve_date_min(date_min: str = None) -> str:
    """Détermine la date min à utiliser pour le filtre."""
    if date_min:
        return date_min
    return SOURCE_CFG.get("date_min_default", "2026-01-01")


def _extract_chunked(date_min: str, chunk_size: int) -> pd.DataFrame:
    """Extraction chunked (pour gros volumes)."""
    logger.info(f"📥 Extraction PCWIN chunked (chunk_size={chunk_size:,}, date_min={date_min})...")

    chunks = []
    total = 0

    iterator = read_pcwin_sql(
        SQL_QUERY_PCWIN,
        params={"date_min": date_min},
        chunksize=chunk_size,
    )

    for i, chunk in enumerate(iterator, 1):
        total += len(chunk)
        chunks.append(chunk)
        logger.info(f"   → Chunk {i} : {len(chunk):,} lignes (total : {total:,})")

    if not chunks:
        return pd.DataFrame()

    df = pd.concat(chunks, ignore_index=True)
    return df


def _extract_full(date_min: str) -> pd.DataFrame:
    """Extraction en une seule requête (petits volumes)."""
    logger.info(f"📥 Extraction PCWIN full (date_min={date_min})...")
    df = read_pcwin_sql(SQL_QUERY_PCWIN, params={"date_min": date_min})
    logger.info(f"   → {len(df):,} lignes extraites")
    return df


# ═══════════════════════════════════════════════════════════════
# POINT D'ENTRÉE PRINCIPAL
# ═══════════════════════════════════════════════════════════════

def run_extract(date_min: str = None, use_chunks: bool = True) -> dict:
    """
    Exécute l'extraction PCWIN complète (Bronze).
    
    Args:
        date_min: date min au format 'YYYY-MM-DD' (défaut : config)
        use_chunks: True pour extraction par chunks (recommandé)
    
    Returns:
        dict avec stats et chemin du Parquet créé
    """
    logger.info("=" * 70)
    logger.info("🥉 BRONZE - EXTRACTION PCWIN (SQL Server ScadaNetDb)")
    logger.info("=" * 70)

    date_extraction = datetime.now()

    # 1. Test connexion
    if not test_pcwin_connection():
        return {"status": "error", "error": "Connexion PCWIN échouée"}

    # 2. Résoudre paramètres
    date_min_used = _resolve_date_min(date_min)
    chunk_size = int(SOURCE_CFG.get("chunk_size", 100000))

    logger.info(f"   • date_min : {date_min_used}")
    logger.info(f"   • chunk_size : {chunk_size:,}")
    logger.info("-" * 70)

    # 3. Extraction
    try:
        if use_chunks:
            df = _extract_chunked(date_min_used, chunk_size)
        else:
            df = _extract_full(date_min_used)
    except Exception as e:
        logger.error(f"❌ Erreur extraction : {e}", exc_info=True)
        return {"status": "error", "error": str(e)}

    if df.empty:
        logger.warning("⚠️  Aucune donnée extraite depuis PCWIN")
        return {"status": "empty", "date_min": date_min_used}

    # 4. Enrichissement métadonnées
    df["source_code"]     = SOURCE_CFG["source_code"]     # "PCWIN"
    df["date_extraction"] = date_extraction
    # id_pmac au format compatible dim_point_mesure (PCWIN_57)
    df["id_pmac"]         = "PCWIN_" + df["station_id"].astype(str)
    # Variable_Key (utile pour cross-check)
    df["variable_key"]    = df["id_pmac"] + "_" + df["variable_id"].astype(str)

    # 5. Statistiques
    logger.info("-" * 70)
    logger.info(f"📊 EXTRACTION TERMINÉE :")
    logger.info(f"   • Total mesures       : {len(df):,}")
    logger.info(f"   • Stations distinctes : {df['station_id'].nunique()}")
    logger.info(f"   • Variables distinctes: {df['variable_id'].nunique()}")
    logger.info(f"   • Plage temporelle    : {df['datehe'].min()} → {df['datehe'].max()}")
    logger.info(f"   • Unités présentes    : {sorted(df['unite'].dropna().unique().tolist())}")

    # 6. Sauvegarde Parquet
    bronze_folder = SOURCE_CFG.get("bronze_folder", "pcwin")
    path = save_parquet(df, "bronze", bronze_folder, "mesures")

    logger.info("=" * 70)
    logger.info("✅ EXTRACTION PCWIN TERMINÉE")
    logger.info("=" * 70)

    return {
        "status":              "success",
        "date_min":            date_min_used,
        "nb_mesures":          len(df),
        "nb_stations":         int(df["station_id"].nunique()),
        "nb_variables":        int(df["variable_id"].nunique()),
        "date_heure_min":      str(df["datehe"].min()),
        "date_heure_max":      str(df["datehe"].max()),
        "bronze_parquet":      str(path),
    }


if __name__ == "__main__":
    import sys
    date_min_arg = sys.argv[1] if len(sys.argv) > 1 else None
    result = run_extract(date_min=date_min_arg)
    print("\n📋 Résultat :")
    for k, v in result.items():
        print(f"   • {k}: {v}")