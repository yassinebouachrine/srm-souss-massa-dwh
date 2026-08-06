"""
ETL - Rendements Étage
Étape : EXTRACT (Bronze)

Lit les 2 fichiers Excel :
- etages_rendements_Histo PBI.xlsx  → nb_clients, vol_facture, vol_amené (bonus), rendement
- Volume Amené par étage (1).xlsx   → vol_amene (wide format, headers = dates Excel)

Consolide en 2 Parquet Bronze séparés.
"""
from datetime import datetime, date
import pandas as pd

from etl.common.config import get_path, load_mapping
from etl.common.logger import get_logger
from etl.common.io_utils import save_parquet

logger = get_logger(__name__)

SOURCE_NAME = "rendements"


# ═══════════════════════════════════════════════════════════════
# EXTRACT 1 : HISTO RENDEMENT (déjà en format long)
# ═══════════════════════════════════════════════════════════════
def _normalize_mois_source(val) -> str:
    """
    Normalise une valeur de mois en format 'Mon-YY' unifié.
    
    Gère :
    - datetime/Timestamp (2021-06-01) → 'Jun-21'
    - Strings FR : 'juin-21', 'juil.-21', 'août-21' → gardés tels quels
    - NaN → None
    """
    if val is None or pd.isna(val):
        return None
    
    # Cas datetime (pandas lit parfois "juin-21" comme datetime)
    if isinstance(val, (datetime, date, pd.Timestamp)):
        return pd.Timestamp(val).strftime("%b-%y")
    
    # Sinon retourner tel quel (string FR)
    s = str(val).strip()
    if not s or s.lower() == "nan":
        return None
    return s




def _extract_histo(cfg: dict, date_extraction: datetime) -> pd.DataFrame:
    """
    Structure attendue :
    NOM_ETAGE | Mois _année | Nombre de clients | Vol amené | Vol Facturé | Rendement
    
    Note : la colonne 'Vol amené' est optionnelle mais on la lit si présente.
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
    
    # Renommer colonnes (avec variantes possibles)
    rename_map = {
        "NOM_ETAGE":          "nom_etage_source",
        "Mois _année":        "mois_source",
        "Mois_année":         "mois_source",
        "Nombre de clients":  "nb_clients_source",
        "Vol amené":          "vol_amene_source",   # ← NOUVEAU (si présent)
        "Vol Amené":          "vol_amene_source",   # variante casse
        "Vol Facturé":        "vol_facture_source",
        "Rendement":          "rendement_source",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    
    # Ajouter colonne vol_amene_source si absente
    if "vol_amene_source" not in df.columns:
        df["vol_amene_source"] = None
        logger.info("   ℹ️  Colonne 'Vol amené' absente → sera récupérée depuis Volume Amené par étage.xlsx")
    else:
        nb_vol = df["vol_amene_source"].notna().sum()
        logger.info(f"   ℹ️  Colonne 'Vol amené' trouvée : {nb_vol}/{len(df)} valeurs")
    
    # ⚠️ Normaliser mois_source AVANT le cast str
    # (Excel peut convertir "juin-21" en datetime automatiquement)
    df["mois_source"] = df["mois_source"].apply(_normalize_mois_source)
    
    # Cast string pour Parquet (Bronze = brut)
    df["nom_etage_source"] = df["nom_etage_source"].astype(str)
    df["mois_source"]      = df["mois_source"].astype(str)
    
    df["fichier_source"]  = filename
    df["onglet_source"]   = sheet
    df["date_extraction"] = date_extraction
    
    logger.info(f"   ✅ {len(df)} lignes extraites")
    return df


# ═══════════════════════════════════════════════════════════════
# EXTRACT 2 : VOLUME AMENÉ (wide format avec datetime headers)
# ═══════════════════════════════════════════════════════════════

def _parse_mois_header(val) -> str:
    """
    Convertit un header de mois en format 'Mon-YY' unifié.
    
    Cas gérés :
    - datetime.datetime(2022, 1, 1)  → 'Jan-22'
    - pd.Timestamp('2022-01-01')     → 'Jan-22'
    - 'Jan-22' (string)              → 'Jan-22'
    - 'Mois 06/2021'                 → 'Jun-21'
    - NaN                            → None
    """
    if val is None or pd.isna(val):
        return None
    
    # Cas datetime
    if isinstance(val, (datetime, date, pd.Timestamp)):
        return pd.Timestamp(val).strftime("%b-%y")
    
    # Cas string
    s = str(val).strip()
    if not s or s.lower() == "nan":
        return None
    
    # Cas "Mois MM/YYYY" (ex: "Mois 06/2021")
    if s.lower().startswith("mois"):
        import re
        m = re.match(r'mois\s+(\d{1,2})[/\-](\d{4})', s.lower())
        if m:
            mois_num, annee = int(m.group(1)), int(m.group(2))
            try:
                dt = datetime(annee, mois_num, 1)
                return dt.strftime("%b-%y")
            except ValueError:
                return None
    
    # Sinon retourner tel quel (sera parsé par transform.py)
    return s


def _extract_vol_amene(cfg: dict, date_extraction: datetime) -> pd.DataFrame:
    """
    Structure attendue :
    Ligne 0 : mois (Jan-22, Feb-22... OU datetime Excel OU 'Mois 06/2021')
    Ligne 1 : NOM_ETAGE | Vol Amené | Vol Amené | ...
    Lignes 2+ : nom_etage | valeur | valeur | ...
    """
    filename = cfg["files"]["vol_amene"]
    sheet    = cfg["sheets"]["vol_amene"]
    filepath = get_path("raw") / "referentiels" / "etoile_c" / filename
    
    if not filepath.exists():
        raise FileNotFoundError(f"❌ {filepath}")
    
    logger.info(f"📖 {filename} (onglet '{sheet}')")
    
    # Lecture SANS header
    df_raw = pd.read_excel(filepath, sheet_name=sheet, engine="openpyxl", header=None)
    logger.info(f"   → {df_raw.shape[0]} lignes × {df_raw.shape[1]} colonnes brutes")
    
    # Ligne 0 = mois, Ligne 1 = labels, Lignes 2+ = données
    mois_raw = df_raw.iloc[0].tolist()
    
    # Normaliser les headers de mois
    mois_headers = [_parse_mois_header(v) for v in mois_raw]
    
    # Log échantillon
    valid_headers = [h for h in mois_headers[1:] if h is not None][:6]
    logger.info(f"   Mois headers (échantillon) : {valid_headers}")
    
    # Reconstruire au format long
    records = []
    for row_idx in range(2, len(df_raw)):
        nom_etage = df_raw.iloc[row_idx, 0]
        if pd.isna(nom_etage) or str(nom_etage).strip() == "":
            continue
        
        nom_etage = str(nom_etage).strip()
        
        for col_idx in range(1, len(mois_headers)):
            mois_str = mois_headers[col_idx]
            if mois_str is None:
                continue
            
            valeur = df_raw.iloc[row_idx, col_idx]
            
            # Ignorer les valeurs vides (mais garder 0.0)
            if pd.isna(valeur):
                continue
            
            records.append({
                "nom_etage_source": nom_etage,
                "mois_source":      mois_str,
                "vol_amene_source": valeur,
            })
    
    df_long = pd.DataFrame(records)
    logger.info(f"   ✅ {len(df_long)} lignes après unpivot")
    
    df_long["fichier_source"]  = filename
    df_long["onglet_source"]   = sheet
    df_long["date_extraction"] = date_extraction
    
    # ⚠️ IMPORTANT : Cast TOUT en string pour Parquet Bronze
    # (les valeurs Excel peuvent être numériques OU strings avec espaces insécables)
    df_long["nom_etage_source"] = df_long["nom_etage_source"].astype(str)
    df_long["mois_source"]      = df_long["mois_source"].astype(str)
    df_long["vol_amene_source"] = df_long["vol_amene_source"].astype(str)  # ← AJOUTÉ
    
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