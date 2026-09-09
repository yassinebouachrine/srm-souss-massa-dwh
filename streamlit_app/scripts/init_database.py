# streamlit_app/scripts/init_database.py
"""
Initialise complètement la base de données Streamlit (Modèle Normalisé).
Exécute tous les DDL puis tous les DML dans l'ordre.
"""
import sys
from pathlib import Path

# Ajouter la racine au path
STREAMLIT_APP = Path(__file__).resolve().parent.parent
PROJECT_ROOT = STREAMLIT_APP.parent
sys.path.insert(0, str(STREAMLIT_APP))

from db.connection import execute_query, get_connection

DDL_DIR = PROJECT_ROOT / "database" / "ddl"
DML_DIR = PROJECT_ROOT / "database" / "dml"


# ═══════════════════════════════════════════════════════════════
# ORDRE D'EXÉCUTION STRICT (crucial pour les clés étrangères)
# ═══════════════════════════════════════════════════════════════
DDL_ORDER = [
    "00_create_schemas.sql",
    "01_reference_tables.sql",       # ref_role, ref_province, ref_centre, ref_periode, ref_type_*, ref_motif_rejet
    "02_auth_tables.sql",            # utilisateurs, sessions, password_reset, audit_logs
    "03_saisie_tables.sql",          # lot_saisie, donnee_saisie, saisie_*
    "03b_vues_saisie.sql",           # v_lot_statut_calcule
    "04_validation_corrections.sql", # validation, correction, detail_correction
    "05_transfert_agent.sql",
    "06_fix_validation_history.sql", 
    "07_demande_modification.sql", 
    "08_security_enterprise.sql",

]

DML_ORDER = [
    "00_seed_nouveaux_referentiels.sql",  # roles, periodes, motifs_rejet
    "01_seed_provinces.sql",
    "02_seed_centres.sql",
    "03_seed_types_indicateurs.sql",
    "04_seed_types_reclamations.sql",
]


def run_sql_file(filepath: Path) -> bool:
    """Exécute un fichier SQL."""
    if not filepath.exists():
        print(f"   ❌ Introuvable : {filepath.name}")
        return False

    try:
        sql = filepath.read_text(encoding="utf-8")
        if not sql.strip():
            print(f"   ⚠️  Vide")
            return True

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
    print("  SRM Souss-Massa — Initialisation base (Modèle Normalisé 3NF)")
    print("=" * 70)

    # ─── DDL ───
    print("\n📁 DDL (structure) :")
    for filename in DDL_ORDER:
        filepath = DDL_DIR / filename
        print(f"\n▶️  {filename}")
        if not run_sql_file(filepath):
            print(f"\n❌ Arrêt sur erreur : {filename}")
            return

    # ─── DML ───
    print("\n\n📁 DML (données de référence) :")
    for filename in DML_ORDER:
        filepath = DML_DIR / filename
        print(f"\n▶️  {filename}")
        if not run_sql_file(filepath):
            print(f"⚠️  Continue malgré l'erreur...")

    # ─── Vérifications ───
    print("\n\n" + "=" * 70)
    print("  Vérifications")
    print("=" * 70)

    checks = [
        ("Rôles",              "SELECT COUNT(*) c FROM app_auth.ref_role",                   4),
        ("Provinces",          "SELECT COUNT(*) c FROM app_staging.ref_province",            6),
        ("Centres",            "SELECT COUNT(*) c FROM app_staging.ref_centre",             68),
        ("Périodes",           "SELECT COUNT(*) c FROM app_staging.ref_periode",            84),  # 7 ans × 12 mois
        ("Types indicateurs",  "SELECT COUNT(*) c FROM app_staging.ref_type_indicateur",    21),
        ("Types réclamations", "SELECT COUNT(*) c FROM app_staging.ref_type_reclamation",   10),
        ("Motifs de rejet",    "SELECT COUNT(*) c FROM app_staging.ref_motif_rejet",         6),
    ]

    all_ok = True
    for label, query, expected in checks:
        try:
            result = execute_query(query, fetch="one")
            count = result["c"] if result else 0
            status = "✅" if count >= expected else "⚠️ "
            if count < expected:
                all_ok = False
            print(f"  {status}  {label:22s} : {count:>3} (attendu ≥ {expected})")
        except Exception as e:
            all_ok = False
            print(f"  ❌  {label:22s} : {e}")

    # ─── Vérification des tables (structure) ───
    print("\n📋 Tables créées :")
    tables_expected = {
        "app_auth": ["ref_role", "utilisateurs", "sessions", "password_reset_tokens", "audit_logs"],
        "app_staging": [
            "ref_province", "ref_centre", "ref_periode",
            "ref_type_indicateur", "ref_type_reclamation",
            "lot_saisie", "donnee_saisie",
            "saisie_indicateur", "saisie_reclamation", "saisie_reclamation_libre",
            "validation", "correction", "detail_correction"
        ],
    }

    for schema, tables in tables_expected.items():
        result = execute_query(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = %s",
            (schema,)
        )
        existing = {r["table_name"] for r in (result or [])}
        for t in tables:
            status = "✅" if t in existing else "❌"
            print(f"  {status}  {schema}.{t}")
            if t not in existing:
                all_ok = False

    # ─── Résumé ───
    print("\n" + "=" * 70)
    if all_ok:
        print("  ✅  Base initialisée avec succès !")
    else:
        print("  ⚠️  Base initialisée avec des avertissements.")
    print("=" * 70)

    print("\n🚀 Prochaine étape :")
    print("   python scripts/init_passwords.py    # Créer les utilisateurs")
    print("   streamlit run app.py                # Lancer l'app\n")


if __name__ == "__main__":
    init_database()