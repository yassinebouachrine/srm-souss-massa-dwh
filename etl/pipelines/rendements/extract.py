"""
ETL - Rendements Étage
Étape : EXTRACT (Bronze)

Lit les 2 fichiers Excel :
- etages_rendements_Histo PBI.xlsx  → nb_clients, vol_facture, rendement
- Volume Amené par étage (1).xlsx   → vol_amene (wide format)

Consolide en 2 Parquet Bronze séparés.
"""
from datetime import datetime
import pandas as pd

from etl.common.config import get_path, load_mapping
from etl.common.logger import get_logger
from etl.common.io_utils import save_parquet

logger = get_logger(__name__)

SOURCE_NAME = "rendements"


# ═══════════════════════════════════════════════════════════════
# EXTRACT 1 : HISTO RENDEMENT (déjà en format long)
# ═══════════════════════════════════════════════════════════════

def _extract_histo(cfg: dict, date_extraction: datetime) -> pd.DataFrame:
    """
    Structure attendue :
    NOM_ETAGE | Mois_année | Nombre de clients | Vol Facturé | Rendement
    """
    filename = cfg["files"]["histo_rendement"]
    sheet    = cfg["sheets"]["histo_rendement"]
    filepath = get_path("raw") / "referentiels" / "etoile_c" / filename
    
    if not filepath.exists():
        raise FileNotFoundError(f"❌ {filepath}")
    
    logger.info(f"📖 {filename} (onglet '{sheet}')")
    df = pd.read_excel(filepath, sheet_name=sheet, engine="openpyxl")
    df.columns = [c.strip() for c in df.columns]
    
    logger.info(f"   → {len(df)} lignes, colonnes : {list(df.columns)}")
    
    # Renommer colonnes
    df = df.rename(columns={
        "NOM_ETAGE":          "nom_etage_source",
        "Mois _année":        "mois_source",
        "Mois_année":         "mois_source",  # variante sans espace
        "Nombre de clients":  "nb_clients_source",
        "Vol Facturé":        "vol_facture_source",
        "Rendement":          "rendement_source",
    })
    
    # Cast en string pour Parquet Bronze (on ne type pas encore)
    for col in ["nom_etage_source", "mois_source"]:
        df[col] = df[col].astype(str)
    
    df["fichier_source"]  = filename
    df["onglet_source"]   = sheet
    df["date_extraction"] = date_extraction
    
    logger.info(f"   ✅ {len(df)} lignes extraites")
    return df


# ═══════════════════════════════════════════════════════════════
# EXTRACT 2 : VOLUME AMENÉ (wide format)
# ═══════════════════════════════════════════════════════════════

def _extract_vol_amene(cfg: dict, date_extraction: datetime) -> pd.DataFrame:
    """
    Structure attendue :
    Ligne 1     : Jan-22 | Feb-22 | ... (mois en headers)
    Ligne 2     : NOM_ETAGE | Vol Amené | Vol Amené | ... (labels)
    Lignes 3+   : nom_etage | valeur | valeur | ...
    """
    filename = cfg["files"]["vol_amene"]
    sheet    = cfg["sheets"]["vol_amene"]
    filepath = get_path("raw") / "referentiels" / "etoile_c" / filename
    
    if not filepath.exists():
        raise FileNotFoundError(f"❌ {filepath}")
    
    logger.info(f"📖 {filename} (onglet '{sheet}')")
    
    # Lecture SANS header pour gérer manuellement
    df_raw = pd.read_excel(filepath, sheet_name=sheet, engine="openpyxl", header=None)
    logger.info(f"   → {df_raw.shape[0]} lignes × {df_raw.shape[1]} colonnes brutes")
    
    # Ligne 0 = mois (Jan-22, Feb-22...), colonne 0 vide
    # Ligne 1 = labels (NOM_ETAGE, Vol Amené, Vol Amené...)
    # Lignes 2+ = données
    
    mois_headers = df_raw.iloc[0].tolist()
    labels       = df_raw.iloc[1].tolist()
    
    logger.info(f"   Mois headers (extrait) : {mois_headers[1:6]}...")
    
    # Reconstruire un DataFrame long
    records = []
    for row_idx in range(2, len(df_raw)):
        nom_etage = df_raw.iloc[row_idx, 0]
        if pd.isna(nom_etage) or str(nom_etage).strip() == "":
            continue
        
        nom_etage = str(nom_etage).strip()
        
        # Parcourir les colonnes de mois
        for col_idx in range(1, len(mois_headers)):
            mois_val = mois_headers[col_idx]
            valeur   = df_raw.iloc[row_idx, col_idx]
            
            if pd.isna(mois_val):
                continue
            
            records.append({
                "nom_etage_source": nom_etage,
                "mois_source":      str(mois_val),
                "vol_amene_source": valeur,
            })
    
    df_long = pd.DataFrame(records)
    logger.info(f"   ✅ {len(df_long)} lignes après unpivot")
    
    df_long["fichier_source"]  = filename
    df_long["onglet_source"]   = sheet
    df_long["date_extraction"] = date_extraction
    
    return df_long


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def run_extract() -> dict:
    logger.info("=" * 70)
    logger.info("🥉 BRONZE - EXTRACTION RENDEMENTS ÉTAGE")
    logger.info("=" * 70)
    
    date_extraction = datetime.now()
    cfg = load_mapping(SOURCE_NAME, "rendements_config")
    result = {"status": "success"}
    
    # 1. Histo rendement
    try:
        df_histo = _extract_histo(cfg, date_extraction)
        if not df_histo.empty:
            path = save_parquet(df_histo, "bronze", SOURCE_NAME, "histo_rendement")
            result["bronze_histo"] = str(path)
            result["nb_histo"] = len(df_histo)
    except Exception as e:
        logger.error(f"❌ Erreur histo : {e}", exc_info=True)
        result["status"] = "partial"
    
    logger.info("-" * 70)
    
    # 2. Volume amené
    try:
        df_vol = _extract_vol_amene(cfg, date_extraction)
        if not df_vol.empty:
            path = save_parquet(df_vol, "bronze", SOURCE_NAME, "vol_amene")
            result["bronze_vol_amene"] = str(path)
            result["nb_vol_amene"] = len(df_vol)
    except Exception as e:
        logger.error(f"❌ Erreur vol_amene : {e}", exc_info=True)
        result["status"] = "partial"
    
    logger.info("=" * 70)
    logger.info("✅ EXTRACTION TERMINÉE")
    logger.info("=" * 70)
    
    return result


if __name__ == "__main__":
    result = run_extract()
    print("\n📋 Résultat :")
    for k, v in result.items():
        print(f"   • {k}: {v}")