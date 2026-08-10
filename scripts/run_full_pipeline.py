"""
Orchestration séquentielle de tous les pipelines ETL.
Version simple sans Airflow — utile pour tests et exécution manuelle.

Usage :
    python scripts/run_full_pipeline.py                     # Tous les pipelines
    python scripts/run_full_pipeline.py --source pmac       # Un seul pipeline
    python scripts/run_full_pipeline.py --skip pcwin        # Exclure un pipeline
    python scripts/run_full_pipeline.py --checks-only       # Uniquement les checks
"""
import argparse
import time
from datetime import datetime
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from etl.common.logger import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════
# CONFIGURATION DES PIPELINES
# ═══════════════════════════════════════════════════════════════

PIPELINES = {
    "indicateurs_reclamations": {
        "description": "Indicateurs & Réclamations (Excel DP)",
        "extract":    "etl.pipelines.indicateurs_reclamations.extract",
        "transform":  "etl.pipelines.indicateurs_reclamations.transform",
        "load":       "etl.pipelines.indicateurs_reclamations.load",
    },
    "streamlit": {
        "description": "Indicateurs & Réclamations (Streamlit)",
        "extract":    "etl.pipelines.streamlit_indicateurs_reclamations.extract",
        "transform":  "etl.pipelines.streamlit_indicateurs_reclamations.transform",
        "load":       "etl.pipelines.streamlit_indicateurs_reclamations.load",
    },
    "pmac": {
        "description": "Mesures PMAC (CSV capteurs)",
        "extract":    "etl.pipelines.pmac.extract",
        "transform":  "etl.pipelines.pmac.transform",
        "load":       "etl.pipelines.pmac.load",
    },
    "pcwin": {
        "description": "Mesures PCWIN (SQL Server)",
        "extract":    "etl.pipelines.pcwin.extract",
        "transform":  "etl.pipelines.pcwin.transform",
        "load":       "etl.pipelines.pcwin.load",
    },
    "rendements": {
        "description": "Rendements par étage",
        "extract":    "etl.pipelines.rendements.extract",
        "transform":  "etl.pipelines.rendements.transform",
        "load":       "etl.pipelines.rendements.load",
    },
    "gstcom": {
        "description": "Clientèle & Consommations GSTCOM",
        "extract":    "etl.pipelines.gstcom.extract",
        "transform":  "etl.pipelines.gstcom.transform",
        "load":       "etl.pipelines.gstcom.load",
    },
}


CHECKS = {
    "indicateurs_reclamations": [
        "etl.setup.checks.check_bronze_excel",
        "etl.setup.checks.check_silver_excel",
        "etl.setup.checks.check_gold_excel",
    ],
    "pmac": [
        "etl.setup.checks.check_bronze_pmac",
        "etl.setup.checks.check_silver_pmac",
        "etl.setup.checks.check_gold_pmac",
    ],
    "pcwin": [
        "etl.setup.checks.check_bronze_pcwin",
        "etl.setup.checks.check_silver_pcwin",
        "etl.setup.checks.check_gold_pcwin",
    ],
    "gstcom": [
        "etl.setup.checks.check_gold_gstcom",
    ],
    "rendements": [
        "etl.setup.checks.check_gold_rendements",
    ],
}


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _run_module(module_path: str) -> dict:
    """Exécute un module Python et retourne son résultat."""
    import importlib
    
    start = time.time()
    try:
        module = importlib.import_module(module_path)
        
        # Tenter run_extract/run_transform/run_load
        result = None
        for func_name in ["run_extract", "run_transform", "run_load", "main"]:
            if hasattr(module, func_name):
                result = getattr(module, func_name)()
                break
        
        duration = time.time() - start
        return {
            "status": "success",
            "duration_sec": round(duration, 2),
            "result": result,
        }
    except Exception as e:
        duration = time.time() - start
        logger.error(f"❌ {module_path} : {e}", exc_info=True)
        return {
            "status": "error",
            "duration_sec": round(duration, 2),
            "error": str(e),
        }


def _run_pipeline(name: str, config: dict) -> dict:
    """Exécute un pipeline complet (Extract → Transform → Load)."""
    logger.info("=" * 70)
    logger.info(f"🚀 PIPELINE : {name.upper()}")
    logger.info(f"   {config['description']}")
    logger.info("=" * 70)
    
    results = {}
    
    for step in ["extract", "transform", "load"]:
        module_path = config[step]
        logger.info(f"\n▶️  Étape : {step.upper()}")
        
        result = _run_module(module_path)
        results[step] = result
        
        if result["status"] == "error":
            logger.error(f"❌ Pipeline {name} interrompu à l'étape {step}")
            break
        
        logger.info(f"✅ {step.upper()} terminé en {result['duration_sec']}s")
    
    return results


def _run_checks(source: str) -> dict:
    """Lance les checks pour une source."""
    if source not in CHECKS:
        logger.warning(f"⚠️  Aucun check défini pour '{source}'")
        return {}
    
    logger.info(f"\n🔎 CHECKS : {source.upper()}")
    logger.info("-" * 70)
    
    results = {}
    for check_module in CHECKS[source]:
        logger.info(f"\n▶️  {check_module}")
        result = _run_module(check_module)
        results[check_module] = result
    
    return results


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Orchestration séquentielle des pipelines ETL SRM"
    )
    parser.add_argument(
        "--source",
        choices=list(PIPELINES.keys()),
        help="Exécuter uniquement ce pipeline",
    )
    parser.add_argument(
        "--skip",
        action="append",
        choices=list(PIPELINES.keys()),
        help="Exclure ce pipeline (peut être utilisé plusieurs fois)",
    )
    parser.add_argument(
        "--checks-only",
        action="store_true",
        help="Lancer uniquement les scripts de vérification",
    )
    parser.add_argument(
        "--no-checks",
        action="store_true",
        help="Ne pas lancer les checks après les pipelines",
    )
    
    args = parser.parse_args()
    skip = set(args.skip or [])
    
    start_time = datetime.now()
    logger.info("=" * 70)
    logger.info("🎯 EXÉCUTION FULL PIPELINE SRM SOUSS-MASSA")
    logger.info(f"   Démarré à : {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)
    
    all_results = {}
    
    # Déterminer les pipelines à exécuter
    if args.source:
        pipelines_to_run = [args.source]
    else:
        pipelines_to_run = [p for p in PIPELINES.keys() if p not in skip]
    
    logger.info(f"📋 Pipelines à exécuter : {pipelines_to_run}")
    
    # 1. Exécution des pipelines (sauf si checks-only)
    if not args.checks_only:
        for name in pipelines_to_run:
            all_results[name] = _run_pipeline(name, PIPELINES[name])
    
    # 2. Checks
    if not args.no_checks:
        logger.info("\n" + "=" * 70)
        logger.info("🔎 EXÉCUTION DES VÉRIFICATIONS")
        logger.info("=" * 70)
        
        for name in pipelines_to_run:
            if name in CHECKS:
                _run_checks(name)
    
    # 3. Résumé final
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    logger.info("\n" + "=" * 70)
    logger.info("📊 RÉSUMÉ FINAL")
    logger.info("=" * 70)
    logger.info(f"Durée totale : {duration:.1f}s ({duration/60:.1f} min)")
    
    if all_results:
        for pipeline, steps in all_results.items():
            errors = [s for s, r in steps.items() if r.get("status") == "error"]
            if errors:
                logger.error(f"❌ {pipeline} : erreurs à l'étape(s) {errors}")
            else:
                logger.info(f"✅ {pipeline} : OK")
    
    logger.info("=" * 70)


if __name__ == "__main__":
    main()