"""
Test de connexion PostgreSQL
Verifie que la base srm_datawarehouse est accessible
"""

import psycopg2
from dotenv import load_dotenv
import os
import sys

load_dotenv()


def test_connection():
    """Tester la connexion PostgreSQL"""
    print("=" * 60)
    print("SRM Souss-Massa - Test de Connexion PostgreSQL")
    print("=" * 60)
    print()
    
    try:
        print("Tentative de connexion...")
        print(f"   Host     : {os.getenv('POSTGRES_HOST')}")
        print(f"   Port     : {os.getenv('POSTGRES_PORT')}")
        print(f"   Database : {os.getenv('POSTGRES_DB')}")
        print(f"   User     : {os.getenv('POSTGRES_USER')}")
        print()
        
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST"),
            port=os.getenv("POSTGRES_PORT"),
            database=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD")
        )
        
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        
        cur.execute("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
            ORDER BY schema_name;
        """)
        schemas = [row[0] for row in cur.fetchall()]
        
        cur.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema');
        """)
        nb_tables = cur.fetchone()[0]
        
        print("CONNEXION REUSSIE !")
        print()
        print(f"Version PostgreSQL :")
        print(f"   {version[:70]}...")
        print()
        print(f"Schemas existants  : {', '.join(schemas)}")
        print(f"Nombre de tables   : {nb_tables}")
        
        cur.close()
        conn.close()
        
        print()
        print("=" * 60)
        return True
        
    except psycopg2.OperationalError as e:
        print(f"ERREUR DE CONNEXION")
        print(f"   {e}")
        print()
        print("Verifications :")
        print("   1. PostgreSQL est-il demarre ?")
        print("   2. Le mot de passe dans .env est-il correct ?")
        print("   3. La base srm_datawarehouse existe-t-elle ?")
        print("=" * 60)
        return False
        
    except Exception as e:
        print(f"ERREUR : {e}")
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
