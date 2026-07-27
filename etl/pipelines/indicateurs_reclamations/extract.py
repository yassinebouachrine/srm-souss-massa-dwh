"""
ETL - Indicateurs & Réclamations
Étape : EXTRACT (Bronze)

Rôle :
- Lire les fichiers Excel bruts (1 fichier par DP)
- Extraire les 2 blocs de chaque onglet (indicateurs + réclamations)
- Ajouter les métadonnées de traçabilité
- Sauvegarder en Parquet dans data/bronze/indicateurs_reclamations/

Aucune transformation métier ici : on garde le format wide tel quel.
"""
from pathlib import Path
from datetime import datetime
import unicodedata
import pandas as pd

from etl.common.config import CONFIG, load_mapping
from etl.common.logger import get_logger
from etl.common.io_utils import save_parquet, list_raw_files

logger = get_logger(__name__)

SOURCE_NAME = "indicateurs_reclamations"
SOURCE_CFG = CONFIG["sources"][SOURCE_NAME]


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _normalize_text(text: str) -> str:
    """Uppercase, retire les accents (pour matcher les noms de fichiers)."""
    if not text:
        return ""
    t = unicodedata.normalize("NFD", str(text))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return t.upper().strip()


def _resolve_dp_from_filename(filepath: Path, dp_mapping: dict) -> tuple[str, str]:
    """
    Détermine le code_dp et le nom du DP à partir du nom du fichier.
    
    Retourne (code_dp, nom_dp_lisible) ou (None, None) si non reconnu.
    """
    filename_norm = _normalize_text(filepath.stem)
    
    # Trier les patterns par longueur décroissante (les plus spécifiques d'abord)
    # Ex: "CHTOUKA AIT BAHA" doit matcher avant "CHTOUKA"
    patterns_sorted = sorted(
        dp_mapping["fichiers_vers_dp"].items(),
        key=lambda kv: len(kv[0]),
        reverse=True,
    )
    
    for pattern, code_dp in patterns_sorted:
        if _normalize_text(pattern) in filename_norm:
            return code_dp, pattern
    
    return None, None


def _clean_column_name(col) -> str:
    """
    Nettoie un nom de colonne pour Parquet.
    Ex: 'Jan-25' → 'jan_25'
        'Récap 2025' → 'recap_2025'
        Timestamp(2025-01-01) → 'jan_25'
    """
    if pd.isna(col):
        return "unnamed"
    
    # Cas Timestamp (Excel les parse parfois comme dates)
    if isinstance(col, pd.Timestamp):
        return col.strftime("%b_%y").lower()
    
    col_str = str(col).strip()
    # Retirer accents
    col_str = unicodedata.normalize("NFD", col_str)
    col_str = "".join(c for c in col_str if unicodedata.category(c) != "Mn")
    # Lowercase, remplacer espaces et tirets par underscore
    col_str = col_str.lower().replace(" ", "_").replace("-", "_")
    # Retirer caractères spéciaux résiduels
    col_str = "".join(c if c.isalnum() or c == "_" else "_" for c in col_str)
    # Retirer underscores multiples
    while "__" in col_str:
        col_str = col_str.replace("__", "_")
    return col_str.strip("_")


def _is_recap_column(col_name: str) -> bool:
    """Détecte si une colonne est une colonne 'Récap YYYY' à ignorer."""
    pattern = SOURCE_CFG["colonnes_ignorer_pattern"].lower()
    return pattern in col_name.lower()


# ═══════════════════════════════════════════════════════════════
# EXTRACTION D'UN BLOC (Indicateurs OU Réclamations)
# ═══════════════════════════════════════════════════════════════

def _extract_bloc(
    df_full: pd.DataFrame,
    header_row: int,
    data_start_row: int,
    data_end_row: int,
    bloc_name: str,
) -> pd.DataFrame:
    """
    Extrait un bloc (indicateurs ou réclamations) d'un onglet Excel.
    
    - Prend le header à la ligne header_row
    - Prend les données de data_start_row à data_end_row
    - La 1ère colonne devient 'libelle_source'
    - Les autres colonnes deviennent les périodes (jan_25, feb_25, ...)
    """
    if len(df_full) <= header_row:
        logger.warning(f"   ⚠️  Onglet trop court pour le bloc '{bloc_name}' (lignes={len(df_full)})")
        return pd.DataFrame()
    
    # Récupérer les noms de colonnes depuis la ligne header
    header = df_full.iloc[header_row].tolist()
    columns = ["libelle_source"] + [_clean_column_name(c) for c in header[1:]]
    
    # Extraire les données
    end = min(data_end_row + 1, len(df_full))  # +1 car iloc exclusif
    df_bloc = df_full.iloc[data_start_row:end].copy()
    df_bloc.columns = columns
    
    # Filtrer lignes vides (pas de libellé)
    df_bloc = df_bloc[df_bloc["libelle_source"].notna()]
    df_bloc = df_bloc[df_bloc["libelle_source"].astype(str).str.strip() != ""]
    
    # Retirer les colonnes "Récap YYYY"
    cols_to_keep = ["libelle_source"] + [
        c for c in df_bloc.columns[1:] if not _is_recap_column(c)
    ]
    df_bloc = df_bloc[cols_to_keep]
    
    # Convertir tous les types en string pour Parquet (Bronze = brut, on ne type pas encore)
    # Sauf libelle_source qui est déjà string
    for col in df_bloc.columns[1:]:
        df_bloc[col] = df_bloc[col].astype(str)
    
    df_bloc["libelle_source"] = df_bloc["libelle_source"].astype(str).str.strip()
    
    return df_bloc.reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════
# EXTRACTION D'UN ONGLET COMPLET
# ═══════════════════════════════════════════════════════════════

def _extract_onglet(
    filepath: Path,
    onglet: str,
    code_dp: str,
    nom_dp: str,
    date_extraction: datetime,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Extrait un onglet complet : renvoie (df_indicateurs, df_reclamations).
    """
    logger.info(f"   📄 Onglet : '{onglet}'")
    
    # Lecture brute (sans header, on gère manuellement)
    df_full = pd.read_excel(filepath, sheet_name=onglet, header=None, engine="openpyxl")
    
    est_recap = (onglet == SOURCE_CFG["onglet_recap"])
    nom_centre_source = None if est_recap else onglet
    
    metadata = {
        "fichier_source": filepath.name,
        "onglet_source": onglet,
        "code_dp_source": code_dp,
        "nom_dp_source": nom_dp,
        "nom_centre_source": nom_centre_source,
        "est_recap_dp": est_recap,
        "date_extraction": date_extraction,
    }
    
    # Bloc Indicateurs
    cfg_ind = SOURCE_CFG["bloc_indicateurs"]
    df_ind = _extract_bloc(
        df_full,
        cfg_ind["header_row"],
        cfg_ind["data_start_row"],
        cfg_ind["data_end_row"],
        "indicateurs",
    )
    if not df_ind.empty:
        for k, v in metadata.items():
            df_ind[k] = v
    
    # Bloc Réclamations
    cfg_rec = SOURCE_CFG["bloc_reclamations"]
    df_rec = _extract_bloc(
        df_full,
        cfg_rec["header_row"],
        cfg_rec["data_start_row"],
        cfg_rec["data_end_row"],
        "reclamations",
    )
    if not df_rec.empty:
        for k, v in metadata.items():
            df_rec[k] = v
    
    logger.info(f"      → Indicateurs : {len(df_ind)} lignes | Réclamations : {len(df_rec)} lignes")
    return df_ind, df_rec


# ═══════════════════════════════════════════════════════════════
# EXTRACTION D'UN FICHIER COMPLET
# ═══════════════════════════════════════════════════════════════

def _extract_fichier(
    filepath: Path,
    dp_mapping: dict,
    date_extraction: datetime,
) -> tuple[list[pd.DataFrame], list[pd.DataFrame]]:
    """
    Extrait tous les onglets d'un fichier. Retourne (list_indicateurs, list_reclamations).
    """
    logger.info(f"📂 Fichier : {filepath.name}")
    
    code_dp, nom_dp = _resolve_dp_from_filename(filepath, dp_mapping)
    if not code_dp:
        logger.error(f"   ❌ Impossible de déterminer le DP pour '{filepath.name}' — fichier ignoré")
        return [], []
    
    logger.info(f"   → DP détecté : {code_dp} ({nom_dp})")
    
    # Lister tous les onglets
    try:
        xl = pd.ExcelFile(filepath, engine="openpyxl")
        onglets = xl.sheet_names
    except Exception as e:
        logger.error(f"   ❌ Erreur lecture fichier : {e}")
        return [], []
    
    logger.info(f"   → {len(onglets)} onglets trouvés : {onglets}")
    
    list_ind, list_rec = [], []
    for onglet in onglets:
        try:
            df_ind, df_rec = _extract_onglet(filepath, onglet, code_dp, nom_dp, date_extraction)
            if not df_ind.empty:
                list_ind.append(df_ind)
            if not df_rec.empty:
                list_rec.append(df_rec)
        except Exception as e:
            logger.error(f"   ❌ Erreur onglet '{onglet}' : {e}", exc_info=True)
    
    return list_ind, list_rec


# ═══════════════════════════════════════════════════════════════
# POINT D'ENTRÉE PRINCIPAL
# ═══════════════════════════════════════════════════════════════

def run_extract() -> dict:
    """
    Exécute l'extraction complète (Bronze).
    
    Returns:
        dict avec les chemins des fichiers Parquet créés et les stats
    """
    logger.info("=" * 70)
    logger.info("🥉 BRONZE - EXTRACTION INDICATEURS & RÉCLAMATIONS")
    logger.info("=" * 70)
    
    date_extraction = datetime.now()
    
    # 1. Charger le mapping des DP
    dp_mapping = load_mapping(SOURCE_NAME, "dp")
    
    # 2. Lister les fichiers Excel
    files = list_raw_files(SOURCE_NAME, SOURCE_CFG["file_pattern"])
    if not files:
        logger.warning(f"⚠️  Aucun fichier trouvé dans data/raw/{SOURCE_CFG['raw_folder']}/")
        return {"status": "no_files", "files_processed": 0}
    
    logger.info(f"📁 {len(files)} fichier(s) Excel à traiter")
    
    # 3. Extraire chaque fichier
    all_indicateurs, all_reclamations = [], []
    for filepath in files:
        list_ind, list_rec = _extract_fichier(filepath, dp_mapping, date_extraction)
        all_indicateurs.extend(list_ind)
        all_reclamations.extend(list_rec)
    
    # 4. Consolider en 2 gros DataFrames
    if not all_indicateurs and not all_reclamations:
        logger.warning("⚠️  Aucune donnée extraite")
        return {"status": "empty", "files_processed": len(files)}
    
    df_ind_final = pd.concat(all_indicateurs, ignore_index=True) if all_indicateurs else pd.DataFrame()
    df_rec_final = pd.concat(all_reclamations, ignore_index=True) if all_reclamations else pd.DataFrame()
    
    logger.info("-" * 70)
    logger.info(f"📊 TOTAL EXTRAIT :")
    logger.info(f"   • Indicateurs : {len(df_ind_final)} lignes")
    logger.info(f"   • Réclamations : {len(df_rec_final)} lignes")
    
    # 5. Sauvegarder en Parquet
    result = {"status": "success", "files_processed": len(files)}
    
    if not df_ind_final.empty:
        path_ind = save_parquet(df_ind_final, "bronze", SOURCE_NAME, "indicateurs")
        result["bronze_indicateurs"] = str(path_ind)
        result["nb_lignes_indicateurs"] = len(df_ind_final)
    
    if not df_rec_final.empty:
        path_rec = save_parquet(df_rec_final, "bronze", SOURCE_NAME, "reclamations")
        result["bronze_reclamations"] = str(path_rec)
        result["nb_lignes_reclamations"] = len(df_rec_final)
    
    logger.info("=" * 70)
    logger.info("✅ EXTRACTION TERMINÉE")
    logger.info("=" * 70)
    
    return result


if __name__ == "__main__":
    result = run_extract()
    print("\n📋 Résultat :")
    for k, v in result.items():
        print(f"   • {k}: {v}")