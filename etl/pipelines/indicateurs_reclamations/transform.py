"""
ETL - Indicateurs & Réclamations
Étape : TRANSFORM (Silver)

Rôle :
- Lire les Parquet bronze (format wide)
- Unpivot : passer en format long (une ligne = 1 période × 1 libellé)
- Parser les périodes (jan_25 → id_temps=20250101)
- Nettoyer les valeurs (#DIV/0!, "-", "" → NULL)
- Mapper libellés → codes (indicateurs, réclamations, centres)
- Filtrer les lignes invalides (→ data/rejects/)
- Sauvegarder en Parquet dans data/silver/indicateurs_reclamations/
"""
from datetime import datetime
from pathlib import Path
import unicodedata
import pandas as pd
import numpy as np

from etl.common.config import CONFIG, load_mapping
from etl.common.logger import get_logger
from etl.common.io_utils import save_parquet, get_latest_parquet, read_parquet

logger = get_logger(__name__)

SOURCE_NAME = "indicateurs_reclamations"

# Valeurs à traiter comme NULL
NULL_VALUES = {"", "-", "nan", "none", "null", "#div/0!", "#n/a", "#value!", "#ref!", "#name?"}

# Correspondance mois abrégé → numéro
MOIS_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _normalize_libelle(text: str) -> str:
    """Normalise un libellé pour un matching robuste (lowercase, sans accents, espaces réduits)."""
    if not text or pd.isna(text):
        return ""
    t = unicodedata.normalize("NFD", str(text))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = t.lower().strip()
    t = " ".join(t.split())  # espaces multiples → 1 espace
    return t


def _parse_periode_to_id_temps(col_name: str) -> int | None:
    """
    Convertit un nom de colonne 'jan_25', 'feb_26' en id_temps du 1er du mois.
    Ex: 'jan_25' → 20250101
        'dec_26' → 20261201
    Retourne None si la colonne n'est pas une période valide.
    """
    if not col_name or "_" not in col_name:
        return None
    parts = col_name.split("_")
    if len(parts) != 2:
        return None
    mois_str, annee_str = parts
    if mois_str not in MOIS_MAP or not annee_str.isdigit():
        return None
    mois = MOIS_MAP[mois_str]
    annee = 2000 + int(annee_str)  # jan_25 → 2025
    return int(f"{annee:04d}{mois:02d}01")


def _parse_valeur(v) -> float | None:
    """
    Convertit une valeur brute en float, ou None si invalide.
    - "#DIV/0!", "-", "" → None
    - "77.75", "77,75", "  12  " → 77.75, 77.75, 12.0
    """
    if v is None or pd.isna(v):
        return None
    s = str(v).strip().lower()
    if s in NULL_VALUES:
        return None
    # Remplacer virgule décimale par point
    s = s.replace(",", ".")
    # Retirer espaces internes (séparateurs de milliers)
    s = s.replace(" ", "").replace("\xa0", "")
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _build_libelle_index(mapping_dict: dict) -> dict:
    """
    Construit un index normalisé pour matcher les libellés.
    Ex: {"Rendement (%)": "REND"} → {"rendement (%)": ("Rendement (%)", "REND")}
    """
    return {
        _normalize_libelle(k): (k, v)
        for k, v in mapping_dict.items()
    }


# ═══════════════════════════════════════════════════════════════
# UNPIVOT
# ═══════════════════════════════════════════════════════════════

def _unpivot_bronze(df_bronze: pd.DataFrame) -> pd.DataFrame:
    """
    Passe le DataFrame Bronze du format wide au format long.
    
    Bronze  : libelle_source | jan_25 | feb_25 | ... | metadata...
    Silver  : libelle_source | periode_col | valeur_brute | metadata...
    """
    # Identifier les colonnes de périodes (jan_25, feb_25, ...)
    periode_cols = [c for c in df_bronze.columns if _parse_periode_to_id_temps(c) is not None]
    
    # Colonnes à garder (tout sauf les périodes)
    id_cols = [c for c in df_bronze.columns if c not in periode_cols]
    
    # Melt (unpivot)
    df_long = df_bronze.melt(
        id_vars=id_cols,
        value_vars=periode_cols,
        var_name="periode_col",
        value_name="valeur_brute",
    )
    return df_long


# ═══════════════════════════════════════════════════════════════
# TRANSFORMATION INDICATEURS
# ═══════════════════════════════════════════════════════════════

def transform_indicateurs(df_bronze: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Transforme le Bronze des indicateurs en Silver.
    
    Returns:
        (df_silver, df_rejects)
    """
    logger.info("🔄 Transformation Indicateurs...")
    logger.info(f"   → Bronze : {len(df_bronze)} lignes")
    
    # 1. Charger le mapping libellés → codes
    map_ind = load_mapping(SOURCE_NAME, "indicateurs")
    idx_indicateurs = _build_libelle_index(map_ind["libelles_vers_code"])
    
    # 2. Charger le mapping centres
    map_ctr = load_mapping(SOURCE_NAME, "centres")
    idx_centres = _build_libelle_index(map_ctr["onglets_vers_centre"])
    
    # 3. Unpivot
    df = _unpivot_bronze(df_bronze)
    logger.info(f"   → Après unpivot : {len(df)} lignes")
    
    # 4. Parser id_temps
    df["id_temps"] = df["periode_col"].apply(_parse_periode_to_id_temps)
    
    # 5. Résoudre code_indicateur
    df["_lib_norm"] = df["libelle_source"].apply(_normalize_libelle)
    df["code_indicateur"] = df["_lib_norm"].map(
        lambda x: idx_indicateurs.get(x, (None, None))[1]
    )
    
    # 6. Résoudre code_centre
    #    - Si est_recap_dp=True → code_centre = NULL (agrégation DP sans centre)
    #    - Sinon → chercher via l'onglet
    df["_ctr_norm"] = df["nom_centre_source"].apply(
        lambda x: _normalize_libelle(x) if pd.notna(x) else None
    )
    df["code_centre"] = df.apply(
        lambda row: None if row["est_recap_dp"]
        else idx_centres.get(row["_ctr_norm"], (None, None))[1],
        axis=1,
    )
    
    # 7. Parser la valeur
    df["valeur"] = df["valeur_brute"].apply(_parse_valeur)
    
    # 8. Renommer code_dp_source → code_dp
    df["code_dp"] = df["code_dp_source"]
    
    # 9. Séparation valides vs rejets
    #    Motifs de rejet :
    #    - id_temps NULL (colonne non parseable)
    #    - code_indicateur NULL (libellé inconnu)
    #    - code_dp NULL (fichier non reconnu)
    #    - code_centre NULL alors qu'on n'est pas en recap DP (onglet inconnu)
    df["motif_rejet"] = None
    df.loc[df["id_temps"].isna(),        "motif_rejet"] = "periode_invalide"
    df.loc[df["code_indicateur"].isna(), "motif_rejet"] = "libelle_indicateur_inconnu"
    df.loc[df["code_dp"].isna(),         "motif_rejet"] = "dp_non_reconnu"
    df.loc[
        (~df["est_recap_dp"]) & (df["code_centre"].isna()),
        "motif_rejet"
    ] = "centre_non_reconnu"
    
    df_rejects = df[df["motif_rejet"].notna()].copy()
    df_valid   = df[df["motif_rejet"].isna()].copy()
    
    # 10. Filtrer les lignes avec valeur NULL (pas d'erreur, juste rien à charger)
    df_null = df_valid[df_valid["valeur"].isna()].copy()
    df_valid = df_valid[df_valid["valeur"].notna()].copy()
    
    logger.info(f"   ✅ Valides       : {len(df_valid)} lignes")
    logger.info(f"   ⭕ Valeurs NULL  : {len(df_null)} lignes (ignorées, non chargées)")
    logger.info(f"   ❌ Rejetées      : {len(df_rejects)} lignes")
    
    if not df_rejects.empty:
        logger.info(f"   📋 Motifs de rejet :")
        for motif, count in df_rejects["motif_rejet"].value_counts().items():
            logger.info(f"      • {motif} : {count}")
    
    # 11. Colonnes finales
    final_cols = [
        "id_temps", "code_dp", "code_centre", "code_indicateur", "valeur",
        "libelle_source", "fichier_source", "onglet_source",
        "est_recap_dp", "date_extraction",
    ]
    df_silver = df_valid[final_cols].reset_index(drop=True)
    
    # 12. Types finaux
    df_silver["id_temps"]   = df_silver["id_temps"].astype("int64")
    df_silver["valeur"]     = df_silver["valeur"].astype("float64")
    
    return df_silver, df_rejects


# ═══════════════════════════════════════════════════════════════
# TRANSFORMATION RÉCLAMATIONS
# ═══════════════════════════════════════════════════════════════

def transform_reclamations(df_bronze: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Transforme le Bronze des réclamations en Silver.
    
    Particularité : selon le libellé, la valeur va dans une colonne différente :
      - nb_reclamations       (compteur)
      - temps_moyen_coupure   (heures)
      - delai_moyen_traitement (jours)
    """
    logger.info("🔄 Transformation Réclamations...")
    logger.info(f"   → Bronze : {len(df_bronze)} lignes")
    
    # 1. Charger les mappings
    map_rec = load_mapping(SOURCE_NAME, "reclamations")
    idx_reclams = {
        _normalize_libelle(k): (k, v["code"], v["target"])
        for k, v in map_rec["libelles_vers_code"].items()
    }
    
    map_ctr = load_mapping(SOURCE_NAME, "centres")
    idx_centres = _build_libelle_index(map_ctr["onglets_vers_centre"])
    
    # 2. Unpivot
    df = _unpivot_bronze(df_bronze)
    logger.info(f"   → Après unpivot : {len(df)} lignes")
    
    # 3. Parser id_temps
    df["id_temps"] = df["periode_col"].apply(_parse_periode_to_id_temps)
    
    # 4. Résoudre code + target
    df["_lib_norm"] = df["libelle_source"].apply(_normalize_libelle)
    df["code_reclamation"] = df["_lib_norm"].map(
        lambda x: idx_reclams.get(x, (None, None, None))[1]
    )
    df["target_col"] = df["_lib_norm"].map(
        lambda x: idx_reclams.get(x, (None, None, None))[2]
    )
    
    # 5. Résoudre code_centre
    df["_ctr_norm"] = df["nom_centre_source"].apply(
        lambda x: _normalize_libelle(x) if pd.notna(x) else None
    )
    df["code_centre"] = df.apply(
        lambda row: None if row["est_recap_dp"]
        else idx_centres.get(row["_ctr_norm"], (None, None))[1],
        axis=1,
    )
    
    # 6. Parser la valeur
    df["valeur"] = df["valeur_brute"].apply(_parse_valeur)
    
    # 7. Renommer code_dp
    df["code_dp"] = df["code_dp_source"]
    
    # 8. Rejets
    df["motif_rejet"] = None
    df.loc[df["id_temps"].isna(),          "motif_rejet"] = "periode_invalide"
    df.loc[df["code_reclamation"].isna(),  "motif_rejet"] = "libelle_reclamation_inconnu"
    df.loc[df["code_dp"].isna(),           "motif_rejet"] = "dp_non_reconnu"
    df.loc[
        (~df["est_recap_dp"]) & (df["code_centre"].isna()),
        "motif_rejet"
    ] = "centre_non_reconnu"
    
    df_rejects = df[df["motif_rejet"].notna()].copy()
    df_valid   = df[df["motif_rejet"].isna()].copy()
    
    # 9. Filtrer valeurs NULL
    df_null = df_valid[df_valid["valeur"].isna()].copy()
    df_valid = df_valid[df_valid["valeur"].notna()].copy()
    
    logger.info(f"   ✅ Valides       : {len(df_valid)} lignes")
    logger.info(f"   ⭕ Valeurs NULL  : {len(df_null)} lignes (ignorées)")
    logger.info(f"   ❌ Rejetées      : {len(df_rejects)} lignes")
    
    if not df_rejects.empty:
        logger.info(f"   📋 Motifs :")
        for motif, count in df_rejects["motif_rejet"].value_counts().items():
            logger.info(f"      • {motif} : {count}")
    
    # 10. Ventilation valeur → bonne colonne selon target
    df_valid["nb_reclamations"]        = np.where(
        df_valid["target_col"] == "nb_reclamations", df_valid["valeur"], np.nan
    )
    df_valid["temps_moyen_coupure"]    = np.where(
        df_valid["target_col"] == "temps_moyen_coupure", df_valid["valeur"], np.nan
    )
    df_valid["delai_moyen_traitement"] = np.where(
        df_valid["target_col"] == "delai_moyen_traitement", df_valid["valeur"], np.nan
    )
    df_valid["valeur_brute_num"] = df_valid["valeur"]  # copie pour Gold
    
    # 11. Colonnes finales
    final_cols = [
        "id_temps", "code_dp", "code_centre", "code_reclamation",
        "nb_reclamations", "temps_moyen_coupure", "delai_moyen_traitement",
        "valeur_brute_num",
        "libelle_source", "fichier_source", "onglet_source",
        "est_recap_dp", "date_extraction",
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
    logger.info("🥈 SILVER - TRANSFORMATION INDICATEURS & RÉCLAMATIONS")
    logger.info("=" * 70)
    
    result = {"status": "success"}
    
    # ─── INDICATEURS ───
    try:
        path_bronze_ind = get_latest_parquet("bronze", SOURCE_NAME, "indicateurs")
        df_bronze_ind = read_parquet(path_bronze_ind)
        df_silver_ind, df_rej_ind = transform_indicateurs(df_bronze_ind)
        
        if not df_silver_ind.empty:
            path = save_parquet(df_silver_ind, "silver", SOURCE_NAME, "indicateurs")
            result["silver_indicateurs"] = str(path)
            result["nb_lignes_indicateurs"] = len(df_silver_ind)
        
        if not df_rej_ind.empty:
            path = save_parquet(df_rej_ind, "rejects", SOURCE_NAME, "indicateurs_rejets")
            result["rejects_indicateurs"] = str(path)
            result["nb_rejets_indicateurs"] = len(df_rej_ind)
    except FileNotFoundError as e:
        logger.error(f"❌ Indicateurs : {e}")
        result["status"] = "partial"
    
    logger.info("-" * 70)
    
    # ─── RÉCLAMATIONS ───
    try:
        path_bronze_rec = get_latest_parquet("bronze", SOURCE_NAME, "reclamations")
        df_bronze_rec = read_parquet(path_bronze_rec)
        df_silver_rec, df_rej_rec = transform_reclamations(df_bronze_rec)
        
        if not df_silver_rec.empty:
            path = save_parquet(df_silver_rec, "silver", SOURCE_NAME, "reclamations")
            result["silver_reclamations"] = str(path)
            result["nb_lignes_reclamations"] = len(df_silver_rec)
        
        if not df_rej_rec.empty:
            path = save_parquet(df_rej_rec, "rejects", SOURCE_NAME, "reclamations_rejets")
            result["rejects_reclamations"] = str(path)
            result["nb_rejets_reclamations"] = len(df_rej_rec)
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