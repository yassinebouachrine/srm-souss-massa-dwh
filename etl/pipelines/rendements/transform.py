"""
ETL - Rendements Étage
Étape : TRANSFORM (Silver)

- Parser les mois (FR + EN) → id_temps
- Normaliser noms d'étage → code_etage
- Fusionner histo_rendement + vol_amene par (etage, mois)
- Calculer volume_pertes, ilp
- Filtrer rejets
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


def _parse_mois_fr(mois_str: str, mapping_fr: dict) -> tuple:
    """
    Parse 'juin-21', 'juil.-21', 'déc.-21', 'janv.-22' → (annee, mois).
    Retourne (None, None) si invalide.
    """
    if not mois_str or pd.isna(mois_str):
        return None, None
    
    s = str(mois_str).strip().lower()
    # Retirer les points : "juil." → "juil"
    s = s.replace(".", "")
    
    # Format attendu : "juin-21" ou "janv-22"
    m = re.match(r'^([a-zéûà]+)[-\s]+(\d{2,4})$', s)
    if not m:
        return None, None
    
    mois_txt, annee_txt = m.group(1), m.group(2)
    mois_num = mapping_fr.get(mois_txt)
    if not mois_num:
        return None, None
    
    annee = int(annee_txt)
    if annee < 100:
        annee += 2000
    
    return annee, mois_num


def _parse_mois_en(mois_str: str, mapping_en: dict) -> tuple:
    """
    Parse 'Jan-22', 'Feb-22', 'Dec-25' → (annee, mois).
    """
    if not mois_str or pd.isna(mois_str):
        return None, None
    
    s = str(mois_str).strip().lower()
    m = re.match(r'^([a-z]+)[-\s]+(\d{2,4})$', s)
    if not m:
        return None, None
    
    mois_txt, annee_txt = m.group(1), m.group(2)
    mois_num = mapping_en.get(mois_txt)
    if not mois_num:
        return None, None
    
    annee = int(annee_txt)
    if annee < 100:
        annee += 2000
    
    return annee, mois_num


def _year_month_to_id_temps(annee: int, mois: int) -> int:
    """(2025, 3) → 20250301"""
    if annee is None or mois is None:
        return None
    return int(f"{annee:04d}{mois:02d}01")


def _parse_float(v) -> float:
    """Convertit une valeur en float, NaN si invalide."""
    if pd.isna(v):
        return np.nan
    if isinstance(v, str):
        s = v.strip().replace(" ", "").replace("\xa0", "").replace(",", ".")
        if not s:
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
# TRANSFORM
# ═══════════════════════════════════════════════════════════════

def transform_histo(df_bronze: pd.DataFrame, cfg: dict) -> tuple:
    """Transforme le Bronze histo → Silver format long propre."""
    logger.info("🔄 Transform histo_rendement...")
    
    mapping_etages = cfg["etages_normalisation"]
    mapping_mois   = cfg["mois_fr"]
    
    df = df_bronze.copy()
    
    # Normaliser étage
    df["code_etage"] = df["nom_etage_source"].apply(
        lambda x: _normalize_etage(x, mapping_etages)
    )
    
    # Parser mois
    df[["annee", "mois"]] = df["mois_source"].apply(
        lambda x: pd.Series(_parse_mois_fr(x, mapping_mois))
    )
    df["id_temps"] = df.apply(
        lambda r: _year_month_to_id_temps(r["annee"], r["mois"]), axis=1
    )
    
    # Parser valeurs
    df["nb_clients"]     = df["nb_clients_source"].apply(_parse_float)
    df["volume_facture"] = df["vol_facture_source"].apply(_parse_float)
    df["rendement"]      = df["rendement_source"].apply(_parse_float)
    
    # Rejets
    df["motif_rejet"] = None
    df.loc[df["code_etage"].isna(), "motif_rejet"] = "etage_inconnu"
    df.loc[df["id_temps"].isna(),   "motif_rejet"] = "mois_invalide"
    # Rendement > seuil = aberrant
    rend_max = cfg["regles"]["rendement_max_valide"]
    df.loc[df["rendement"] > rend_max, "motif_rejet"] = f"rendement_aberrant_gt_{rend_max}"
    
    df_rejets  = df[df["motif_rejet"].notna()].copy()
    df_valides = df[df["motif_rejet"].isna()].copy()
    
    logger.info(f"   ✅ {len(df_valides)} valides | ❌ {len(df_rejets)} rejets")
    if not df_rejets.empty:
        for motif, cnt in df_rejets["motif_rejet"].value_counts().items():
            logger.warning(f"      • {motif} : {cnt}")
    
    # Colonnes finales Silver (dédupliquer par (id_temps, code_etage) → prendre la dernière)
    df_silver = df_valides[[
        "id_temps", "code_etage", "annee", "mois",
        "nb_clients", "volume_facture", "rendement",
        "fichier_source", "onglet_source", "date_extraction",
    ]].copy()
    
    # Déduplication (fichier historique peut avoir des doublons)
    df_silver = df_silver.drop_duplicates(
        subset=["id_temps", "code_etage"], keep="last"
    ).reset_index(drop=True)
    
    df_silver["id_temps"] = df_silver["id_temps"].astype("int64")
    
    return df_silver, df_rejets


def transform_vol_amene(df_bronze: pd.DataFrame, cfg: dict) -> tuple:
    """Transforme le Bronze vol_amene → Silver format long propre."""
    logger.info("🔄 Transform vol_amene...")
    
    mapping_etages = cfg["etages_normalisation"]
    mapping_mois   = cfg["mois_en"]
    
    df = df_bronze.copy()
    
    df["code_etage"] = df["nom_etage_source"].apply(
        lambda x: _normalize_etage(x, mapping_etages)
    )
    
    df[["annee", "mois"]] = df["mois_source"].apply(
        lambda x: pd.Series(_parse_mois_en(x, mapping_mois))
    )
    df["id_temps"] = df.apply(
        lambda r: _year_month_to_id_temps(r["annee"], r["mois"]), axis=1
    )
    
    df["volume_amene"] = df["vol_amene_source"].apply(_parse_float)
    
    # Rejets
    df["motif_rejet"] = None
    df.loc[df["code_etage"].isna(),   "motif_rejet"] = "etage_inconnu"
    df.loc[df["id_temps"].isna(),     "motif_rejet"] = "mois_invalide"
    # Volume NULL → ignoré (rien à charger), pas rejet
    
    df_rejets  = df[df["motif_rejet"].notna()].copy()
    df_valides = df[df["motif_rejet"].isna() & df["volume_amene"].notna()].copy()
    
    logger.info(f"   ✅ {len(df_valides)} valides | ❌ {len(df_rejets)} rejets")
    if not df_rejets.empty:
        for motif, cnt in df_rejets["motif_rejet"].value_counts().items():
            logger.warning(f"      • {motif} : {cnt}")
    
    df_silver = df_valides[[
        "id_temps", "code_etage", "annee", "mois", "volume_amene",
        "fichier_source", "onglet_source", "date_extraction",
    ]].copy()
    
    df_silver = df_silver.drop_duplicates(
        subset=["id_temps", "code_etage"], keep="last"
    ).reset_index(drop=True)
    
    df_silver["id_temps"] = df_silver["id_temps"].astype("int64")
    
    return df_silver, df_rejets


def merge_and_enrich(
    df_histo: pd.DataFrame, 
    df_vol: pd.DataFrame,
    df_lineaires: pd.DataFrame,
    cfg: dict,
) -> pd.DataFrame:
    """
    Fusionne histo + vol_amene par (id_temps, code_etage) [FULL OUTER].
    Enrichit avec linéaire et calcule pertes + ILP.
    """
    logger.info("🔗 Fusion histo + vol_amene...")
    
    # FULL OUTER JOIN sur (id_temps, code_etage)
    df = pd.merge(
        df_histo[["id_temps", "code_etage", "annee", "mois",
                  "nb_clients", "volume_facture", "rendement"]],
        df_vol[["id_temps", "code_etage", "volume_amene"]],
        on=["id_temps", "code_etage"],
        how="outer",
    )
    
    logger.info(f"   Résultat fusion : {len(df)} lignes")
    logger.info(f"      • Histo seul       : {df['nb_clients'].notna().sum() & df['volume_amene'].isna().sum()}")
    logger.info(f"      • Vol_amene seul   : {df['volume_amene'].notna().sum() & df['nb_clients'].isna().sum()}")
    logger.info(f"      • Les deux         : {(df['nb_clients'].notna() & df['volume_amene'].notna()).sum()}")
    
    # Reconstituer annee/mois si NULL (venait uniquement de vol_amene)
    if df["annee"].isna().any():
        df["annee"] = df["annee"].fillna(df["id_temps"].astype(str).str[:4].astype(int))
        df["mois"]  = df["mois"].fillna(df["id_temps"].astype(str).str[4:6].astype(int))
    
    # Enrichir avec linéaire
    df = df.merge(df_lineaires, on="code_etage", how="left")
    
    # Calculs dérivés
    df["volume_pertes"] = df["volume_amene"] - df["volume_facture"]
    
    # ILP = volume_pertes / lineaire_km / nb_jours_mois
    nb_jours = cfg["regles"]["nb_jours_mois_default"]
    df["ilp"] = np.where(
        (df["lineaire_km"] > 0) & df["volume_pertes"].notna(),
        df["volume_pertes"] / df["lineaire_km"] / nb_jours,
        np.nan,
    )
    
    # Source de données
    df["source_donnees"] = "histo_pbi+vol_amene"
    df.loc[df["nb_clients"].isna(),   "source_donnees"] = "vol_amene_seul"
    df.loc[df["volume_amene"].isna(), "source_donnees"] = "histo_pbi_seul"
    
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
        # 1. Charger Bronze
        df_bronze_histo = read_parquet(get_latest_parquet("bronze", SOURCE_NAME, "histo_rendement"))
        df_bronze_vol   = read_parquet(get_latest_parquet("bronze", SOURCE_NAME, "vol_amene"))
        
        # 2. Charger linéaires depuis DWH
        from etl.common.db import read_sql
        df_lineaires = read_sql("""
            SELECT code_etage, lineaire_km
            FROM dwh.dim_etage
            WHERE id_etage > 0
        """)
        
        # 3. Transformer
        df_histo_sv, df_rej_h = transform_histo(df_bronze_histo, cfg)
        df_vol_sv,   df_rej_v = transform_vol_amene(df_bronze_vol, cfg)
        
        # 4. Fusionner + enrichir
        df_silver = merge_and_enrich(df_histo_sv, df_vol_sv, df_lineaires, cfg)
        
        # 5. Sauvegardes
        logger.info("-" * 70)
        logger.info(f"📊 Silver final : {len(df_silver)} lignes")
        
        if not df_silver.empty:
            p = save_parquet(df_silver, "silver", SOURCE_NAME, "rendements")
            result["silver_parquet"] = str(p)
            result["nb_silver"] = len(df_silver)
        
        # Consolider rejets
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