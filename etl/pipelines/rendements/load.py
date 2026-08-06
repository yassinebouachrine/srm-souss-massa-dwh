"""
ETL - Rendements Étage
Étape : LOAD (Gold)

UPSERT dans dwh.fait_rendement_etage
"""
from datetime import datetime
import pandas as pd
from sqlalchemy import text

from etl.common.logger import get_logger
from etl.common.db import get_engine, read_sql
from etl.common.io_utils import get_latest_parquet, read_parquet, save_parquet

logger = get_logger(__name__)

SOURCE_NAME = "rendements"
BATCH_SIZE = 500

# id_secteur=0 (INCONNU) pour rendements agrégés au niveau étage
ID_SECTEUR_INCONNU = 0


def _to_pg_int(v):
    if pd.isna(v): return None
    return int(v)

def _to_pg_float(v):
    if pd.isna(v): return None
    return float(v)


UPSERT_SQL = """
INSERT INTO dwh.fait_rendement_etage (
    id_temps, id_etage, id_secteur,
    volume_amene, volume_facture, volume_pertes,
    nb_clients, rendement, lineaire_km, ilp,
    source_donnees, fichier_source, date_chargement
) VALUES (
    :id_temps, :id_etage, :id_secteur,
    :volume_amene, :volume_facture, :volume_pertes,
    :nb_clients, :rendement, :lineaire_km, :ilp,
    :source_donnees, :fichier_source, :date_chargement
)
ON CONFLICT (id_temps, id_etage, id_secteur) DO UPDATE SET
    volume_amene    = EXCLUDED.volume_amene,
    volume_facture  = EXCLUDED.volume_facture,
    volume_pertes   = EXCLUDED.volume_pertes,
    nb_clients      = EXCLUDED.nb_clients,
    rendement       = EXCLUDED.rendement,
    lineaire_km     = EXCLUDED.lineaire_km,
    ilp             = EXCLUDED.ilp,
    source_donnees  = EXCLUDED.source_donnees,
    fichier_source  = EXCLUDED.fichier_source,
    date_chargement = EXCLUDED.date_chargement;
"""


def resolve_sk(df: pd.DataFrame) -> tuple:
    """Résout id_etage depuis code_etage."""
    logger.info("🔑 Résolution SK...")
    
    df_etages = read_sql("SELECT id_etage, code_etage FROM dwh.dim_etage")
    map_etage = dict(zip(df_etages["code_etage"], df_etages["id_etage"]))
    
    df = df.copy()
    df["id_etage"]   = df["code_etage"].map(map_etage)
    df["id_secteur"] = ID_SECTEUR_INCONNU
    
    df["motif_rejet"] = None
    df.loc[df["id_etage"].isna(), "motif_rejet"] = "id_etage_introuvable"
    
    df_rej   = df[df["motif_rejet"].notna()].copy()
    df_valid = df[df["motif_rejet"].isna()].copy()
    
    logger.info(f"   ✅ {len(df_valid)} valides | ❌ {len(df_rej)} rejets SK")
    return df_valid, df_rej


def load_rendements(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"inserted_or_updated": 0}
    
    now = datetime.now()
    records = [
        {
            "id_temps":       _to_pg_int(row["id_temps"]),
            "id_etage":       _to_pg_int(row["id_etage"]),
            "id_secteur":     _to_pg_int(row["id_secteur"]),
            "volume_amene":   _to_pg_float(row["volume_amene"]),
            "volume_facture": _to_pg_float(row["volume_facture"]),
            "volume_pertes":  _to_pg_float(row["volume_pertes"]),
            "nb_clients":     _to_pg_int(row["nb_clients"]),
            "rendement":      _to_pg_float(row["rendement"]),
            "lineaire_km":    _to_pg_float(row["lineaire_km"]),
            "ilp":            _to_pg_float(row["ilp"]),
            "source_donnees": str(row.get("source_donnees", "")),
            "fichier_source": "histo_pbi+vol_amene",
            "date_chargement": now,
        }
        for _, row in df.iterrows()
    ]
    
    engine = get_engine()
    stmt = text(UPSERT_SQL)
    total = 0
    
    logger.info(f"📤 UPSERT par batch de {BATCH_SIZE}...")
    with engine.begin() as conn:
        for i in range(0, len(records), BATCH_SIZE):
            batch = records[i:i+BATCH_SIZE]
            conn.execute(stmt, batch)
            total += len(batch)
    
    logger.info(f"✅ {total} lignes UPSERT dans dwh.fait_rendement_etage")
    return {"inserted_or_updated": total}


def run_load() -> dict:
    logger.info("=" * 70)
    logger.info("🥇 GOLD - CHARGEMENT DWH RENDEMENTS")
    logger.info("=" * 70)
    
    result = {"status": "success"}
    
    try:
        path = get_latest_parquet("silver", SOURCE_NAME, "rendements")
        df_silver = read_parquet(path)
        logger.info(f"📖 Silver : {len(df_silver)} lignes")
        
        df_valid, df_rej = resolve_sk(df_silver)
        
        if not df_rej.empty:
            save_parquet(df_rej, "rejects", SOURCE_NAME, "rendements_rejets_sk")
        
        stats = load_rendements(df_valid)
        result.update({
            "silver_total":        len(df_silver),
            "valides":             len(df_valid),
            "rejets_sk":           len(df_rej),
            **stats,
        })
        
    except Exception as e:
        logger.error(f"❌ Erreur : {e}", exc_info=True)
        result["status"] = "error"
        result["error"] = str(e)
    
    logger.info("=" * 70)
    logger.info("✅ CHARGEMENT TERMINÉ")
    logger.info("=" * 70)
    return result


if __name__ == "__main__":
    import json
    result = run_load()
    print(json.dumps(result, indent=2, default=str))