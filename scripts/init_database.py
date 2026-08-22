# """
# Initialisation complète de la base de données DWH.

# Exécute dans l'ordre :
# 1. DDL (structures des tables)
# 2. DML (seeds statiques)
# 3. Scripts Python de peuplement des dimensions

# Usage :
#     python scripts/init_database.py                  # Init complète
#     python scripts/init_database.py --ddl-only       # Uniquement DDL
#     python scripts/init_database.py --seeds-only     # Uniquement seeds
#     python scripts/init_database.py --skip-python    # Sans les seeds Python
# """
# import argparse
# import subprocess
# import sys
# from pathlib import Path
# from datetime import datetime

# PROJECT_ROOT = Path(__file__).resolve().parent.parent
# sys.path.insert(0, str(PROJECT_ROOT))

# from etl.common.config import get_env
# from etl.common.logger import get_logger

# logger = get_logger(__name__)


# # ═══════════════════════════════════════════════════════════════
# # ORDRE D'EXÉCUTION
# # ═══════════════════════════════════════════════════════════════

# DDL_FILES = sorted((PROJECT_ROOT / "database" / "ddl").glob("*.sql"))
# DML_FILES = sorted((PROJECT_ROOT / "database" / "dml").glob("*.sql"))


# PYTHON_SEEDS = [
#     "etl.setup.initialization.generate_dim_temps",
#     "etl.setup.initialization.seed_dim_point_mesure",
#     "etl.setup.initialization.seed_dim_point_mesure_pcwin",
#     "etl.setup.initialization.seed_dim_canal_label",
#     "etl.setup.initialization.seed_bridge_groupe_point_pcwin",
#     "etl.setup.initialization.seed_dim_loc_sec_bridge",
#     "etl.setup.initialization.update_dim_etage_lineaire",
#     "etl.setup.initialization.update_dim_secteur_lineaire",
# ]


# # ═══════════════════════════════════════════════════════════════
# # HELPERS
# # ═══════════════════════════════════════════════════════════════

# def run_sql_file(filepath: Path) -> bool:
#     """Exécute un fichier .sql via psql."""
#     host = get_env("POSTGRES_HOST", "localhost")
#     port = get_env("POSTGRES_PORT", "5432")
#     db   = get_env("POSTGRES_DB")
#     user = get_env("POSTGRES_USER")
#     pwd  = get_env("POSTGRES_PASSWORD")
    
#     env = {"PGPASSWORD": pwd, **dict(__import__("os").environ)}
    
#     cmd = [
#         "psql",
#         "-h", host, "-p", port,
#         "-U", user, "-d", db,
#         "-f", str(filepath),
#         "-v", "ON_ERROR_STOP=1",
#     ]
    
#     logger.info(f"📄 {filepath.name}")
#     result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    
#     if result.returncode != 0:
#         logger.error(f"❌ Erreur SQL : {result.stderr}")
#         return False
#     return True


# def run_python_module(module_path: str) -> bool:
#     """Exécute un module Python."""
#     import importlib
    
#     logger.info(f"🐍 {module_path}")
#     try:
#         module = importlib.import_module(module_path)
#         if hasattr(module, "main"):
#             module.main()
#         return True
#     except Exception as e:
#         logger.error(f"❌ Erreur : {e}", exc_info=True)
#         return False


# # ═══════════════════════════════════════════════════════════════
# # MAIN
# # ═══════════════════════════════════════════════════════════════

# def main():
#     parser = argparse.ArgumentParser(description="Init DB SRM DWH")
#     parser.add_argument("--ddl-only",    action="store_true")
#     parser.add_argument("--seeds-only",  action="store_true")
#     parser.add_argument("--skip-python", action="store_true")
#     args = parser.parse_args()
    
#     start = datetime.now()
#     logger.info("=" * 70)
#     logger.info("🔧 INITIALISATION BASE DE DONNÉES SRM DWH")
#     logger.info("=" * 70)
    
#     total, errors = 0, 0
    
#     # 1. DDL
#     if not args.seeds_only:
#         logger.info("\n📐 EXÉCUTION DES DDL")
#         logger.info("-" * 70)
#         for f in DDL_FILES:
#             total += 1
#             if not run_sql_file(f):
#                 errors += 1
    
#     # 2. DML (seeds SQL)
#     if not args.ddl_only:
#         logger.info("\n🌱 EXÉCUTION DES DML (seeds SQL)")
#         logger.info("-" * 70)
#         for f in DML_FILES:
#             total += 1
#             if not run_sql_file(f):
#                 errors += 1
    
#     # 3. Scripts Python de peuplement
#     if not args.ddl_only and not args.skip_python:
#         logger.info("\n🐍 EXÉCUTION DES SEEDS PYTHON")
#         logger.info("-" * 70)
#         for module in PYTHON_SEEDS:
#             total += 1
#             if not run_python_module(module):
#                 errors += 1
    
#     # Résumé
#     duration = (datetime.now() - start).total_seconds()
#     logger.info("\n" + "=" * 70)
#     logger.info(f"📊 RÉSUMÉ : {total} scripts | {errors} erreurs | {duration:.1f}s")
#     logger.info("=" * 70)
    
#     sys.exit(0 if errors == 0 else 1)


# if __name__ == "__main__":
#     main()








"""
Initialisation complète de la base de données DWH.

Exécute dans l'ordre :
1. DDL (structures des tables)
2. DML (seeds statiques)
3. Views (vues SQL)
4. Scripts Python de peuplement des dimensions

Usage :
    python scripts/init_database.py                  # Init complète
    python scripts/init_database.py --ddl-only       # Uniquement DDL
    python scripts/init_database.py --seeds-only     # Uniquement seeds
    python scripts/init_database.py --views-only      # Uniquement views
    python scripts/init_database.py --skip-python    # Sans les seeds Python
"""
import argparse
import subprocess
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from etl.common.config import get_env
from etl.common.logger import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════
# ORDRE D'EXÉCUTION
# ═══════════════════════════════════════════════════════════════

DDL_FILES = sorted((PROJECT_ROOT / "database" / "ddl").glob("*.sql"))
DML_FILES = sorted((PROJECT_ROOT / "database" / "dml").glob("*.sql"))
VIEWS_FILES = sorted((PROJECT_ROOT / "database" / "views").glob("*.sql"))


PYTHON_SEEDS = [
    "etl.setup.initialization.generate_dim_temps",
    "etl.setup.initialization.seed_dim_point_mesure",
    "etl.setup.initialization.seed_dim_point_mesure_pcwin",
    "etl.setup.initialization.seed_dim_canal_label",
    "etl.setup.initialization.seed_bridge_groupe_point_pcwin",
    "etl.setup.initialization.seed_dim_loc_sec_bridge",
    "etl.setup.initialization.update_dim_etage_lineaire",
    "etl.setup.initialization.update_dim_secteur_lineaire",
]


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def run_sql_file(filepath: Path) -> bool:
    """Exécute un fichier .sql via psql."""
    host = get_env("POSTGRES_HOST", "localhost")
    port = get_env("POSTGRES_PORT", "5432")
    db   = get_env("POSTGRES_DB")
    user = get_env("POSTGRES_USER")
    pwd  = get_env("POSTGRES_PASSWORD")
    
    env = {"PGPASSWORD": pwd, **dict(__import__("os").environ)}
    
    cmd = [
        "psql",
        "-h", host, "-p", port,
        "-U", user, "-d", db,
        "-f", str(filepath),
        "-v", "ON_ERROR_STOP=1",
    ]
    
    logger.info(f"📄 {filepath.name}")
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    
    if result.returncode != 0:
        logger.error(f"❌ Erreur SQL : {result.stderr}")
        return False
    return True


def run_python_module(module_path: str) -> bool:
    """Exécute un module Python."""
    import importlib
    
    logger.info(f"🐍 {module_path}")
    try:
        module = importlib.import_module(module_path)
        if hasattr(module, "main"):
            module.main()
        return True
    except Exception as e:
        logger.error(f"❌ Erreur : {e}", exc_info=True)
        return False


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Init DB SRM DWH")
    parser.add_argument("--ddl-only",    action="store_true")
    parser.add_argument("--seeds-only",  action="store_true")
    parser.add_argument("--views-only",  action="store_true")
    parser.add_argument("--skip-python", action="store_true")
    args = parser.parse_args()
    
    only_flags = (args.ddl_only, args.seeds_only, args.views_only)
    run_all = not any(only_flags)
    
    start = datetime.now()
    logger.info("=" * 70)
    logger.info("🔧 INITIALISATION BASE DE DONNÉES SRM DWH")
    logger.info("=" * 70)
    
    total, errors = 0, 0
    
    # 1. DDL
    if run_all or args.ddl_only:
        logger.info("\n📐 EXÉCUTION DES DDL")
        logger.info("-" * 70)
        for f in DDL_FILES:
            total += 1
            if not run_sql_file(f):
                errors += 1
    
    # 2. DML (seeds SQL)
    if run_all or args.seeds_only:
        logger.info("\n🌱 EXÉCUTION DES DML (seeds SQL)")
        logger.info("-" * 70)
        for f in DML_FILES:
            total += 1
            if not run_sql_file(f):
                errors += 1
    
    # 3. Views
    if run_all or args.views_only:
        logger.info("\n👁️  EXÉCUTION DES VIEWS")
        logger.info("-" * 70)
        for f in VIEWS_FILES:
            total += 1
            if not run_sql_file(f):
                errors += 1
    
    # 4. Scripts Python de peuplement
    if run_all and not args.skip_python:
        logger.info("\n🐍 EXÉCUTION DES SEEDS PYTHON")
        logger.info("-" * 70)
        for module in PYTHON_SEEDS:
            total += 1
            if not run_python_module(module):
                errors += 1
    
    # Résumé
    duration = (datetime.now() - start).total_seconds()
    logger.info("\n" + "=" * 70)
    logger.info(f"📊 RÉSUMÉ : {total} scripts | {errors} erreurs | {duration:.1f}s")
    logger.info("=" * 70)
    
    sys.exit(0 if errors == 0 else 1)


if __name__ == "__main__":
    main()