"""
ETL - Streamlit Indicateurs & Réclamations
Étape : LOAD (Gold)

Rôle :
- Lire les Parquet silver
- Résoudre les Surrogate Keys via les dimensions du DWH
- Pour les réclamations personnalisées : get_or_create dans DIM_TYPE_RECLAMATION
- UPSERT dans dwh.fait_indicateurs_performance_dp et dwh.fait_reclamation
- source_saisie = 'streamlit' (distingue des données excel_legacy)
"""
from datetime import datetime
import pandas as pd
from sqlalchemy import text

from etl.common.config import CONFIG
from etl.common.logger import get_logger
from etl.common.db import get_engine
from etl.common.io_utils import get_latest_parquet, read_parquet, save_parquet
from etl.common.dim_resolver import (
    get_dp_mapping,
    get_centre_mapping,
    get_indicateur_mapping,
    get_reclamation_mapping,
    get_or_create_reclamation_id,
    clear_cache,
    CENTRE_AGREG_DP_ID,
)

logger = get_logger(__name__)

SOURCE_NAME = "streamlit_indicateurs_reclamations"
SOURCE_SAISIE = CONFIG["sources"][SOURCE_NAME]["source_saisie"]  # 'streamlit'

BATCH_SIZE = 1000


# ═══════════════════════════════════════════════════════════════
# HELPERS TYPES
# ═══════════════════════════════════════════════════════════════

def _to_pg_int(v):
    if pd.isna(v):
        return None
    return int(v)


def _to_pg_float(v):
    if pd.isna(v):
        return None
    return float(v)


def _to_pg_str(v):
    if pd.isna(v):
        return None
    return str(v)


# ═══════════════════════════════════════════════════════════════
# RÉSOLUTION DES SK — INDICATEURS
# ═══════════════════════════════════════════════════════════════

def _resolve_sk_indicateurs(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Résout les SK pour les indicateurs Streamlit."""
    logger.info("🔑 Résolution des Surrogate Keys (indicateurs)...")
    
    clear_cache()
    map_dp     = get_dp_mapping()
    map_centre = get_centre_mapping()
    map_indic  = get_indicateur_mapping()
    
    df = df.copy()
    df["id_dp"]              = df["code_dp"].map(map_dp)
    df["id_type_indicateur"] = df["code_indicateur"].map(map_indic)
    
    # id_centre : soit centre réel, soit AGREG_DP si Recap DP (id_centre NULL dans staging)
    df["id_centre"] = df.apply(
        lambda row: CENTRE_AGREG_DP_ID if row["est_recap_dp"]
        else map_centre.get(row["code_centre"]),
        axis=1,
    )
    
    df["motif_rejet"] = None
    df.loc[df["id_dp"].isna(),              "motif_rejet"] = "id_dp_introuvable"
    df.loc[df["id_type_indicateur"].isna(), "motif_rejet"] = "id_type_indicateur_introuvable"
    df.loc[df["id_centre"].isna(),          "motif_rejet"] = "id_centre_introuvable"
    
    df_rejects = df[df["motif_rejet"].notna()].copy()
    df_valid   = df[df["motif_rejet"].isna()].copy()
    
    logger.info(f"   ✅ Valides : {len(df_valid)} | ❌ Rejets SK : {len(df_rejects)}")
    if not df_rejects.empty:
        for motif, cnt in df_rejects["motif_rejet"].value_counts().items():
            logger.warning(f"      • {motif} : {cnt}")
    
    return df_valid, df_rejects


# ═══════════════════════════════════════════════════════════════
# RÉSOLUTION DES SK — RÉCLAMATIONS (avec get_or_create)
# ═══════════════════════════════════════════════════════════════

def _resolve_sk_reclamations(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Résout les SK pour les réclamations Streamlit.
    
    Particularité : pour les réclamations personnalisées (est_personnalisee_source=True),
    on utilise get_or_create_reclamation_id qui va créer une entrée CUSTOM_<hash>
    dans DIM_TYPE_RECLAMATION si elle n'existe pas déjà.
    """
    logger.info("🔑 Résolution des Surrogate Keys (réclamations)...")
    
    clear_cache()
    map_dp     = get_dp_mapping()
    map_centre = get_centre_mapping()
    map_reclam = get_reclamation_mapping()
    
    df = df.copy()
    df["id_dp"] = df["code_dp"].map(map_dp)
    df["id_centre"] = df.apply(
        lambda row: CENTRE_AGREG_DP_ID if row["est_recap_dp"]
        else map_centre.get(row["code_centre"]),
        axis=1,
    )
    
    # Résolution id_type : différent selon standard/personnalisée
    def _resolve_id_type(row):
        if row["est_personnalisee_source"]:
            # Réclamation personnalisée : get_or_create via hash du libellé
            try:
                return get_or_create_reclamation_id(
                    libelle=row["libelle_reclamation"],
                    categorie=row["categorie_reclamation"] or "Reclamation_Divers",
                )
            except Exception as e:
                logger.error(f"❌ Erreur get_or_create pour '{row['libelle_reclamation']}' : {e}")
                return None
        else:
            # Réclamation standard : lookup direct dans le mapping
            return map_reclam.get(row["code_type"])
    
    df["id_type"] = df.apply(_resolve_id_type, axis=1)
    
    # Détection rejets
    df["motif_rejet"] = None
    df.loc[df["id_dp"].isna(),     "motif_rejet"] = "id_dp_introuvable"
    df.loc[df["id_type"].isna(),   "motif_rejet"] = "id_type_reclamation_introuvable"
    df.loc[df["id_centre"].isna(), "motif_rejet"] = "id_centre_introuvable"
    
    df_rejects = df[df["motif_rejet"].notna()].copy()
    df_valid   = df[df["motif_rejet"].isna()].copy()
    
    logger.info(f"   ✅ Valides : {len(df_valid)} | ❌ Rejets SK : {len(df_rejects)}")
    if not df_rejects.empty:
        for motif, cnt in df_rejects["motif_rejet"].value_counts().items():
            logger.warning(f"      • {motif} : {cnt}")
    
    # Info sur les customs traités
    if not df_valid.empty:
        nb_custom = df_valid["est_personnalisee_source"].sum()
        if nb_custom > 0:
            logger.info(f"   🏷️  {nb_custom} réclamation(s) personnalisée(s) traitée(s) via get_or_create")
    
    return df_valid, df_rejects


# ═══════════════════════════════════════════════════════════════
# UPSERT INDICATEURS
# ═══════════════════════════════════════════════════════════════

UPSERT_INDIC_SQL = """
INSERT INTO dwh.fait_indicateurs_performance_dp
    (id_temps, id_dp, id_centre, id_type_indicateur, valeur,
     source_saisie, fichier_source, onglet_source, date_chargement)
VALUES
    (:id_temps, :id_dp, :id_centre, :id_type_indicateur, :valeur,
     :source_saisie, :fichier_source, :onglet_source, :date_chargement)
ON CONFLICT (id_temps, id_dp, id_centre, id_type_indicateur, source_saisie)
DO UPDATE SET
    valeur          = EXCLUDED.valeur,
    fichier_source  = EXCLUDED.fichier_source,
    onglet_source   = EXCLUDED.onglet_source,
    date_chargement = EXCLUDED.date_chargement;
"""


def load_indicateurs(df: pd.DataFrame) -> dict:
    """Charge les indicateurs Streamlit dans le DWH (UPSERT)."""
    if df.empty:
        logger.warning("⚠️  Aucun indicateur à charger")
        return {"inserted_or_updated": 0}
    
    now = datetime.now()
    
    # Pour Streamlit : fichier_source = source_table, onglet_source = lot_id
    records = [
        {
            "id_temps":           _to_pg_int(row["id_temps"]),
            "id_dp":              _to_pg_int(row["id_dp"]),
            "id_centre":          _to_pg_int(row["id_centre"]),
            "id_type_indicateur": _to_pg_int(row["id_type_indicateur"]),
            "valeur":             _to_pg_float(row["valeur"]),
            "source_saisie":      SOURCE_SAISIE,
            "fichier_source":     _to_pg_str(row["source_table"]),
            "onglet_source":      _to_pg_str(row["lot_id"]),
            "date_chargement":    now,
        }
        for _, row in df.iterrows()
    ]
    
    engine = get_engine()
    stmt = text(UPSERT_INDIC_SQL)
    total = 0
    
    with engine.begin() as conn:
        for i in range(0, len(records), BATCH_SIZE):
            batch = records[i:i + BATCH_SIZE]
            conn.execute(stmt, batch)
            total += len(batch)
            logger.debug(f"   Batch {i // BATCH_SIZE + 1} : {len(batch)} lignes")
    
    logger.info(f"✅ {total} lignes UPSERT dans dwh.fait_indicateurs_performance_dp")
    return {"inserted_or_updated": total}


# ═══════════════════════════════════════════════════════════════
# UPSERT RÉCLAMATIONS
# ═══════════════════════════════════════════════════════════════

UPSERT_RECLAM_SQL = """
INSERT INTO dwh.fait_reclamation
    (id_temps, id_dp, id_centre, id_type,
     nb_reclamations, temps_moyen_coupure, delai_moyen_traitement, valeur_brute,
     source_saisie, fichier_source, onglet_source, date_chargement)
VALUES
    (:id_temps, :id_dp, :id_centre, :id_type,
     :nb_reclamations, :temps_moyen_coupure, :delai_moyen_traitement, :valeur_brute,
     :source_saisie, :fichier_source, :onglet_source, :date_chargement)
ON CONFLICT (id_temps, id_dp, id_centre, id_type, source_saisie)
DO UPDATE SET
    nb_reclamations         = EXCLUDED.nb_reclamations,
    temps_moyen_coupure     = EXCLUDED.temps_moyen_coupure,
    delai_moyen_traitement  = EXCLUDED.delai_moyen_traitement,
    valeur_brute            = EXCLUDED.valeur_brute,
    fichier_source          = EXCLUDED.fichier_source,
    onglet_source           = EXCLUDED.onglet_source,
    date_chargement         = EXCLUDED.date_chargement;
"""


def load_reclamations(df: pd.DataFrame) -> dict:
    """Charge les réclamations Streamlit dans le DWH (UPSERT)."""
    if df.empty:
        logger.warning("⚠️  Aucune réclamation à charger")
        return {"inserted_or_updated": 0}
    
    now = datetime.now()
    
    records = [
        {
            "id_temps":                _to_pg_int(row["id_temps"]),
            "id_dp":                   _to_pg_int(row["id_dp"]),
            "id_centre":               _to_pg_int(row["id_centre"]),
            "id_type":                 _to_pg_int(row["id_type"]),
            "nb_reclamations":         _to_pg_int(row["nb_reclamations_num"]),
            "temps_moyen_coupure":     _to_pg_float(row["temps_moyen_coupure_num"]),
            "delai_moyen_traitement":  _to_pg_float(row["delai_moyen_traitement_num"]),
            "valeur_brute":            _to_pg_float(row["valeur_brute_num"]),
            "source_saisie":           SOURCE_SAISIE,
            "fichier_source":          _to_pg_str(row["source_table"]),
            "onglet_source":           _to_pg_str(row["lot_id"]),
            "date_chargement":         now,
        }
        for _, row in df.iterrows()
    ]
    
    engine = get_engine()
    stmt = text(UPSERT_RECLAM_SQL)
    total = 0
    
    with engine.begin() as conn:
        for i in range(0, len(records), BATCH_SIZE):
            batch = records[i:i + BATCH_SIZE]
            conn.execute(stmt, batch)
            total += len(batch)
            logger.debug(f"   Batch {i // BATCH_SIZE + 1} : {len(batch)} lignes")
    
    logger.info(f"✅ {total} lignes UPSERT dans dwh.fait_reclamation")
    return {"inserted_or_updated": total}


# ═══════════════════════════════════════════════════════════════
# POINT D'ENTRÉE PRINCIPAL
# ═══════════════════════════════════════════════════════════════

def run_load() -> dict:
    """Exécute le chargement Gold pour la source Streamlit."""
    logger.info("=" * 70)
    logger.info("🥇 GOLD - CHARGEMENT DWH STREAMLIT INDICATEURS & RÉCLAMATIONS")
    logger.info(f"   source_saisie = '{SOURCE_SAISIE}'")
    logger.info("=" * 70)
    
    result = {"status": "success"}
    
    # ─── INDICATEURS ───
    try:
        path = get_latest_parquet("silver", SOURCE_NAME, "indicateurs")
        df_silver = read_parquet(path)
        
        df_valid, df_rej = _resolve_sk_indicateurs(df_silver)
        
        if not df_rej.empty:
            save_parquet(df_rej, "rejects", SOURCE_NAME, "indicateurs_rejets_sk")
        
        stats = load_indicateurs(df_valid)
        result["indicateurs"] = {
            "silver_total":    len(df_silver),
            "valides":         len(df_valid),
            "rejets_sk":       len(df_rej),
            **stats,
        }
    except FileNotFoundError as e:
        logger.error(f"❌ Indicateurs : {e}")
        result["status"] = "partial"
    
    logger.info("-" * 70)
    
    # ─── RÉCLAMATIONS ───
    try:
        path = get_latest_parquet("silver", SOURCE_NAME, "reclamations")
        df_silver = read_parquet(path)
        
        df_valid, df_rej = _resolve_sk_reclamations(df_silver)
        
        if not df_rej.empty:
            save_parquet(df_rej, "rejects", SOURCE_NAME, "reclamations_rejets_sk")
        
        stats = load_reclamations(df_valid)
        result["reclamations"] = {
            "silver_total":    len(df_silver),
            "valides":         len(df_valid),
            "rejets_sk":       len(df_rej),
            **stats,
        }
    except FileNotFoundError as e:
        logger.error(f"❌ Réclamations : {e}")
        result["status"] = "partial"
    
    logger.info("=" * 70)
    logger.info("✅ CHARGEMENT TERMINÉ")
    logger.info("=" * 70)
    
    return result


if __name__ == "__main__":
    result = run_load()
    print("\n📋 Résultat :")
    import json
    print(json.dumps(result, indent=2, default=str))