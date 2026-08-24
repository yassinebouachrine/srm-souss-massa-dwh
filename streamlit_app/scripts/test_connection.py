# scripts/test_connection.py
"""
Script de test de connexion à la base de données.
Usage : python scripts/test_connection.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import DB_CONFIG, print_config_summary
import psycopg2


def test_connection():
    print_config_summary()
    print("\n🔌  Test de connexion PostgreSQL...\n")

    try:
        conn = psycopg2.connect(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            database=DB_CONFIG["database"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
        )
        cur = conn.cursor()

        # Version PostgreSQL
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print(f"  ✅  Connexion réussie")
        print(f"  📦  {version.split(',')[0]}")

        # Schémas existants
        cur.execute("""
            SELECT schema_name FROM information_schema.schemata
            WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
            ORDER BY schema_name;
        """)
        schemas = [r[0] for r in cur.fetchall()]
        print(f"\n  📁  Schémas disponibles ({len(schemas)}) :")
        for s in schemas:
            marker = "  ⭐" if s in ("app_auth", "app_staging", "gold") else "    "
            print(f"    {marker}  {s}")

        # Test présence des tables app_auth
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'app_auth';
        """)
        auth_tables = [r[0] for r in cur.fetchall()]
        print(f"\n  🔐  Tables app_auth : {auth_tables or 'AUCUNE — Exécutez le DDL !'}")

        # Test présence des tables app_staging
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'app_staging';
        """)
        staging_tables = [r[0] for r in cur.fetchall()]
        print(f"  📥  Tables app_staging : {staging_tables or 'AUCUNE — Exécutez le DDL !'}")

        # Nombre d'utilisateurs si table existe
        if "utilisateurs" in auth_tables:
            cur.execute("SELECT COUNT(*) FROM app_auth.utilisateurs;")
            count = cur.fetchone()[0]
            print(f"\n  👥  Utilisateurs enregistrés : {count}")
            if count == 0:
                print(f"    ⚠️   Exécutez : python scripts/init_passwords.py")

        cur.close()
        conn.close()
        print(f"\n  ✅  Tout est OK !\n")
        return True

    except psycopg2.OperationalError as e:
        print(f"  ❌  Erreur de connexion :")
        print(f"      {e}")
        print(f"\n  🔧  Vérifiez :")
        print(f"      - PostgreSQL est démarré (service Windows)")
        print(f"      - La base '{DB_CONFIG['database']}' existe")
        print(f"      - Les identifiants dans le .env sont corrects")
        return False
    except Exception as e:
        print(f"  ❌  Erreur : {e}")
        return False


if __name__ == "__main__":
    test_connection()