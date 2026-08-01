"""
ETL - PMAC
Étape : TRANSFORM (Silver)

Rôle :
- Lire le Parquet Bronze
- Résoudre les Surrogate Keys (id_point_mesure, id_source_mesure, id_temps)
- Appliquer les règles de qualité (GOOD/SUSPECT/BAD)
- Détecter et gérer les doublons temporels
- Ventiler les valeurs dans les bonnes colonnes selon la voie
- Séparer valides / rejets
- Sauvegarder Silver Parquet
"""
from datetime import datetime
import pandas as pd
import numpy as np

from etl.common.config import CONFIG, load_mapping
from etl.common.logger import get_logger
from etl.common.io_utils import save_parquet, get_latest_parquet, read_parquet
from etl.common.dim_resolver import (
    get_point_mesure_mapping,
    get_source_mesure_mapping,
    datetime_to_id_temps,
    clear_cache_pmac,
)

logger = get_logger(__name__)

SOURCE_NAME = "pmac"

# Sentinelles pour étage/secteur (INCONNU pour l'instant)
ID_ETAGE_INCONNU   = 0
ID_SECTEUR_INCONNU = 0

# Statuts qualité
QUALITE_GOOD    = "GOOD"
QUALITE_SUSPECT = "SUSPECT"
QUALITE_BAD     = "BAD"


# ═══════════════════════════════════════════════════════════════
# RÈGLES DE QUALITÉ
# ═══════════════════════════════════════════════════════════════

def _evaluate_qualite(voie: str, valeur: float, regles: dict) -> str:
    """
    Évalue la qualité d'une valeur selon les seuils métier.
    
    Retourne : GOOD | SUSPECT | BAD
    """
    if pd.isna(valeur):
        return QUALITE_BAD
    
    voie_key = voie.lower() if voie else "autre"
    regle = regles.get(voie_key)
    
    if not regle:
        # Voie sans règle spécifique → GOOD par défaut
        return QUALITE_GOOD
    
    max_absolu = regle.get("max_absolu")
    max_normal = regle.get("max_normal")
    min_normal = regle.get("min_normal")
    
    # BAD : dépasse le seuil absolu (rejet)
    if max_absolu is not None and valeur > max_absolu:
        return QUALITE_BAD
    if min_normal is not None and valeur < -abs(max_absolu or 500):  # bornes basses très permissives
        return QUALITE_BAD
    
    # SUSPECT : hors plage normale mais dans plage absolue
    if max_normal is not None and valeur > max_normal:
        return QUALITE_SUSPECT
    if min_normal is not None and valeur < min_normal:
        return QUALITE_SUSPECT
    
    return QUALITE_GOOD


# ═══════════════════════════════════════════════════════════════
# RÉSOLUTION DES SURROGATE KEYS
# ═══════════════════════════════════════════════════════════════

def _resolve_sk(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Résout les Surrogate Keys : id_point_mesure, id_source_mesure, id_temps.
    
    Retourne (df_valides, df_rejets_sk).
    """
    logger.info("🔑 Résolution des Surrogate Keys...")
    
    clear_cache_pmac()
    map_point  = get_point_mesure_mapping()
    map_source = get_source_mesure_mapping()
    
    df = df.copy()
    
    # 1. id_point_mesure (via pmac_id)
    df["id_point_mesure"] = df["pmac_id"].map(map_point)
    
    # 2. id_source_mesure (via source_code)
    df["id_source_mesure"] = df["source_code"].map(map_source)
    
    # 3. id_temps (via date_heure → YYYYMMDD)
    df["id_temps"] = df["date_heure"].apply(datetime_to_id_temps)
    
    # 4. id_etage / id_secteur = INCONNU pour l'instant
    df["id_etage"]   = ID_ETAGE_INCONNU
    df["id_secteur"] = ID_SECTEUR_INCONNU
    
    # 5. Détection des rejets
    df["motif_rejet"] = None
    df.loc[df["id_point_mesure"].isna(),  "motif_rejet"] = "point_mesure_introuvable"
    df.loc[df["id_source_mesure"].isna(), "motif_rejet"] = "source_mesure_introuvable"
    df.loc[df["id_temps"].isna(),         "motif_rejet"] = "date_heure_invalide"
    df.loc[df["valeur_brute"].isna(),     "motif_rejet"] = "valeur_null"
    
    df_rejets  = df[df["motif_rejet"].notna()].copy()
    df_valides = df[df["motif_rejet"].isna()].copy()
    
    logger.info(f"   ✅ Valides : {len(df_valides):,} | ❌ Rejets SK : {len(df_rejets):,}")
    
    if not df_rejets.empty:
        for motif, cnt in df_rejets["motif_rejet"].value_counts().items():
            logger.warning(f"      • {motif} : {cnt:,}")
        # Détail des PMAC introuvables
        if "point_mesure_introuvable" in df_rejets["motif_rejet"].values:
            pmac_ko = df_rejets[df_rejets["motif_rejet"] == "point_mesure_introuvable"]["pmac_id"].unique()
            logger.warning(f"      → PMAC_IDs introuvables : {sorted(pmac_ko)[:20]}")
    
    return df_valides, df_rejets


# ═══════════════════════════════════════════════════════════════
# CONTRÔLE QUALITÉ + BAD → REJETS
# ═══════════════════════════════════════════════════════════════

def _apply_qualite(df: pd.DataFrame, mapping: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Applique les règles de qualité.
    
    - GOOD → conservé
    - SUSPECT → conservé avec flag
    - BAD → rejeté
    
    Retourne (df_valides, df_rejets_qualite).
    """
    logger.info("🎯 Contrôle qualité des valeurs...")
    
    df = df.copy()
    regles = mapping.get("qualite_regles", {})
    
    df["qualite_donnees"] = df.apply(
        lambda row: _evaluate_qualite(row["voie"], row["valeur_brute"], regles),
        axis=1,
    )
    
    # Séparation
    df_bad     = df[df["qualite_donnees"] == QUALITE_BAD].copy()
    df_conserv = df[df["qualite_donnees"] != QUALITE_BAD].copy()
    
    if not df_bad.empty:
        df_bad["motif_rejet"] = "valeur_BAD_seuil_absolu"
    
    # Stats
    stats = df_conserv["qualite_donnees"].value_counts()
    logger.info(f"   ✅ GOOD    : {stats.get(QUALITE_GOOD, 0):,}")
    logger.info(f"   ⚠️  SUSPECT : {stats.get(QUALITE_SUSPECT, 0):,}")
    logger.info(f"   ❌ BAD     : {len(df_bad):,} (rejetés)")
    
    return df_conserv, df_bad


# ═══════════════════════════════════════════════════════════════
# DÉDUPLICATION TEMPORELLE
# ═══════════════════════════════════════════════════════════════

def _deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """
    Supprime les VRAIS doublons.
    
    Un vrai doublon = même (id_point_mesure, date_heure, voie, canal).
    
    NOTE : un même PMAC peut avoir plusieurs canaux physiques 
    (ex: DEBIT_02, DEBIT_03 sur des conduites différentes).
    Ce ne sont PAS des doublons.
    """
    logger.info("🔄 Déduplication temporelle...")
    
    nb_avant = len(df)
    
    # Trier par date_extraction pour garder la plus récente
    df_sorted = df.sort_values("date_extraction", ascending=True)
    df_dedup = df_sorted.drop_duplicates(
        subset=["id_point_mesure", "date_heure", "voie", "canal"],   # ← "canal" ajouté !
        keep="last",
    )
    
    nb_doublons = nb_avant - len(df_dedup)
    if nb_doublons > 0:
        logger.info(f"   → {nb_doublons:,} VRAIS doublons supprimés (même clé complète)")
    else:
        logger.info(f"   → Aucun vrai doublon")
    
    return df_dedup.reset_index(drop=True)

# ═══════════════════════════════════════════════════════════════
# VENTILATION DES VALEURS PAR VOIE
# ═══════════════════════════════════════════════════════════════

def _ventiler_valeurs(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ventile les valeurs dans les bonnes colonnes selon la voie et amont/aval.
    
    Règles :
      - voie=PRESSION + est_amont → pression_amont_bar
      - voie=PRESSION + est_aval  → pression_aval_bar
      - voie=PRESSION sans A/A    → pression_bar
      - voie=DEBIT                → debit_m3_h
      - voie=INDEX                → index_compteur
      - voie=VOLUME               → volume_15min
    """
    logger.info("🎨 Ventilation des valeurs par voie...")
    
    df = df.copy()
    
    # Initialiser toutes les colonnes de mesures à NaN
    df["pression_bar"]       = np.nan
    df["pression_amont_bar"] = np.nan
    df["pression_aval_bar"]  = np.nan
    df["debit_m3_h"]         = np.nan
    df["volume_15min"]       = np.nan
    df["index_compteur"]     = np.nan
    
    # PRESSION
    mask_pression = df["voie"] == "PRESSION"
    mask_amont = mask_pression & df["est_amont"] & (~df["est_aval"])
    mask_aval  = mask_pression & df["est_aval"]  & (~df["est_amont"])
    mask_pres  = mask_pression & (~df["est_amont"]) & (~df["est_aval"])
    
    df.loc[mask_amont, "pression_amont_bar"] = df.loc[mask_amont, "valeur_brute"]
    df.loc[mask_aval,  "pression_aval_bar"]  = df.loc[mask_aval,  "valeur_brute"]
    df.loc[mask_pres,  "pression_bar"]       = df.loc[mask_pres,  "valeur_brute"]
    
    # DEBIT
    mask_debit = df["voie"] == "DEBIT"
    df.loc[mask_debit, "debit_m3_h"] = df.loc[mask_debit, "valeur_brute"]
    
    # INDEX
    mask_index = df["voie"] == "INDEX"
    df.loc[mask_index, "index_compteur"] = df.loc[mask_index, "valeur_brute"]
    
    # VOLUME
    mask_volume = df["voie"] == "VOLUME"
    df.loc[mask_volume, "volume_15min"] = df.loc[mask_volume, "valeur_brute"]
    
    # Logs de ventilation
    logger.info(f"   • pression_bar       : {df['pression_bar'].notna().sum():,}")
    logger.info(f"   • pression_amont_bar : {df['pression_amont_bar'].notna().sum():,}")
    logger.info(f"   • pression_aval_bar  : {df['pression_aval_bar'].notna().sum():,}")
    logger.info(f"   • debit_m3_h         : {df['debit_m3_h'].notna().sum():,}")
    logger.info(f"   • volume_15min       : {df['volume_15min'].notna().sum():,}")
    logger.info(f"   • index_compteur     : {df['index_compteur'].notna().sum():,}")
    
    return df


# ═══════════════════════════════════════════════════════════════
# POINT D'ENTRÉE PRINCIPAL
# ═══════════════════════════════════════════════════════════════

def run_transform() -> dict:
    """Exécute la transformation Silver."""
    logger.info("=" * 70)
    logger.info("🥈 SILVER - TRANSFORMATION PMAC")
    logger.info("=" * 70)
    
    result = {"status": "success"}
    
    try:
        # 1. Charger Bronze
        path_bronze = get_latest_parquet("bronze", SOURCE_NAME, "mesures")
        df_bronze = read_parquet(path_bronze)
        logger.info(f"📖 Bronze : {len(df_bronze):,} lignes")
        
        # 2. Charger mapping métier
        mapping = load_mapping(SOURCE_NAME, "pmac_config")
        
        # 3. Résolution des SK
        df_valides, df_rej_sk = _resolve_sk(df_bronze)
        
        # 4. Contrôle qualité
        df_valides, df_rej_bad = _apply_qualite(df_valides, mapping)
        
        # 5. Consolider les rejets
        df_rejets = pd.concat([df_rej_sk, df_rej_bad], ignore_index=True) if not df_rej_bad.empty or not df_rej_sk.empty else pd.DataFrame()
        
        # 6. Déduplication
        df_valides = _deduplicate(df_valides)
        
        # 7. Ventilation des valeurs
        df_valides = _ventiler_valeurs(df_valides)
        
        # 8. Colonnes finales Silver
        cols_silver = [
            # Clés
            "id_temps", "id_etage", "id_secteur", "id_point_mesure", "id_source_mesure",
            # Timestamp
            "date_heure",
            # Mesures ventilées
            "pression_bar", "pression_amont_bar", "pression_aval_bar",
            "debit_m3_h", "volume_15min", "index_compteur",
            # Qualité
            "qualite_donnees", "voie", "unite",
            # Traçabilité
            "pmac_id", "canal", "channel", "site_name", 
            "est_amont", "est_aval",
            "fichier_source", "source_code", "date_extraction",
        ]
        df_silver = df_valides[cols_silver].reset_index(drop=True)
        
        # Types SQL-friendly
        df_silver["id_temps"]         = df_silver["id_temps"].astype("int64")
        df_silver["id_etage"]         = df_silver["id_etage"].astype("int64")
        df_silver["id_secteur"]       = df_silver["id_secteur"].astype("int64")
        df_silver["id_point_mesure"]  = df_silver["id_point_mesure"].astype("int64")
        df_silver["id_source_mesure"] = df_silver["id_source_mesure"].astype("int64")
        
        # 9. Sauvegardes
        logger.info("-" * 70)
        logger.info(f"📊 RÉSUMÉ FINAL :")
        logger.info(f"   • Bronze total   : {len(df_bronze):,}")
        logger.info(f"   • Silver valides : {len(df_silver):,}")
        logger.info(f"   • Rejets totaux  : {len(df_rejets):,}")
        
        if not df_silver.empty:
            path = save_parquet(df_silver, "silver", SOURCE_NAME, "mesures")
            result["silver_parquet"] = str(path)
            result["nb_silver"] = len(df_silver)
        
        if not df_rejets.empty:
            path = save_parquet(df_rejets, "rejects", SOURCE_NAME, "mesures_rejets")
            result["rejects_parquet"] = str(path)
            result["nb_rejets"] = len(df_rejets)
        
        # Stats qualité
        if not df_silver.empty:
            qualite_stats = df_silver["qualite_donnees"].value_counts().to_dict()
            result["qualite_stats"] = qualite_stats
    
    except FileNotFoundError as e:
        logger.error(f"❌ Bronze introuvable : {e}")
        result["status"] = "error"
        result["error"] = str(e)
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
    print("\n📋 Résultat :")
    import json
    print(json.dumps(result, indent=2, default=str))