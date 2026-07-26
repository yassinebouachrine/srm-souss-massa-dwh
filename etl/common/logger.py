"""Configuration centralisée du logging."""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime
from etl.common.config import CONFIG, get_path, get_env


def get_logger(name: str) -> logging.Logger:
    """
    Retourne un logger configuré (console + fichier).
    
    Le fichier de log est créé dans data/logs/etl_YYYYMMDD.log
    """
    logger = logging.getLogger(name)

    # Éviter la double configuration
    if logger.handlers:
        return logger

    level_str = get_env("ETL_LOG_LEVEL", CONFIG["logging"]["level"])
    logger.setLevel(getattr(logging, level_str.upper()))

    fmt = logging.Formatter(
        CONFIG["logging"]["format"],
        datefmt=CONFIG["logging"]["date_format"],
    )

    # Console
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    # Fichier
    logs_dir = get_path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / f"etl_{datetime.now():%Y%m%d}.log"

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=CONFIG["logging"]["file_rotation_mb"] * 1024 * 1024,
        backupCount=CONFIG["logging"]["file_backup_count"],
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    return logger