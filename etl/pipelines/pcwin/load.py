"""
ETL - PCWIN
Étape : LOAD (Gold)

Rôle :
- Lire Parquet Silver
- UPSERT dans dwh.fait_mesure_temps_reel avec source_saisie='pcwin'
- Gestion idempotente via contrainte UNIQUE
- Batch de 1000 pour performances
"""
from datetime import datetime
import pandas as pd
from sqlalchemy import text

from etl.common.config import CONFIG
from etl.common.logger import get_logger
from etl.common.db import get_engine
from etl.common.io_utils import get_latest_parquet, read_parquet

logger = get_logger(__name__)

SOURCE_NAME = "pcwin"
BATCH_SIZE = 1000


def _to_pg_int(v):
    if pd.isna(v): return None
    return int(v)


def _to_pg_float(v):
    if pd.isna(v): return None
    return float(v)


def _to_pg_str(v):
    if pd.isna(v): return None
    return str(v)


def _to_pg_datetime(v):
    if pd.isna(v): return None
    return pd.to_datetime(v).to_pydatetime()


UPSERT_MESURE_SQL = """
INSERT INTO dwh.fait_mesure_temps_reel (
    id_temps, id_etage, id_secteur, id_point_mesure, id_source_mesure,
    heure,
    index_compteur, pression_bar, pression_amont_bar, pression_aval_bar,
    debit_m3_h, volume_15min,
    qualite_donnees, voie, canal, unite,
    fichier_source, canal_source, date_chargement
)
VALUES (
    :id_temps, :id_etage, :id_secteur, :id_point_mesure, :id_source_mesure,
    :heure,
    :index_compteur, :pression_bar, :pression_amont_bar, :pression_aval_bar,
    :debit_m3_h, :volume_15min,
    :qualite_donnees, :voie, :canal, :unite,
    :fichier_source, :canal_source, :date_chargement
)
ON CONFLICT (id_point_mesure, heure, voie, canal)
DO UPDATE SET
    index_compteur       = EXCLUDED.index_compteur,
    pression_bar         = EXCLUDED.pression_bar,
    pression_amont_bar   = EXCLUDED.pression_amont_bar,
    pression_aval_bar    = EXCLUDED.pression_aval_bar,
    debit_m3_h           = EXCLUDED.debit_m3_h,
    volume_15min         = EXCLUDED.volume_15min,
    qualite_donnees      = EXCLUDED.qualite_donnees,
    unite                = EXCLUDED.unite,
    fichier_source       = EXCLUDED.fichier_source,
    canal_source         = EXCLUDED.canal_source,
    date_chargement      = EXCLUDED.date_chargement;
"""


def load_mesures(df: pd.DataFrame) -> dict:
    """Charge dans dwh.fait_mesure_temps_reel (UPSERT)."""
    if df.empty:
        logger.warning("⚠️  Aucune mesure à charger")
        return {"inserted_or_updated": 0}

    logger.info(f"📥 Préparation de {len(df):,} records...")
    now = datetime.now()

    records = [
        {
            "id_temps":            _to_pg_int(row["id_temps"]),
            "id_etage":            _to_pg_int(row["id_etage"]),
            "id_secteur":          _to_pg_int(row["id_secteur"]),
            "id_point_mesure":     _to_pg_int(row["id_point_mesure"]),
            "id_source_mesure":    _to_pg_int(row["id_source_mesure"]),
            "heure":               _to_pg_datetime(row["datehe"]),
            "index_compteur":      _to_pg_float(row["index_compteur"]),
            "pression_bar":        _to_pg_float(row["pression_bar"]),
            "pression_amont_bar":  _to_pg_float(row["pression_amont_bar"]),
            "pression_aval_bar":   _to_pg_float(row["pression_aval_bar"]),
            "debit_m3_h":          _to_pg_float(row["debit_m3_h"]),
            "volume_15min":        _to_pg_float(row["volume_15min"]),
            "qualite_donnees":     _to_pg_str(row["qualite_donnees"]),
            "voie":                _to_pg_str(row["voie"]),
            "canal":               _to_pg_str(row["canal"]),
            "unite":               _to_pg_str(row["unite"]),
            "fichier_source":      _to_pg_str(row["libelle_mesure"]),   # libellé PCWIN
            "canal_source":        _to_pg_str(row["variable_key"]),      # PCWIN_<sid>_<vid>
            "date_chargement":     now,
        }
        for _, row in df.iterrows()
    ]

    engine = get_engine()
    stmt = text(UPSERT_MESURE_SQL)
    total = 0

    logger.info(f"📤 Chargement par batch de {BATCH_SIZE}...")

    with engine.begin() as conn:
        for i in range(0, len(records), BATCH_SIZE):
            batch = records[i:i + BATCH_SIZE]
            conn.execute(stmt, batch)
            total += len(batch)
            if total % 5000 == 0 or total == len(records):
                logger.info(f"   → {total:,} / {len(records):,} lignes ({100*total/len(records):.1f}%)")

    logger.info(f"✅ {total:,} lignes UPSERT dans dwh.fait_mesure_temps_reel")
    return {"inserted_or_updated": total}


def run_load() -> dict:
    """Exécute le chargement Gold pour PCWIN."""
    logger.info("=" * 70)
    logger.info("🥇 GOLD - CHARGEMENT DWH PCWIN")
    logger.info("=" * 70)

    result = {"status": "success"}

    try:
        # Silver PCWIN a besoin d'être renommé : le pipeline PCWIN utilise 'variable_key'
        # comme équivalent de 'channel'/'canal_source'
        path = get_latest_parquet("silver", SOURCE_NAME, "mesures")
        df_silver = read_parquet(path)
        logger.info(f"📖 Silver : {len(df_silver):,} lignes")

        stats = load_mesures(df_silver)

        result.update({
            "silver_total":         len(df_silver),
            "inserted_or_updated":  stats["inserted_or_updated"],
        })

        if "voie" in df_silver.columns:
            result["stats_par_voie"] = df_silver["voie"].value_counts().to_dict()
        if "qualite_donnees" in df_silver.columns:
            result["stats_par_qualite"] = df_silver["qualite_donnees"].value_counts().to_dict()

    except FileNotFoundError as e:
        logger.error(f"❌ Silver introuvable : {e}")
        result["status"] = "error"
        result["error"] = str(e)
    except Exception as e:
        logger.error(f"❌ Erreur : {e}", exc_info=True)
        result["status"] = "error"
        result["error"] = str(e)

    logger.info("=" * 70)
    logger.info("✅ CHARGEMENT TERMINÉ")
    logger.info("=" * 70)

    return result


if __name__ == "__main__":
    result = run_load()
    print("\n📋 Résultat :")
    import json
    print(json.dumps(result, indent=2, default=str))