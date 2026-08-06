"""
ETL - Rendements Étage
Étape : TRANSFORM (Silver)

- Parser les mois (FR + EN + variantes) → id_temps
- Normaliser noms d'étage → code_etage
- Fusionner histo_rendement + vol_amene par (etage, mois)
  → Priorité : Vol_amene depuis "Volume Amené par étage.xlsx" (plus complet/récent)
  → Fallback : Vol_amene depuis "etages_rendements_Histo PBI.xlsx" (si colonne présente)
- Calculer volume_pertes, ilp
"""
import re
import unicodedata
from datetime import datetime
import pandas as pd
import numpy as np

from etl.common.config import load_mapping
from etl.common.logger import get_logger
from etl.common.io_utils import save_parquet, get_latest_parquet, read_parquet

logger = get_logger(__name__)

SOURCE_NAME = "rendements"


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _normalize_etage(nom: str, mapping: dict) -> str:
    """Retourne code_etage DWH depuis un nom Excel."""
    if not nom or pd.isna(nom):
        return None
    key = str(nom).upper().strip()
    key = " ".join(key.split())
    return mapping.get(key)


def _parse_mois_universal(mois_str: str, mapping_fr: dict, mapping_en: dict) -> tuple:
    """
    Parser universel :
    - 'juin-21', 'juil.-21', 'déc.-21', 'janv.-22' (FR)
    - 'Jan-22', 'Feb-22', 'Dec-25' (EN)
    - datetime déjà converti en 'Jan-22' par extract
    """
    if not mois_str or pd.isna(mois_str):
        return None, None
    
    s = str(mois_str).strip().lower()
    if s == "nan" or s == "none":
        return None, None
    
    s = s.replace(".", "")
    
    # Format attendu : "juin-21" ou "jan-22"
    m = re.match(r'^([a-zéûàêô]+)[-\s]+(\d{2,4})$', s)
    if not m:
        return None, None
    
    mois_txt, annee_txt = m.group(1), m.group(2)
    
    # Essayer FR d'abord, puis EN
    mois_num = mapping_fr.get(mois_txt) or mapping_en.get(mois_txt)
    if not mois_num:
        return None, None
    
    annee = int(annee_txt)
    if annee < 100:
        annee += 2000
    
    return annee, mois_num


def _year_month_to_id_temps(annee, mois) -> int:
    """(2025, 3) → 20250301"""
    if annee is None or mois is None or pd.isna(annee) or pd.isna(mois):
        return None
    return int(f"{int(annee):04d}{int(mois):02d}01")


def _parse_float(v) -> float:
    """Convertit une valeur en float, NaN si invalide."""
    if pd.isna(v):
        return np.nan
    if isinstance(v, str):
        s = v.strip().replace(" ", "").replace("\xa0", "").replace(",", ".")
        if not s or s.lower() in ("nan", "none", "-"):
            return np.nan
        try:
            return float(s)
        except (ValueError, TypeError):
            return np.nan
    try:
        return float(v)
    except (ValueError, TypeError):
        return np.nan


# ═══════════════════════════════════════════════════════════════
# TRANSFORM HISTO
# ═══════════════════════════════════════════════════════════════

def transform_histo(df_bronze: pd.DataFrame, cfg: dict) -> tuple:
    """Transforme le Bronze histo → Silver format long propre."""
    logger.info("🔄 Transform histo_rendement...")
    
    mapping_etages = cfg["etages_normalisation"]
    mapping_fr     = cfg["mois_fr"]
    mapping_en     = cfg["mois_en"]
    
    df = df_bronze.copy()
    
    df["code_etage"] = df["nom_etage_source"].apply(
        lambda x: _normalize_etage(x, mapping_etages)
    )
    
    df[["annee", "mois"]] = df["mois_source"].apply(
        lambda x: pd.Series(_parse_mois_universal(x, mapping_fr, mapping_en))
    )
    df["id_temps"] = df.apply(
        lambda r: _year_month_to_id_temps(r["annee"], r["mois"]), axis=1
    )
    
    # Parser valeurs
    df["nb_clients"]        = df["nb_clients_source"].apply(_parse_float)
    df["volume_facture"]    = df["vol_facture_source"].apply(_parse_float)
    df["rendement"]         = df["rendement_source"].apply(_parse_float)
    df["volume_amene_histo"] = df["vol_amene_source"].apply(_parse_float)
    
    # Rejets
    df["motif_rejet"] = None
    df.loc[df["code_etage"].isna(), "motif_rejet"] = "etage_inconnu"
    df.loc[df["id_temps"].isna(),   "motif_rejet"] = "mois_invalide"
    rend_max = cfg["regles"]["rendement_max_valide"]
    df.loc[df["rendement"] > rend_max, "motif_rejet"] = f"rendement_aberrant_gt_{rend_max}"
    
    df_rejets  = df[df["motif_rejet"].notna()].copy()
    df_valides = df[df["motif_rejet"].isna()].copy()
    
    logger.info(f"   ✅ {len(df_valides)} valides | ❌ {len(df_rejets)} rejets")
    if not df_rejets.empty:
        for motif, cnt in df_rejets["motif_rejet"].value_counts().items():
            logger.warning(f"      • {motif} : {cnt}")
        etages_ko = df_rejets[df_rejets["motif_rejet"] == "etage_inconnu"]["nom_etage_source"].unique()
        if len(etages_ko) > 0:
            logger.warning(f"      Étages inconnus : {list(etages_ko)[:10]}")
    
    # Silver
    df_silver = df_valides[[
        "id_temps", "code_etage", "annee", "mois",
        "nb_clients", "volume_facture", "rendement", "volume_amene_histo",
        "fichier_source", "onglet_source", "date_extraction",
    ]].copy()
    
    # Déduplication (garder dernier)
    df_silver = df_silver.drop_duplicates(
        subset=["id_temps", "code_etage"], keep="last"
    ).reset_index(drop=True)
    
    df_silver["id_temps"] = df_silver["id_temps"].astype("int64")
    
    return df_silver, df_rejets


# ═══════════════════════════════════════════════════════════════
# TRANSFORM VOL AMENE
# ═══════════════════════════════════════════════════════════════

def transform_vol_amene(df_bronze: pd.DataFrame, cfg: dict) -> tuple:
    """Transforme le Bronze vol_amene → Silver format long propre."""
    logger.info("🔄 Transform vol_amene...")
    
    mapping_etages = cfg["etages_normalisation"]
    mapping_fr     = cfg["mois_fr"]
    mapping_en     = cfg["mois_en"]
    
    df = df_bronze.copy()
    
    df["code_etage"] = df["nom_etage_source"].apply(
        lambda x: _normalize_etage(x, mapping_etages)
    )
    
    df[["annee", "mois"]] = df["mois_source"].apply(
        lambda x: pd.Series(_parse_mois_universal(x, mapping_fr, mapping_en))
    )
    df["id_temps"] = df.apply(
        lambda r: _year_month_to_id_temps(r["annee"], r["mois"]), axis=1
    )
    
    df["volume_amene"] = df["vol_amene_source"].apply(_parse_float)
    
    df["motif_rejet"] = None
    df.loc[df["code_etage"].isna(), "motif_rejet"] = "etage_inconnu"
    df.loc[df["id_temps"].isna(),   "motif_rejet"] = "mois_invalide"
    
    df_rejets  = df[df["motif_rejet"].notna()].copy()
    df_valides = df[df["motif_rejet"].isna() & df["volume_amene"].notna()].copy()
    
    logger.info(f"   ✅ {len(df_valides)} valides | ❌ {len(df_rejets)} rejets")
    if not df_rejets.empty:
        for motif, cnt in df_rejets["motif_rejet"].value_counts().items():
            logger.warning(f"      • {motif} : {cnt}")
        etages_ko = df_rejets[df_rejets["motif_rejet"] == "etage_inconnu"]["nom_etage_source"].unique()
        if len(etages_ko) > 0:
            logger.warning(f"      Étages inconnus : {list(etages_ko)[:10]}")
    
    df_silver = df_valides[[
        "id_temps", "code_etage", "annee", "mois", "volume_amene",
        "fichier_source", "onglet_source", "date_extraction",
    ]].copy()
    
    df_silver = df_silver.drop_duplicates(
        subset=["id_temps", "code_etage"], keep="last"
    ).reset_index(drop=True)
    
    df_silver["id_temps"] = df_silver["id_temps"].astype("int64")
    
    return df_silver, df_rejets


# ═══════════════════════════════════════════════════════════════
# MERGE & ENRICH
# ═══════════════════════════════════════════════════════════════

def merge_and_enrich(
    df_histo: pd.DataFrame, 
    df_vol: pd.DataFrame,
    df_lineaires: pd.DataFrame,
    cfg: dict,
) -> pd.DataFrame:
    """
    Fusionne histo + vol_amene par (id_temps, code_etage) [FULL OUTER].
    
    Priorité pour volume_amene :
    1. Vol_amene du fichier dédié (plus fiable/récent)
    2. Vol_amene_histo (si colonne présente dans fichier histo)
    """
    logger.info("🔗 Fusion histo + vol_amene...")
    
    # FULL OUTER JOIN
    df = pd.merge(
        df_histo[["id_temps", "code_etage", "annee", "mois",
                  "nb_clients", "volume_facture", "rendement", "volume_amene_histo"]],
        df_vol[["id_temps", "code_etage", "volume_amene"]].rename(
            columns={"volume_amene": "volume_amene_dedie"}
        ),
        on=["id_temps", "code_etage"],
        how="outer",
    )
    
    logger.info(f"   Résultat fusion : {len(df)} lignes")
    
    # Reconstituer annee/mois si NULL (venait uniquement de vol_amene)
    if df["annee"].isna().any():
        mask_null = df["annee"].isna() & df["id_temps"].notna()
        df.loc[mask_null, "annee"] = df.loc[mask_null, "id_temps"].astype(str).str[:4].astype(int)
        df.loc[mask_null, "mois"]  = df.loc[mask_null, "id_temps"].astype(str).str[4:6].astype(int)
    
    # Prioriser vol_amene dédié sur vol_amene_histo
    df["volume_amene"] = df["volume_amene_dedie"].fillna(df["volume_amene_histo"])
    
    # Enrichir avec linéaire
    df = df.merge(df_lineaires, on="code_etage", how="left")
    
    # Calculs
    df["volume_pertes"] = df["volume_amene"] - df["volume_facture"]
    
    nb_jours = cfg["regles"]["nb_jours_mois_default"]
    df["ilp"] = np.where(
        (df["lineaire_km"] > 0) & df["volume_pertes"].notna() & (df["volume_pertes"] > 0),
        df["volume_pertes"] / df["lineaire_km"] / nb_jours,
        np.nan,
    )
    
    # Source des données
    df["source_donnees"] = "inconnue"
    df.loc[df["nb_clients"].notna() & df["volume_amene"].notna(), "source_donnees"] = "histo+vol_amene"
    df.loc[df["nb_clients"].notna() & df["volume_amene"].isna(),  "source_donnees"] = "histo_seul"
    df.loc[df["nb_clients"].isna()  & df["volume_amene"].notna(), "source_donnees"] = "vol_amene_seul"
    
    # Stats
    logger.info(f"   📊 Répartition des sources :")
    for src, cnt in df["source_donnees"].value_counts().items():
        logger.info(f"      • {src:20s} : {cnt}")
    
    logger.info(f"   💧 Volumes disponibles :")
    logger.info(f"      • volume_amene     : {df['volume_amene'].notna().sum()}")
    logger.info(f"      • volume_facture   : {df['volume_facture'].notna().sum()}")
    logger.info(f"      • volume_pertes    : {df['volume_pertes'].notna().sum()}")
    logger.info(f"      • ilp calculé      : {df['ilp'].notna().sum()}")
    logger.info(f"      • rendement        : {df['rendement'].notna().sum()}")
    
    # Nettoyer colonnes intermédiaires
    df = df.drop(columns=["volume_amene_histo", "volume_amene_dedie"], errors="ignore")
    
    return df


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def run_transform() -> dict:
    logger.info("=" * 70)
    logger.info("🥈 SILVER - TRANSFORMATION RENDEMENTS")
    logger.info("=" * 70)
    
    cfg = load_mapping(SOURCE_NAME, "rendements_config")
    result = {"status": "success"}
    
    try:
        # 1. Bronze
        df_bronze_histo = read_parquet(get_latest_parquet("bronze", SOURCE_NAME, "histo_rendement"))
        df_bronze_vol   = read_parquet(get_latest_parquet("bronze", SOURCE_NAME, "vol_amene"))
        
        # 2. Linéaires DWH
        from etl.common.db import read_sql
        df_lineaires = read_sql("""
            SELECT code_etage, lineaire_km
            FROM dwh.dim_etage
            WHERE id_etage > 0
        """)
        
        # 3. Transformer
        df_histo_sv, df_rej_h = transform_histo(df_bronze_histo, cfg)
        df_vol_sv,   df_rej_v = transform_vol_amene(df_bronze_vol, cfg)
        
        # 4. Fusion
        df_silver = merge_and_enrich(df_histo_sv, df_vol_sv, df_lineaires, cfg)
        
        # 5. Sauvegardes
        logger.info("-" * 70)
        logger.info(f"📊 Silver final : {len(df_silver)} lignes")
        
        if not df_silver.empty:
            p = save_parquet(df_silver, "silver", SOURCE_NAME, "rendements")
            result["silver_parquet"] = str(p)
            result["nb_silver"] = len(df_silver)
        
        rejets = [r for r in [df_rej_h, df_rej_v] if not r.empty]
        if rejets:
            df_rej = pd.concat(rejets, ignore_index=True)
            p = save_parquet(df_rej, "rejects", SOURCE_NAME, "rendements_rejets")
            result["rejects_parquet"] = str(p)
            result["nb_rejets"] = len(df_rej)
        
    except Exception as e:
        logger.error(f"❌ Erreur : {e}", exc_info=True)
        result["status"] = "error"
        result["error"] = str(e)
    
    logger.info("=" * 70)
    logger.info("✅ TRANSFORMATION TERMINÉE")
    logger.info("=" * 70)
    return result


if __name__ == "__main__":
    result = run_transform()
    import json
    print(json.dumps(result, indent=2, default=str))