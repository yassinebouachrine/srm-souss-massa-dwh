"""
ETL - Streamlit Indicateurs & Réclamations
Étape : TRANSFORM (Silver)

Rôle :
- Lire les Parquet bronze (déjà en format long)
- Convertir (annee, mois) → id_temps
- Mapper id_province → code_dp
- Mapper id_centre → code_centre (via jointure staging/dwh)
- Marquer les réclamations personnalisées pour traitement spécial au Load
- Filtrer les lignes invalides (→ data/rejects/)
- Sauvegarder en Parquet dans data/silver/streamlit_indicateurs_reclamations/
"""
import pandas as pd
import numpy as np

from etl.common.config import CONFIG
from etl.common.logger import get_logger
from etl.common.io_utils import save_parquet, get_latest_parquet, read_parquet
from etl.common.dim_resolver import (
    PROVINCE_TO_DP,
    get_staging_centre_to_dwh_centre_mapping,
    year_month_to_id_temps,
    clear_cache,
)

logger = get_logger(__name__)

SOURCE_NAME = "streamlit_indicateurs_reclamations"


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _to_float(v):
    """Convertit une valeur en float, NaN si invalide."""
    if pd.isna(v):
        return np.nan
    try:
        return float(v)
    except (ValueError, TypeError):
        return np.nan


def _to_int(v):
    """Convertit une valeur en int nullable."""
    if pd.isna(v):
        return None
    try:
        return int(v)
    except (ValueError, TypeError):
        return None


# ═══════════════════════════════════════════════════════════════
# TRANSFORMATION INDICATEURS
# ═══════════════════════════════════════════════════════════════

def transform_indicateurs(df_bronze: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Transforme le Bronze des indicateurs Streamlit en Silver.
    
    Returns:
        (df_silver, df_rejects)
    """
    logger.info("🔄 Transformation Indicateurs...")
    logger.info(f"   → Bronze : {len(df_bronze)} lignes")
    
    clear_cache()
    map_centre = get_staging_centre_to_dwh_centre_mapping()
    
    df = df_bronze.copy()
    
    # 1. Convertir (annee, mois) → id_temps
    df["id_temps"] = df.apply(
        lambda r: year_month_to_id_temps(int(r["annee"]), int(r["mois"]))
        if pd.notna(r["annee"]) and pd.notna(r["mois"]) else None,
        axis=1,
    )
    
    # 2. Mapper id_province → code_dp
    df["code_dp"] = df["id_province"].map(PROVINCE_TO_DP)
    
    # 3. Mapper id_centre → code_centre (peut être NULL si Recap DP)
    df["code_centre"] = df["id_centre"].map(map_centre)
    # Détecter si c'est un Recap DP (pas de centre saisi dans Streamlit)
    df["est_recap_dp"] = df["id_centre"].isna()
    
    # 4. Convertir la valeur en float propre
    df["valeur"] = df["valeur_indicateur"].apply(_to_float)
    
    # 5. Détecter les rejets
    df["motif_rejet"] = None
    df.loc[df["id_temps"].isna(),        "motif_rejet"] = "periode_invalide"
    df.loc[df["code_dp"].isna(),         "motif_rejet"] = "province_inconnue"
    df.loc[df["code_indicateur"].isna(), "motif_rejet"] = "code_indicateur_manquant"
    # code_centre peut être NULL (Recap DP) : rejet uniquement si id_centre non NULL mais introuvable
    df.loc[
        (df["id_centre"].notna()) & (df["code_centre"].isna()),
        "motif_rejet"
    ] = "centre_introuvable"
    
    df_rejects = df[df["motif_rejet"].notna()].copy()
    df_valid   = df[df["motif_rejet"].isna()].copy()
    
    # 6. Filtrer valeurs NULL (rien à charger)
    df_null = df_valid[df_valid["valeur"].isna()].copy()
    df_valid = df_valid[df_valid["valeur"].notna()].copy()
    
    logger.info(f"   ✅ Valides      : {len(df_valid)} lignes")
    logger.info(f"   ⭕ Valeurs NULL : {len(df_null)} lignes (ignorées)")
    logger.info(f"   ❌ Rejetées     : {len(df_rejects)} lignes")
    
    if not df_rejects.empty:
        logger.info(f"   📋 Motifs de rejet :")
        for motif, count in df_rejects["motif_rejet"].value_counts().items():
            logger.info(f"      • {motif} : {count}")
    
    # 7. Colonnes finales
    final_cols = [
        "id_temps", "code_dp", "code_centre", "code_indicateur", "valeur",
        "est_recap_dp",
        # Traçabilité Streamlit
        "id_staging", "lot_id", "libelle_indicateur",
        "soumis_par", "date_soumission",
        "valide_par_regional", "date_validation_reg",
        "source_table", "date_extraction",
    ]
    df_silver = df_valid[final_cols].reset_index(drop=True)
    df_silver["id_temps"] = df_silver["id_temps"].astype("int64")
    
    return df_silver, df_rejects


# ═══════════════════════════════════════════════════════════════
# TRANSFORMATION RÉCLAMATIONS
# ═══════════════════════════════════════════════════════════════

def transform_reclamations(df_bronze: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Transforme le Bronze des réclamations Streamlit en Silver.
    
    Particularité : les 3 colonnes de valeur (nombre_reclamations, temps_moyen_coupure_h,
    delai_moyen_traitement_j) sont déjà correctement ventilées dans Streamlit,
    on n'a rien à ventiler contrairement à l'Excel.
    """
    logger.info("🔄 Transformation Réclamations...")
    logger.info(f"   → Bronze : {len(df_bronze)} lignes")
    
    clear_cache()
    map_centre = get_staging_centre_to_dwh_centre_mapping()
    
    df = df_bronze.copy()
    
    # 1. Convertir (annee, mois) → id_temps
    df["id_temps"] = df.apply(
        lambda r: year_month_to_id_temps(int(r["annee"]), int(r["mois"]))
        if pd.notna(r["annee"]) and pd.notna(r["mois"]) else None,
        axis=1,
    )
    
    # 2. Mapper id_province → code_dp
    df["code_dp"] = df["id_province"].map(PROVINCE_TO_DP)
    
    # 3. Mapper id_centre → code_centre
    df["code_centre"] = df["id_centre"].map(map_centre)
    df["est_recap_dp"] = df["id_centre"].isna()
    
    # 4. Nettoyer les valeurs
    df["nb_reclamations_num"]       = df["nombre_reclamations"].apply(_to_float)
    df["temps_moyen_coupure_num"]   = df["temps_moyen_coupure_h"].apply(_to_float)
    df["delai_moyen_traitement_num"] = df["delai_moyen_traitement_j"].apply(_to_float)
    df["valeur_brute_num"]          = df["valeur_brute"].apply(_to_float)
    
    # 5. Rejets
    df["motif_rejet"] = None
    df.loc[df["id_temps"].isna(),    "motif_rejet"] = "periode_invalide"
    df.loc[df["code_dp"].isna(),     "motif_rejet"] = "province_inconnue"
    df.loc[df["code_type"].isna(),   "motif_rejet"] = "code_type_manquant"
    df.loc[df["libelle_reclamation"].isna(), "motif_rejet"] = "libelle_manquant"
    df.loc[
        (df["id_centre"].notna()) & (df["code_centre"].isna()),
        "motif_rejet"
    ] = "centre_introuvable"
    
    # Rejet si toutes les valeurs sont NULL (rien à charger)
    all_null = (
        df["nb_reclamations_num"].isna()
        & df["temps_moyen_coupure_num"].isna()
        & df["delai_moyen_traitement_num"].isna()
    )
    df.loc[all_null & df["motif_rejet"].isna(), "motif_rejet"] = "toutes_valeurs_null"
    
    df_rejects = df[df["motif_rejet"].notna()].copy()
    df_valid   = df[df["motif_rejet"].isna()].copy()
    
    logger.info(f"   ✅ Valides      : {len(df_valid)} lignes")
    logger.info(f"   ❌ Rejetées     : {len(df_rejects)} lignes")
    
    if not df_rejects.empty:
        logger.info(f"   📋 Motifs :")
        for motif, count in df_rejects["motif_rejet"].value_counts().items():
            logger.info(f"      • {motif} : {count}")
    
    nb_std    = (~df_valid["est_personnalisee_source"]).sum()
    nb_custom = df_valid["est_personnalisee_source"].sum()
    logger.info(f"   📊 Standards : {nb_std} | Personnalisées : {nb_custom}")
    
    # 6. Colonnes finales
    final_cols = [
        "id_temps", "code_dp", "code_centre",
        "code_type", "libelle_reclamation", "categorie_reclamation",
        "est_personnalisee_source",     # important pour le Load (get_or_create)
        "nb_reclamations_num", "temps_moyen_coupure_num",
        "delai_moyen_traitement_num", "valeur_brute_num",
        "est_recap_dp",
        # Traçabilité Streamlit
        "id_staging", "lot_id",
        "soumis_par", "date_soumission",
        "valide_par_regional", "date_validation_reg",
        "source_table", "date_extraction",
    ]
    df_silver = df_valid[final_cols].reset_index(drop=True)
    df_silver["id_temps"] = df_silver["id_temps"].astype("int64")
    
    return df_silver, df_rejects


# ═══════════════════════════════════════════════════════════════
# POINT D'ENTRÉE PRINCIPAL
# ═══════════════════════════════════════════════════════════════

def run_transform() -> dict:
    """Exécute la transformation Silver."""
    logger.info("=" * 70)
    logger.info("🥈 SILVER - TRANSFORMATION STREAMLIT INDICATEURS & RÉCLAMATIONS")
    logger.info("=" * 70)
    
    result = {"status": "success"}
    
    # ─── INDICATEURS ───
    try:
        path = get_latest_parquet("bronze", SOURCE_NAME, "indicateurs")
        df_bronze = read_parquet(path)
        df_silver, df_rej = transform_indicateurs(df_bronze)
        
        if not df_silver.empty:
            p = save_parquet(df_silver, "silver", SOURCE_NAME, "indicateurs")
            result["silver_indicateurs"] = str(p)
            result["nb_lignes_indicateurs"] = len(df_silver)
        
        if not df_rej.empty:
            p = save_parquet(df_rej, "rejects", SOURCE_NAME, "indicateurs_rejets")
            result["rejects_indicateurs"] = str(p)
            result["nb_rejets_indicateurs"] = len(df_rej)
    except FileNotFoundError as e:
        logger.error(f"❌ Indicateurs : {e}")
        result["status"] = "partial"
    
    logger.info("-" * 70)
    
    # ─── RÉCLAMATIONS ───
    try:
        path = get_latest_parquet("bronze", SOURCE_NAME, "reclamations")
        df_bronze = read_parquet(path)
        df_silver, df_rej = transform_reclamations(df_bronze)
        
        if not df_silver.empty:
            p = save_parquet(df_silver, "silver", SOURCE_NAME, "reclamations")
            result["silver_reclamations"] = str(p)
            result["nb_lignes_reclamations"] = len(df_silver)
        
        if not df_rej.empty:
            p = save_parquet(df_rej, "rejects", SOURCE_NAME, "reclamations_rejets")
            result["rejects_reclamations"] = str(p)
            result["nb_rejets_reclamations"] = len(df_rej)
    except FileNotFoundError as e:
        logger.error(f"❌ Réclamations : {e}")
        result["status"] = "partial"
    
    logger.info("=" * 70)
    logger.info("✅ TRANSFORMATION TERMINÉE")
    logger.info("=" * 70)
    
    return result


if __name__ == "__main__":
    result = run_transform()
    print("\n📋 Résultat :")
    for k, v in result.items():
        print(f"   • {k}: {v}")