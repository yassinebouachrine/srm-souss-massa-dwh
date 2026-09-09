# scripts/init_passwords.py
"""
Script d'initialisation des utilisateurs avec la base de données NORMALISÉE.
Usage : python scripts/init_passwords.py
"""
import sys
import os

# Ajout du répertoire streamlit_app au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bcrypt
from db.connection import execute_insert
from config.settings import print_config_summary

DEFAULT_PASSWORD = "SRM2024!"

def hash_password(password: str) -> str:
    """Hash bcrypt avec cost=12."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def init_users():
    print_config_summary()
    print("\n🔐 Initialisation des utilisateurs (Modèle Normalisé 3NF)...\n")

    password_hash = hash_password(DEFAULT_PASSWORD)

    # RAPPEL des Rôles (id_role) :
    # 1: agent_dp | 2: admin_dp | 3: admin_regional | 4: super_admin
    # RAPPEL des Provinces (id_province) :
    # 1: Tata | 2: Tiznit | 3: Chtouka | 4: Taroudant | 5: Inezgane | 6: Agadir

    users = [
        # (username, password_hash, nom_complet, email, id_role, id_province)
        
        # ─── Agents DP (6 provinces) ───
        ("agent_dp_tata",       password_hash, "Agent DP Tata",                 "agent.tata@srm-sm.ma",       1, 1),
        ("agent_dp_tiznit",     password_hash, "Agent DP Tiznit",               "agent.tiznit@srm-sm.ma",     1, 2),
        ("agent_dp_chtouka",    password_hash, "Agent DP Chtouka",              "agent.chtouka@srm-sm.ma",    1, 3),
        ("agent_dp_taroudant",  password_hash, "Agent DP Taroudant",            "agent.taroudant@srm-sm.ma",  1, 4),
        ("agent_dp_inezgane",   password_hash, "Agent DP Inezgane",             "agent.inezgane@srm-sm.ma",   1, 5),
        ("agent_dp_agadir",     password_hash, "Agent DP Agadir",               "agent.agadir@srm-sm.ma",     1, 6),

        # ─── Admins DP (6 provinces) ───
        ("admin_dp_tata",       password_hash, "Admin DP Tata",                 "admin.tata@srm-sm.ma",       2, 1),
        ("admin_dp_tiznit",     password_hash, "Admin DP Tiznit",               "admin.tiznit@srm-sm.ma",     2, 2),
        ("admin_dp_chtouka",    password_hash, "Admin DP Chtouka",              "admin.chtouka@srm-sm.ma",    2, 3),
        ("admin_dp_taroudant",  password_hash, "Admin DP Taroudant",            "admin.taroudant@srm-sm.ma",  2, 4),
        ("admin_dp_inezgane",   password_hash, "Admin DP Inezgane",             "admin.inezgane@srm-sm.ma",   2, 5),
        ("admin_dp_agadir",     password_hash, "Admin DP Agadir",               "admin.agadir@srm-sm.ma",     2, 6),

        # ─── Admin Régional et Super Admin (Sans province -> NULL) ───
        ("admin_regional",      password_hash, "Admin Régional Souss-Massa",    "admin.regional@srm-sm.ma",   3, None),
        ("super_admin",         password_hash, "Super Administrateur",          "superadmin@srm-sm.ma",       4, None),
    ]

    ok, err = 0, 0
    for u in users:
        try:
            execute_insert(
                """
                INSERT INTO app_auth.utilisateurs
                    (username, password_hash, nom_complet, email, id_role, id_province)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (username) DO UPDATE
                SET password_hash = EXCLUDED.password_hash,
                    date_modification = CURRENT_TIMESTAMP
                """,
                u,
            )
            print(f"  ✅  {u[0]:25s} | Rôle ID: {u[4]} | Prov ID: {u[5] or 'SIEGE'}")
            ok += 1
        except Exception as e:
            print(f"  ❌  {u[0]:25s} | Erreur : {e}")
            err += 1

    print(f"\n{'─' * 60}")
    print(f"  ✅  {ok} utilisateurs créés / mis à jour")
    if err:
        print(f"  ❌  {err} erreurs")
    print(f"{'─' * 60}\n")

if __name__ == "__main__":
    init_users()