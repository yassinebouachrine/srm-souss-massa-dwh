"""
Script de restructuration du projet SRM Souss-Massa DWH
Réorganise la structure de dossiers pour la mettre en conformité avec
la structure cible professionnelle.

⚠️ IMPORTANT : Exécuter en mode dry-run d'abord pour vérifier !

Usage :
    python scripts/restructure_project.py --dry-run   # Simulation
    python scripts/restructure_project.py             # Exécution réelle
    python scripts/restructure_project.py --backup    # Avec sauvegarde préalable
"""
import argparse
import shutil
from pathlib import Path
from datetime import datetime
import sys

# Racine du projet
PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ═══════════════════════════════════════════════════════════════
# CONFIGURATION DES OPÉRATIONS
# ═══════════════════════════════════════════════════════════════

# Nouveaux dossiers à créer
NEW_FOLDERS = [
    # Database
    "database/views",
    "database/migrations",
    
    # ETL - réorganisation setup
    "etl/setup/initialization",
    "etl/setup/checks",
    
    # Airflow
    "airflow/dags",
    "airflow/plugins",
    "airflow/logs",
    
    # Docker
    "docker",
    
    # Documentation
    "docs/architecture",
    "docs/architecture/diagrammes",
    "docs/deployment",
    "docs/exploitation",
    "docs/rapport_pfa",
    
    # Power BI
    "powerbi/datasets",
    "powerbi/mesures_dax",
    
    # Scripts
    "scripts",
]


# Renommage / déplacement de dossiers
FOLDER_MOVES = [
    # Renommer le dossier PMAC pour homogénéité
    ("data/raw/Dossier Export Données PMAC", "data/raw/pmac"),
]


# Déplacement de fichiers (par pattern)
# Format : (source_glob, destination_folder)
FILE_MOVES = [
    # Scripts d'initialisation
    ("etl/setup/generate_dim_temps.py",              "etl/setup/initialization/"),
    ("etl/setup/seed_dim_point_mesure.py",           "etl/setup/initialization/"),
    ("etl/setup/seed_dim_point_mesure_pcwin.py",     "etl/setup/initialization/"),
    ("etl/setup/seed_dim_canal_label.py",            "etl/setup/initialization/"),
    ("etl/setup/seed_bridge_groupe_point_pcwin.py",  "etl/setup/initialization/"),
    ("etl/setup/seed_dim_loc_sec_bridge.py",         "etl/setup/initialization/"),
    ("etl/setup/update_dim_etage_lineaire.py",       "etl/setup/initialization/"),
    ("etl/setup/update_dim_secteur_lineaire.py",     "etl/setup/initialization/"),
    
    # Scripts de check/diagnostic
    ("etl/setup/check_bronze_excel.py",              "etl/setup/checks/"),
    ("etl/setup/check_bronze_pmac.py",               "etl/setup/checks/"),
    ("etl/setup/check_bronze_pcwin.py",              "etl/setup/checks/"),
    ("etl/setup/check_bronze_streamlit.py",          "etl/setup/checks/"),
    ("etl/setup/check_silver_excel.py",              "etl/setup/checks/"),
    ("etl/setup/check_silver_pmac.py",               "etl/setup/checks/"),
    ("etl/setup/check_silver_pcwin.py",              "etl/setup/checks/"),
    ("etl/setup/check_silver_streamlit.py",          "etl/setup/checks/"),
    ("etl/setup/check_gold_excel.py",                "etl/setup/checks/"),
    ("etl/setup/check_gold_pmac.py",                 "etl/setup/checks/"),
    ("etl/setup/check_gold_pcwin.py",                "etl/setup/checks/"),
    ("etl/setup/check_gold_streamlit.py",            "etl/setup/checks/"),
    ("etl/setup/check_referentiels_pcwin.py",        "etl/setup/checks/"),
    ("etl/setup/diagnostic_doublons_pmac.py",        "etl/setup/checks/"),
    ("etl/setup/diagnostic_voies_pmac.py",           "etl/setup/checks/"),
]


# Fichiers à déplacer depuis un sous-dossier (récursif)
FOLDER_CONTENT_MOVES = [
    # Si le sous-dossier test_valider_partie existe, déplacer son contenu vers checks/
    ("etl/setup/test_valider_partie", "etl/setup/checks/"),
]


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def log_info(msg, color=Colors.BLUE):
    print(f"{color}{msg}{Colors.END}")


def log_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.END}")


def log_warning(msg):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.END}")


def log_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.END}")


def log_action(msg, dry_run=False):
    prefix = "[DRY-RUN] " if dry_run else ""
    print(f"{Colors.CYAN}{prefix}{msg}{Colors.END}")


# ═══════════════════════════════════════════════════════════════
# OPÉRATIONS
# ═══════════════════════════════════════════════════════════════

def create_folders(dry_run=False):
    """Crée les nouveaux dossiers avec .gitkeep."""
    log_info("\n📁 CRÉATION DES NOUVEAUX DOSSIERS", Colors.BOLD)
    log_info("-" * 60)
    
    created = 0
    for folder in NEW_FOLDERS:
        folder_path = PROJECT_ROOT / folder
        
        if folder_path.exists():
            log_warning(f"Existe déjà : {folder}")
            continue
        
        log_action(f"Créer : {folder}", dry_run)
        
        if not dry_run:
            folder_path.mkdir(parents=True, exist_ok=True)
            # Ajouter .gitkeep pour git
            (folder_path / ".gitkeep").touch()
        
        created += 1
    
    log_success(f"{created} dossiers créés")


def rename_folders(dry_run=False):
    """Renomme/déplace des dossiers."""
    log_info("\n📂 RENOMMAGE DE DOSSIERS", Colors.BOLD)
    log_info("-" * 60)
    
    renamed = 0
    for src, dst in FOLDER_MOVES:
        src_path = PROJECT_ROOT / src
        dst_path = PROJECT_ROOT / dst
        
        if not src_path.exists():
            log_warning(f"Source introuvable : {src}")
            continue
        
        if dst_path.exists():
            log_warning(f"Destination existe déjà : {dst} - fusion...")
            if not dry_run:
                # Fusionner : déplacer contenu
                for item in src_path.iterdir():
                    target = dst_path / item.name
                    if not target.exists():
                        shutil.move(str(item), str(target))
                # Supprimer dossier source vide
                if not any(src_path.iterdir()):
                    src_path.rmdir()
            continue
        
        log_action(f"Renommer : {src} → {dst}", dry_run)
        
        if not dry_run:
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_path), str(dst_path))
        
        renamed += 1
    
    log_success(f"{renamed} dossiers renommés")


def move_files(dry_run=False):
    """Déplace les fichiers Python selon FILE_MOVES."""
    log_info("\n📄 DÉPLACEMENT DE FICHIERS", Colors.BOLD)
    log_info("-" * 60)
    
    moved = 0
    for src, dst_folder in FILE_MOVES:
        src_path = PROJECT_ROOT / src
        dst_folder_path = PROJECT_ROOT / dst_folder
        
        if not src_path.exists():
            log_warning(f"Introuvable : {src}")
            continue
        
        dst_path = dst_folder_path / src_path.name
        
        if dst_path.exists():
            log_warning(f"Destination existe déjà : {dst_folder}{src_path.name}")
            continue
        
        log_action(f"Déplacer : {src} → {dst_folder}{src_path.name}", dry_run)
        
        if not dry_run:
            dst_folder_path.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_path), str(dst_path))
        
        moved += 1
    
    log_success(f"{moved} fichiers déplacés")


def move_folder_contents(dry_run=False):
    """Déplace tout le contenu d'un sous-dossier vers un autre."""
    log_info("\n📦 DÉPLACEMENT DE CONTENU DE SOUS-DOSSIERS", Colors.BOLD)
    log_info("-" * 60)
    
    total = 0
    for src_folder, dst_folder in FOLDER_CONTENT_MOVES:
        src_path = PROJECT_ROOT / src_folder
        dst_path = PROJECT_ROOT / dst_folder
        
        if not src_path.exists() or not src_path.is_dir():
            log_warning(f"Dossier source introuvable : {src_folder}")
            continue
        
        moved = 0
        for item in src_path.iterdir():
            if item.name.startswith("."):
                continue  # skip .gitkeep, .pyc
            
            target = dst_path / item.name
            if target.exists():
                log_warning(f"Destination existe déjà : {target.relative_to(PROJECT_ROOT)}")
                continue
            
            log_action(f"Déplacer : {item.relative_to(PROJECT_ROOT)} → {dst_folder}", dry_run)
            
            if not dry_run:
                dst_path.mkdir(parents=True, exist_ok=True)
                shutil.move(str(item), str(target))
            
            moved += 1
        
        total += moved
        
        # Supprimer dossier source s'il est vide (sauf __pycache__)
        if not dry_run and src_path.exists():
            remaining = [f for f in src_path.iterdir() if not f.name.startswith(".") and f.name != "__pycache__"]
            if not remaining:
                # Nettoyer __pycache__ et supprimer
                pycache = src_path / "__pycache__"
                if pycache.exists():
                    shutil.rmtree(pycache)
                # Retirer .gitkeep
                gitkeep = src_path / ".gitkeep"
                if gitkeep.exists():
                    gitkeep.unlink()
                # Supprimer dossier vide
                if not any(src_path.iterdir()):
                    src_path.rmdir()
                    log_success(f"Dossier vide supprimé : {src_folder}")
        
    log_success(f"{total} éléments déplacés")


def create_init_files(dry_run=False):
    """Crée les __init__.py manquants dans les dossiers Python."""
    log_info("\n🐍 CRÉATION DES __init__.py", Colors.BOLD)
    log_info("-" * 60)
    
    python_folders = [
        "etl/setup/initialization",
        "etl/setup/checks",
        "scripts",
    ]
    
    created = 0
    for folder in python_folders:
        folder_path = PROJECT_ROOT / folder
        if not folder_path.exists():
            continue
        
        init_file = folder_path / "__init__.py"
        if init_file.exists():
            continue
        
        log_action(f"Créer : {folder}/__init__.py", dry_run)
        
        if not dry_run:
            init_file.touch()
        
        created += 1
    
    log_success(f"{created} fichiers __init__.py créés")


def create_backup(dry_run=False):
    """Crée un backup complet du projet."""
    if dry_run:
        log_info("\n💾 BACKUP", Colors.BOLD)
        log_action("Backup ignoré (dry-run)", dry_run=True)
        return
    
    log_info("\n💾 CRÉATION DU BACKUP", Colors.BOLD)
    log_info("-" * 60)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"backup_before_restructure_{timestamp}"
    backup_path = PROJECT_ROOT.parent / backup_name
    
    log_action(f"Backup vers : {backup_path}")
    
    # Copier en excluant venv, data, __pycache__
    ignore = shutil.ignore_patterns(
        "venv", ".venv", "env", "__pycache__", "*.pyc",
        "data/bronze/*", "data/silver/*", "data/rejects/*", "data/logs/*",
        ".git",
    )
    
    try:
        shutil.copytree(PROJECT_ROOT, backup_path, ignore=ignore)
        log_success(f"Backup créé : {backup_path}")
    except Exception as e:
        log_error(f"Backup échoué : {e}")
        sys.exit(1)


def print_summary(dry_run=False):
    """Affiche un résumé après restructuration."""
    log_info("\n" + "=" * 60, Colors.BOLD)
    log_info("📊 RÉSUMÉ DE LA RESTRUCTURATION", Colors.BOLD)
    log_info("=" * 60, Colors.BOLD)
    
    mode = "DRY-RUN (simulation)" if dry_run else "EXÉCUTION RÉELLE"
    log_info(f"Mode : {mode}")
    log_info(f"Projet : {PROJECT_ROOT}")
    
    if dry_run:
        log_warning("\nAucune modification n'a été effectuée.")
        log_info("Pour appliquer les changements, relancez sans --dry-run :")
        log_info(f"  python scripts/restructure_project.py", Colors.GREEN)
    else:
        log_success("\nRestructuration terminée avec succès !")
        log_info("\n🎯 Prochaines étapes :")
        log_info("  1. Vérifier la nouvelle structure : tree /F ou ls -la")
        log_info("  2. Tester les pipelines : make check-all")
        log_info("  3. Committer les changements : git add . && git commit -m 'refactor: restructure project'")


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Restructuration du projet SRM Souss-Massa DWH",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulation sans modification réelle",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Créer un backup avant restructuration",
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Ne pas demander de confirmation",
    )
    
    args = parser.parse_args()
    
    log_info("=" * 60, Colors.BOLD)
    log_info("🔧 RESTRUCTURATION DU PROJET SRM SOUSS-MASSA DWH", Colors.BOLD)
    log_info("=" * 60, Colors.BOLD)
    log_info(f"Racine : {PROJECT_ROOT}")
    log_info(f"Mode   : {'DRY-RUN' if args.dry_run else 'EXÉCUTION RÉELLE'}")
    
    if not args.dry_run and not args.yes:
        response = input("\n⚠️  Confirmer l'exécution ? (y/N) : ").strip().lower()
        if response != "y":
            log_warning("Annulé par l'utilisateur")
            sys.exit(0)
    
    # Backup si demandé
    if args.backup:
        create_backup(dry_run=args.dry_run)
    
    # Étapes de restructuration
    create_folders(dry_run=args.dry_run)
    rename_folders(dry_run=args.dry_run)
    move_files(dry_run=args.dry_run)
    move_folder_contents(dry_run=args.dry_run)
    create_init_files(dry_run=args.dry_run)
    
    # Résumé
    print_summary(dry_run=args.dry_run)


if __name__ == "__main__":
    main()