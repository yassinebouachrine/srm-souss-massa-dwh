# streamlit_app/scripts/init_database.py
"""Initialise complètement la base de données Streamlit."""
import sys
import os
from pathlib import Path

# Ajouter la racine au path
STREAMLIT_APP = Path(__file__).resolve().parent.parent
PROJECT_ROOT = STREAMLIT_APP.parent
sys.path.insert(0, str(STREAMLIT_APP))

from db.connection import execute_query

DDL_DIR = PROJECT_ROOT / "database" / "ddl"
DML_DIR = PROJECT_ROOT / "database" / "dml"


def run_sql_file(filepath: Path) -> bool:
    """Exécute un fichier SQL."""
    if not filepath.exists():
        print(f"   ❌ Introuvable : {filepath}")
        return False

    try:
        sql = filepath.read_text(encoding="utf-8")
        if not sql.strip():
            print(f"   ⚠️  Fichier vide")
            return True

        # Utiliser execute_query pour du SQL brut
        from db.connection import get_connection
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                conn.commit()

        size = filepath.stat().st_size
        print(f"   ✅ OK ({size:,} octets)")
        return True
    except Exception as e:
        print(f"   ❌ Erreur : {e}")
        return False


def init_database():
    print("=" * 70)
    print("  SRM Souss-Massa — Initialisation base Streamlit")
    print("=" * 70)

    # DDL
    print("\n📁 DDL (structure) :")
    ddl_files = sorted(DDL_DIR.glob("*.sql"))
    for f in ddl_files:
        print(f"\n▶️  {f.name}")
        run_sql_file(f)

    # DML
    print("\n\n📁 DML (données) :")
    dml_files = sorted(DML_DIR.glob("*.sql"))
    for f in dml_files:
        print(f"\n▶️  {f.name}")
        run_sql_file(f)

    # Vérifications
    print("\n\n" + "=" * 70)
    print("  Vérifications")
    print("=" * 70)

    checks = [
        ("Provinces", "SELECT COUNT(*) as c FROM app_staging.ref_province", 6),
        ("Centres", "SELECT COUNT(*) as c FROM app_staging.ref_centre", 68),
        ("Types indicateurs", "SELECT COUNT(*) as c FROM app_staging.ref_type_indicateur", 21),
        ("Types réclamations", "SELECT COUNT(*) as c FROM app_staging.ref_type_reclamation", 10),
    ]

    for label, query, expected in checks:
        try:
            result = execute_query(query, fetch="one")
            count = result["c"] if result else 0
            status = "✅" if count >= expected else "⚠️ "
            print(f"  {status}  {label:25s} : {count:>3} (attendu ≥ {expected})")
        except Exception as e:
            print(f"  ❌  {label:25s} : {e}")

    print("\n✅ Initialisation terminée !")
    print("\n🚀 Prochaine étape :")
    print("   cd streamlit_app")
    print("   python scripts\\init_passwords.py    # Créer les utilisateurs")
    print("   streamlit run app.py                # Lancer l'app")


if __name__ == "__main__":
    init_database()