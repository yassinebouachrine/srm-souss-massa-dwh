"""
ETL - GSTCOM (Clientèle & Consommations)
Étape : EXTRACT (Bronze)

Lit le fichier Excel GSTCOM et sauvegarde en Parquet Bronze.
Aucune transformation métier ici.
"""
from datetime import datetime
from pathlib import Path
import pandas as pd

from etl.common.config import get_path, load_mapping
from etl.common.logger import get_logger
from etl.common.io_utils import save_parquet, list_raw_files

logger = get_logger(__name__)

SOURCE_NAME = "gstcom"


def _extract_file(filepath: Path, cfg: dict, date_extraction: datetime) -> pd.DataFrame:
    """Lit un fichier Excel GSTCOM."""
    sheet = cfg.get("sheet_name", "Feuil1")
    
    logger.info(f"📖 {filepath.name} (onglet '{sheet}')")
    df = pd.read_excel(filepath, sheet_name=sheet, engine="openpyxl")
    df.columns = [c.strip() for c in df.columns]
    
    logger.info(f"   → {len(df)} lignes brutes, {len(df.columns)} colonnes")
    logger.info(f"   Colonnes : {list(df.columns)}")
    
    # Rename colonnes (mapping YAML)
    rename_map = {k: v for k, v in cfg["column_mapping"].items() if k in df.columns}
    df = df.rename(columns=rename_map)
    
    # Vérifier les colonnes attendues (celles qui étaient dans le mapping mais pas dans le fichier)
    expected_cols = list(cfg["column_mapping"].keys())
    original_cols_before_rename = list(rename_map.keys())
    missing = [k for k in expected_cols if k not in original_cols_before_rename]
    if missing:
        logger.warning(f"   ⚠️  Colonnes attendues manquantes : {missing}")
    else:
        logger.info(f"   ✅ Toutes les colonnes attendues sont présentes ({len(rename_map)}/{len(expected_cols)})")
    
    # Traçabilité
    df["fichier_source"]  = filepath.name
    df["date_extraction"] = date_extraction
    
    # ⚠️ Cast tout en string pour éviter les problèmes de type mixte Parquet
    # (les vraies conversions seront faites en Silver)
    for col in df.columns:
        if col not in ["date_extraction"]:
            df[col] = df[col].astype(str)
    
    logger.info(f"   ✅ {len(df)} lignes extraites")
    return df


def run_extract() -> dict:
    logger.info("=" * 70)
    logger.info("🥉 BRONZE - EXTRACTION GSTCOM")
    logger.info("=" * 70)
    
    date_extraction = datetime.now()
    cfg = load_mapping(SOURCE_NAME, "gstcom_config")
    result = {"status": "success"}
    
    # Lister fichiers
    files = list_raw_files(SOURCE_NAME, cfg.get("file_pattern", "*.xlsx"))
    if not files:
        logger.warning(f"⚠️  Aucun fichier trouvé dans data/raw/{SOURCE_NAME}/")
        return {"status": "no_files"}
    
    logger.info(f"📁 {len(files)} fichier(s) à traiter")
    
    all_dfs = []
    for filepath in files:
        try:
            df = _extract_file(filepath, cfg, date_extraction)
            if not df.empty:
                all_dfs.append(df)
        except Exception as e:
            logger.error(f"❌ Erreur fichier {filepath.name} : {e}", exc_info=True)
    
    if not all_dfs:
        return {"status": "empty"}
    
    df_final = pd.concat(all_dfs, ignore_index=True)
    logger.info(f"📊 TOTAL : {len(df_final):,} lignes clientèle")
    
    path = save_parquet(df_final, "bronze", SOURCE_NAME, "clientele")
    result["bronze_parquet"] = str(path)
    result["nb_lignes"] = len(df_final)
    
    logger.info("=" * 70)
    logger.info("✅ EXTRACTION TERMINÉE")
    logger.info("=" * 70)
    return result


if __name__ == "__main__":
    result = run_extract()
    print("\n📋 Résultat :")
    for k, v in result.items():
        print(f"   • {k}: {v}")