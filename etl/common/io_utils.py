"""Utilitaires I/O : lecture/écriture Parquet + gestion fichiers."""
from pathlib import Path
from datetime import datetime
import pandas as pd
from etl.common.config import get_path
from etl.common.logger import get_logger

logger = get_logger(__name__)


def save_parquet(
    df: pd.DataFrame,
    layer: str,           # 'bronze' | 'silver' | 'rejects'
    source: str,          # ex: 'indicateurs_reclamations'
    name: str,            # ex: 'indicateurs' ou 'reclamations'
    add_timestamp: bool = True,
) -> Path:
    """
    Sauvegarde un DataFrame en Parquet dans data/<layer>/<source>/.
    
    Nomenclature : <name>_YYYYMMDD_HHMMSS.parquet
    """
    folder = get_path(layer) / source
    folder.mkdir(parents=True, exist_ok=True)

    if add_timestamp:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{ts}.parquet"
    else:
        filename = f"{name}.parquet"

    filepath = folder / filename
    df.to_parquet(filepath, index=False, engine="pyarrow")
    logger.info(f"✅ Parquet sauvegardé : {filepath} ({len(df)} lignes)")
    return filepath


def read_parquet(filepath: Path) -> pd.DataFrame:
    """Lit un fichier Parquet."""
    df = pd.read_parquet(filepath, engine="pyarrow")
    logger.info(f"📖 Parquet lu : {filepath} ({len(df)} lignes)")
    return df


def get_latest_parquet(layer: str, source: str, name_prefix: str) -> Path:
    """
    Retourne le dernier fichier Parquet correspondant au préfixe.
    Ex: get_latest_parquet('bronze', 'indicateurs_reclamations', 'indicateurs')
    """
    folder = get_path(layer) / source
    files = sorted(folder.glob(f"{name_prefix}_*.parquet"), reverse=True)
    if not files:
        raise FileNotFoundError(f"Aucun fichier {name_prefix}_*.parquet dans {folder}")
    return files[0]


def list_raw_files(source: str, pattern: str = "*.xlsx") -> list[Path]:
    """Liste les fichiers bruts d'une source."""
    folder = get_path("raw") / source
    if not folder.exists():
        logger.warning(f"⚠️  Dossier introuvable : {folder}")
        return []
    return sorted(folder.glob(pattern))