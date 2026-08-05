"""
ETL - PCWIN
Étape : TRANSFORM (Silver)

Rôle :
- Lire Parquet Bronze
- Détecter voie / canal_affichage / nature_mesure / granularite (logique alignée sur PBI M)
- Résoudre Surrogate Keys (id_point_mesure, id_source_mesure, id_temps)
- Appliquer règles qualité (GOOD/SUSPECT/BAD)
- Dédupliquer sur (id_point_mesure, datehe, voie, canal)
- Ventiler valeurs dans bonnes colonnes selon voie
- Sauvegarder Silver + Rejets
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

SOURCE_NAME = "pcwin"
SOURCE_CFG = CONFIG["sources"][SOURCE_NAME]

# Sentinelles étage/secteur
ID_ETAGE_INCONNU   = 0
ID_SECTEUR_INCONNU = 0

# Statuts qualité
QUALITE_GOOD    = "GOOD"
QUALITE_SUSPECT = "SUSPECT"
QUALITE_BAD     = "BAD"


# ═══════════════════════════════════════════════════════════════
# DÉTECTION VOIE / CANAL / NATURE / GRANULARITÉ
# ═══════════════════════════════════════════════════════════════

def _text_lower(v) -> str:
    """Retourne le texte en minuscules, ou '' si NaN/None."""
    if v is None or pd.isna(v):
        return ""
    return str(v).lower().strip()


def _match_keywords(text: str, keywords: list) -> bool:
    """True si au moins UN keyword est présent dans text."""
    return any(kw.lower() in text for kw in keywords)


def _match_all_keywords_groups(text: str, keywords_groups: list) -> bool:
    """
    True si au moins UN groupe de keywords match (tous les mots du groupe présents).
    keywords_groups = [["volume", "journalier"], ["vol", "journ"]]
    """
    for group in keywords_groups:
        if all(kw.lower() in text for kw in group):
            return True
    return False


def _detect_voie(libelle: str, unite: str, mapping: dict) -> str:
    """
    Reproduit la logique Power Query :
      1. Volume + journalier → VOLUME
      2. Pression / bar → PRESSION
      3. Débit / m3/h → DEBIT
      4. Comptage / index → INDEX
      5. Sinon AUTRE
    """
    lib = _text_lower(libelle)
    uni = _text_lower(unite)

    cfg = mapping["voie_detection"]

    # VOLUME (doit checker en premier car "volume journalier" contient déjà "volume")
    v_cfg = cfg.get("volume", {})
    if _match_all_keywords_groups(lib, v_cfg.get("keywords_all", [])):
        return "VOLUME"

    # PRESSION
    p_cfg = cfg.get("pression", {})
    if _match_keywords(lib, p_cfg.get("keywords", [])) or uni in p_cfg.get("unites", []):
        return "PRESSION"

    # DEBIT
    d_cfg = cfg.get("debit", {})
    if _match_keywords(lib, d_cfg.get("keywords", [])) or uni in d_cfg.get("unites", []):
        return "DEBIT"

    # INDEX
    i_cfg = cfg.get("index", {})
    if _match_keywords(lib, i_cfg.get("keywords", [])):
        return "INDEX"

    return "AUTRE"


def _detect_canal_affichage(libelle: str, unite: str, mapping: dict) -> str:
    """
    Détecte le canal_affichage (plus fin que voie).
    Reproduit la cascade Power Query.
    """
    lib = _text_lower(libelle)
    uni = _text_lower(unite)

    # 1. PRESSION
    if "pression" in lib or uni == "bar":
        return "PRESSION"

    # 2. VOLUME_JOURNALIER
    if "volume" in lib and "journalier" in lib:
        return "VOLUME_JOURNALIER"

    # 3. DEBIT_MIN_JOURNALIER
    if (("debit" in lib or "débit" in lib) and
        ("min" in lib or "minimum" in lib)):
        return "DEBIT_MIN_JOURNALIER"

    # 4. DEBIT
    if "debit" in lib or "débit" in lib or uni == "m3/h":
        return "DEBIT"

    # 5. INDEX
    if "comptage" in lib or "index" in lib:
        return "INDEX"

    return "AUTRE"


def _detect_nature_mesure(libelle: str, unite: str) -> str:
    """Détecte la nature métier de la mesure."""
    lib = _text_lower(libelle)
    uni = _text_lower(unite)

    if "volume" in lib and "journalier" in lib:
        return "VOLUME_JOURNALIER_CALCULE"

    if (("debit" in lib or "débit" in lib) and
        ("min" in lib or "minimum" in lib)):
        return "DEBIT_MIN_JOURNALIER_CALCULE"

    if "comptage" in lib or "index" in lib:
        return "INDEX_CUMULATIF"

    if ("debit" in lib or "débit" in lib) or uni == "m3/h":
        return "DEBIT_INSTANTANE"

    if "pression" in lib or uni == "bar":
        return "PRESSION_INSTANTANEE"

    return "AUTRE"


def _detect_granularite(libelle: str) -> str:
    """JOURNALIER si contient 'journalier' ou 'jour', sinon INSTANTANE."""
    lib = _text_lower(libelle)
    if "journalier" in lib or "jour" in lib:
        return "JOURNALIER"
    return "INSTANTANE"


def _detect_amont_aval(libelle: str, mapping: dict) -> tuple[bool, bool]:
    """Retourne (est_amont, est_aval) depuis les mots-clés dans libelle."""
    lib = _text_lower(libelle)
    aa = mapping.get("amont_aval_detection", {})

    est_amont = any(kw.lower() in lib for kw in aa.get("amont_keywords", []))
    est_aval  = any(kw.lower() in lib for kw in aa.get("aval_keywords", []))

    return est_amont, est_aval


# ═══════════════════════════════════════════════════════════════
# CONSTRUCTION DU CANAL (VOIE_XX)
# ═══════════════════════════════════════════════════════════════

def _build_canal(voie: str, variable_id: int) -> str:
    """
    Construit le canal au format VOIE_XX (comme PMAC).
    Pour PCWIN, on utilise variable_id % 100 formaté sur 2 chiffres.
    Ex: variable_id=101 → canal="DEBIT_01"
        variable_id=203 → canal="DEBIT_03"
    """
    if not voie or voie == "AUTRE":
        voie = "AUTRE"
    channel = f"{int(variable_id) % 100:02d}"
    return f"{voie}_{channel}"


# ═══════════════════════════════════════════════════════════════
# RÈGLES DE QUALITÉ
# ═══════════════════════════════════════════════════════════════

def _evaluate_qualite(voie: str, valeur: float, regles: dict) -> str:
    """Évalue GOOD/SUSPECT/BAD selon les seuils par voie."""
    if pd.isna(valeur):
        return QUALITE_BAD

    voie_key = voie.lower() if voie else "autre"
    regle = regles.get(voie_key)
    if not regle:
        return QUALITE_GOOD

    max_absolu = regle.get("max_absolu")
    max_normal = regle.get("max_normal")
    min_normal = regle.get("min_normal")

    if max_absolu is not None and valeur > max_absolu:
        return QUALITE_BAD
    if min_normal is not None and valeur < -abs(max_absolu or 500):
        return QUALITE_BAD
    if max_normal is not None and valeur > max_normal:
        return QUALITE_SUSPECT
    if min_normal is not None and valeur < min_normal:
        return QUALITE_SUSPECT

    return QUALITE_GOOD


# ═══════════════════════════════════════════════════════════════
# RÉSOLUTION SK
# ═══════════════════════════════════════════════════════════════

def _resolve_sk(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Résout id_point_mesure, id_source_mesure, id_temps."""
    logger.info("🔑 Résolution des Surrogate Keys...")

    clear_cache_pmac()
    map_point  = get_point_mesure_mapping()
    map_source = get_source_mesure_mapping()

    df = df.copy()

    df["id_point_mesure"]  = df["id_pmac"].map(map_point)
    df["id_source_mesure"] = df["source_code"].map(map_source)
    df["id_temps"]         = df["datehe"].apply(datetime_to_id_temps)
    df["id_etage"]         = ID_ETAGE_INCONNU
    df["id_secteur"]       = ID_SECTEUR_INCONNU

    df["motif_rejet"] = None
    df.loc[df["id_point_mesure"].isna(),  "motif_rejet"] = "point_mesure_introuvable"
    df.loc[df["id_source_mesure"].isna(), "motif_rejet"] = "source_mesure_introuvable"
    df.loc[df["id_temps"].isna(),         "motif_rejet"] = "datehe_invalide"
    df.loc[df["valeur"].isna(),           "motif_rejet"] = "valeur_null"

    df_rejets  = df[df["motif_rejet"].notna()].copy()
    df_valides = df[df["motif_rejet"].isna()].copy()

    logger.info(f"   ✅ Valides : {len(df_valides):,} | ❌ Rejets SK : {len(df_rejets):,}")

    if not df_rejets.empty:
        for motif, cnt in df_rejets["motif_rejet"].value_counts().items():
            logger.warning(f"      • {motif} : {cnt:,}")
        if "point_mesure_introuvable" in df_rejets["motif_rejet"].values:
            pmac_ko = df_rejets[df_rejets["motif_rejet"] == "point_mesure_introuvable"]["id_pmac"].unique()
            logger.warning(f"      → id_pmac introuvables : {sorted(pmac_ko)[:20]}")

    return df_valides, df_rejets


# ═══════════════════════════════════════════════════════════════
# QUALITÉ
# ═══════════════════════════════════════════════════════════════

def _apply_qualite(df: pd.DataFrame, mapping: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Applique les règles qualité. BAD → rejeté."""
    logger.info("🎯 Contrôle qualité...")

    df = df.copy()
    regles = mapping.get("qualite_regles", {})

    df["qualite_donnees"] = df.apply(
        lambda row: _evaluate_qualite(row["voie"], row["valeur"], regles),
        axis=1,
    )

    df_bad     = df[df["qualite_donnees"] == QUALITE_BAD].copy()
    df_conserv = df[df["qualite_donnees"] != QUALITE_BAD].copy()

    if not df_bad.empty:
        df_bad["motif_rejet"] = "valeur_BAD_seuil_absolu"

    stats = df_conserv["qualite_donnees"].value_counts()
    logger.info(f"   ✅ GOOD    : {stats.get(QUALITE_GOOD, 0):,}")
    logger.info(f"   ⚠️  SUSPECT : {stats.get(QUALITE_SUSPECT, 0):,}")
    logger.info(f"   ❌ BAD     : {len(df_bad):,} (rejetés)")

    return df_conserv, df_bad


# ═══════════════════════════════════════════════════════════════
# DÉDUPLICATION
# ═══════════════════════════════════════════════════════════════

def _deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """Supprime les vrais doublons sur (id_point_mesure, datehe, voie, canal)."""
    logger.info("🔄 Déduplication...")
    nb_avant = len(df)

    df_sorted = df.sort_values("date_extraction", ascending=True)
    df_dedup = df_sorted.drop_duplicates(
        subset=["id_point_mesure", "datehe", "voie", "canal"],
        keep="last",
    )

    nb_doublons = nb_avant - len(df_dedup)
    if nb_doublons > 0:
        logger.info(f"   → {nb_doublons:,} doublons supprimés")
    else:
        logger.info(f"   → Aucun doublon")

    return df_dedup.reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════
# VENTILATION
# ═══════════════════════════════════════════════════════════════

def _ventiler_valeurs(df: pd.DataFrame) -> pd.DataFrame:
    """Ventile valeur → colonne cible selon voie + amont/aval."""
    logger.info("🎨 Ventilation des valeurs...")

    df = df.copy()

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

    df.loc[mask_amont, "pression_amont_bar"] = df.loc[mask_amont, "valeur"]
    df.loc[mask_aval,  "pression_aval_bar"]  = df.loc[mask_aval,  "valeur"]
    df.loc[mask_pres,  "pression_bar"]       = df.loc[mask_pres,  "valeur"]

    # DEBIT
    mask_debit = df["voie"] == "DEBIT"
    df.loc[mask_debit, "debit_m3_h"] = df.loc[mask_debit, "valeur"]

    # INDEX
    mask_index = df["voie"] == "INDEX"
    df.loc[mask_index, "index_compteur"] = df.loc[mask_index, "valeur"]

    # VOLUME (traité comme volume journalier)
    mask_volume = df["voie"] == "VOLUME"
    df.loc[mask_volume, "volume_15min"] = df.loc[mask_volume, "valeur"]

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
    logger.info("🥈 SILVER - TRANSFORMATION PCWIN")
    logger.info("=" * 70)

    result = {"status": "success"}

    try:
        # 1. Charger Bronze
        path_bronze = get_latest_parquet("bronze", SOURCE_NAME, "mesures")
        df_bronze = read_parquet(path_bronze)
        logger.info(f"📖 Bronze : {len(df_bronze):,} lignes")

        # 2. Charger mapping
        mapping = load_mapping(SOURCE_NAME, "pcwin_config")

        # 3. Enrichissement métier
        logger.info("🏷️  Détection voie/canal_affichage/nature_mesure/granularité...")
        df = df_bronze.copy()

        df["voie"] = df.apply(
            lambda r: _detect_voie(r["libelle_mesure"], r["unite"], mapping),
            axis=1,
        )
        df["canal_affichage"] = df.apply(
            lambda r: _detect_canal_affichage(r["libelle_mesure"], r["unite"], mapping),
            axis=1,
        )
        df["nature_mesure"] = df.apply(
            lambda r: _detect_nature_mesure(r["libelle_mesure"], r["unite"]),
            axis=1,
        )
        df["granularite"] = df["libelle_mesure"].apply(_detect_granularite)

        aa = df.apply(
            lambda r: _detect_amont_aval(r["libelle_mesure"], mapping),
            axis=1,
        )
        df["est_amont"] = aa.apply(lambda x: x[0])
        df["est_aval"]  = aa.apply(lambda x: x[1])

        # 4. Construction du canal (VOIE_XX)
        df["canal"] = df.apply(
            lambda r: _build_canal(r["voie"], r["variable_id"]),
            axis=1,
        )
        df["channel"] = df["canal"].str.split("_").str[-1]

        # Stats voies
        logger.info(f"   📊 Répartition voies :")
        for voie, cnt in df["voie"].value_counts().items():
            logger.info(f"      • {voie:10s} : {cnt:,}")

        # 5. Résolution SK
        df_valides, df_rej_sk = _resolve_sk(df)

        # 6. Qualité
        df_valides, df_rej_bad = _apply_qualite(df_valides, mapping)

        # 7. Consolider rejets
        rejets_list = [r for r in [df_rej_sk, df_rej_bad] if not r.empty]
        df_rejets = pd.concat(rejets_list, ignore_index=True) if rejets_list else pd.DataFrame()

        # 8. Déduplication
        df_valides = _deduplicate(df_valides)

        # 9. Ventilation
        df_valides = _ventiler_valeurs(df_valides)

        # 10. Colonnes finales Silver
        cols_silver = [
            # Clés
            "id_temps", "id_etage", "id_secteur", "id_point_mesure", "id_source_mesure",
            # Timestamp
            "datehe",
            # Mesures ventilées
            "pression_bar", "pression_amont_bar", "pression_aval_bar",
            "debit_m3_h", "volume_15min", "index_compteur",
            # Qualité et voie
            "qualite_donnees", "voie", "unite",
            # Enrichissement PCWIN
            "canal_affichage", "nature_mesure", "granularite",
            # Traçabilité
            "id_pmac", "canal", "channel",
            "station_id", "nom_station", "variable_id", "variable_key",
            "libelle_mesure",
            "est_amont", "est_aval",
            "source_code", "date_extraction",
        ]
        df_silver = df_valides[cols_silver].reset_index(drop=True)

        # Types SQL-friendly
        df_silver["id_temps"]         = df_silver["id_temps"].astype("int64")
        df_silver["id_etage"]         = df_silver["id_etage"].astype("int64")
        df_silver["id_secteur"]       = df_silver["id_secteur"].astype("int64")
        df_silver["id_point_mesure"]  = df_silver["id_point_mesure"].astype("int64")
        df_silver["id_source_mesure"] = df_silver["id_source_mesure"].astype("int64")

        # 11. Sauvegardes
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

        if not df_silver.empty:
            result["qualite_stats"] = df_silver["qualite_donnees"].value_counts().to_dict()
            result["voie_stats"]    = df_silver["voie"].value_counts().to_dict()

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