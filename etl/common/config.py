"""Chargement de la configuration ETL depuis YAML + .env."""
from pathlib import Path
import os
import yaml
from dotenv import load_dotenv

# Racine du projet (2 niveaux au-dessus de ce fichier : etl/common/config.py)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Charger .env
load_dotenv(PROJECT_ROOT / ".env")


def load_etl_config() -> dict:
    """Charge etl/config/etl_config.yaml."""
    config_path = PROJECT_ROOT / "etl" / "config" / "etl_config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_mapping(source_name: str, mapping_name: str) -> dict:
    """
    Charge un fichier de mapping YAML.
    Ex: load_mapping('indicateurs_reclamations', 'indicateurs')
        → etl/config/mappings/indicateurs_reclamations/indicateurs.yaml
    """
    path = (
        PROJECT_ROOT
        / "etl"
        / "config"
        / "mappings"
        / source_name
        / f"{mapping_name}.yaml"
    )
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_path(key: str) -> Path:
    """Retourne un chemin absolu depuis la config (raw, bronze, silver, etc.)."""
    config = load_etl_config()
    rel_path = config["paths"][key]
    return PROJECT_ROOT / rel_path


def get_env(key: str, default: str = None) -> str:
    """Récupère une variable d'environnement."""
    return os.getenv(key, default)


# Constantes exportées
CONFIG = load_etl_config()