"""
Script de refresh des vues matérialisées Power BI.
Exécutable en CLI ou importable dans Airflow.

Usage CLI :
    python scripts/refresh_pbi_views.py                # Refresh toutes
    python scripts/refresh_pbi_views.py --view carte   # Refresh spécifique
"""
import argparse
import time
from datetime import datetime
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from etl.common.db import get_engine
from etl.common.logger import get_logger
from sqlalchemy import text

logger = get_logger(__name__)


# Vues matérialisées à refresh
MATERIALIZED_VIEWS = {
    "carte": "dwh.vw_pbi_carte_points_enrichie",
}


def refresh_view(view_name: str, concurrently: bool = True) -> dict:
    """Refresh une vue matérialisée."""
    start = time.time()
    engine = get_engine()
    
    mode = "CONCURRENTLY" if concurrently else ""
    sql = f"REFRESH MATERIALIZED VIEW {mode} {view_name};"
    
    logger.info(f"🔄 Refresh {view_name} (mode={mode or 'BLOCKING'})...")
    
    try:
        with engine.begin() as conn:
            conn.execute(text(sql))
        
        duration = round(time.time() - start, 2)
        logger.info(f"✅ {view_name} refresh terminé en {duration}s")
        return {"status": "success", "view": view_name, "duration_sec": duration}
    
    except Exception as e:
        logger.error(f"❌ Erreur refresh {view_name} : {e}")
        # Retry sans CONCURRENTLY (au cas où l'index unique manque)
        if concurrently:
            logger.warning(f"⚠️  Retry sans CONCURRENTLY...")
            return refresh_view(view_name, concurrently=False)
        return {"status": "error", "view": view_name, "error": str(e)}


def run_refresh_views(view_name: str = "all") -> dict:
    """
    Fonction principale appelée par Airflow ou Python sans passer par argparse.
    """
    logger.info("=" * 70)
    logger.info("🔄 REFRESH VUES MATÉRIALISÉES POWER BI")
    logger.info(f"   Démarré à : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)
    
    results = []
    
    if view_name == "all":
        views_to_refresh = MATERIALIZED_VIEWS.values()
    else:
        views_to_refresh = [MATERIALIZED_VIEWS.get(view_name, view_name)]
    
    for view in views_to_refresh:
        result = refresh_view(view)
        results.append(result)
    
    # Résumé
    logger.info("=" * 70)
    logger.info("📊 RÉSUMÉ REFRESH PBI")
    logger.info("=" * 70)
    
    for r in results:
        if r["status"] == "success":
            logger.info(f"✅ {r['view']} : {r['duration_sec']}s")
        else:
            logger.error(f"❌ {r['view']} : {r.get('error')}")
    
    logger.info("=" * 70)
    return {"status": "success", "results": results}


def main():
    """Point d'entrée CLI (ligne de commande uniquement)."""
    parser = argparse.ArgumentParser(description="Refresh vues matérialisées PBI")
    parser.add_argument(
        "--view",
        choices=list(MATERIALIZED_VIEWS.keys()) + ["all"],
        default="all",
        help="Vue à refresh (défaut: all)",
    )
    args = parser.parse_args()
    run_refresh_views(args.view)


if __name__ == "__main__":
    main()