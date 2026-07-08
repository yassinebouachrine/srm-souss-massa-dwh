# scripts/init_passwords.py
"""
Script d'initialisation des utilisateurs et de leurs mots de passe.
À exécuter UNE FOIS après avoir créé les tables app_auth.utilisateurs.

Usage :
    cd streamlit_app
    python scripts/init_passwords.py
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
    """Créer les utilisateurs initiaux avec hash bcrypt sécurisés."""
    print_config_summary()
    print("\n🔐 Initialisation des utilisateurs...\n")

    password_hash = hash_password(DEFAULT_PASSWORD)

    users = [
        # ─── Agents DP (6 provinces) ───
        ("agent_dp_tata",       password_hash, "Agent DP Tata",                 "agent.tata@srm-sm.ma",       "agent_dp", 1, "TATA"),
        ("agent_dp_tiznit",     password_hash, "Agent DP Tiznit",               "agent.tiznit@srm-sm.ma",     "agent_dp", 2, "TIZNIT"),
        ("agent_dp_chtouka",    password_hash, "Agent DP Chtouka Ait Baha",     "agent.chtouka@srm-sm.ma",    "agent_dp", 3, "CHTOUKA"),
        ("agent_dp_taroudant",  password_hash, "Agent DP Taroudant",            "agent.taroudant@srm-sm.ma",  "agent_dp", 4, "TAROUDANT"),
        ("agent_dp_inezgane",   password_hash, "Agent DP Inezgane Ait Melloul", "agent.inezgane@srm-sm.ma",   "agent_dp", 5, "INEZGANE"),
        ("agent_dp_agadir",     password_hash, "Agent DP Agadir",               "agent.agadir@srm-sm.ma",     "agent_dp", 6, "AGADIR"),

        # ─── Admins DP (6 provinces) ───
        ("admin_dp_tata",       password_hash, "Admin DP Tata",                 "admin.tata@srm-sm.ma",       "admin_dp", 1, "TATA"),
        ("admin_dp_tiznit",     password_hash, "Admin DP Tiznit",               "admin.tiznit@srm-sm.ma",     "admin_dp", 2, "TIZNIT"),
        ("admin_dp_chtouka",    password_hash, "Admin DP Chtouka Ait Baha",     "admin.chtouka@srm-sm.ma",    "admin_dp", 3, "CHTOUKA"),
        ("admin_dp_taroudant",  password_hash, "Admin DP Taroudant",            "admin.taroudant@srm-sm.ma",  "admin_dp", 4, "TAROUDANT"),
        ("admin_dp_inezgane",   password_hash, "Admin DP Inezgane Ait Melloul", "admin.inezgane@srm-sm.ma",   "admin_dp", 5, "INEZGANE"),
        ("admin_dp_agadir",     password_hash, "Admin DP Agadir",               "admin.agadir@srm-sm.ma",     "admin_dp", 6, "AGADIR"),

        # ─── Admin Régional (siège Agadir) ───
        ("admin_regional",      password_hash, "Administrateur Régional Souss-Massa", "admin.regional@srm-sm.ma", "admin_regional", None, None),

        # ─── Super Admin ───
        ("super_admin",         password_hash, "Super Administrateur",          "superadmin@srm-sm.ma",       "super_admin", None, None),
    ]

    ok, err = 0, 0
    for u in users:
        try:
            execute_insert(
                """
                INSERT INTO app_auth.utilisateurs
                    (username, password_hash, nom_complet, email, role, id_province, code_province)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (username) DO UPDATE
                SET password_hash = EXCLUDED.password_hash,
                    date_modification = CURRENT_TIMESTAMP
                """,
                u,
            )
            print(f"  ✅  {u[0]:25s}  {u[4]:20s}  ({u[6] or 'REGIONAL'})")
            ok += 1
        except Exception as e:
            print(f"  ❌  {u[0]:25s}  Erreur : {e}")
            err += 1

    print(f"\n{'─' * 60}")
    print(f"  ✅  {ok} utilisateurs créés / mis à jour")
    if err:
        print(f"  ❌  {err} erreurs")
    print(f"{'─' * 60}")
    print(f"  🔑  Mot de passe par défaut : {DEFAULT_PASSWORD}")
    print(f"  ⚠️   Changez-le après la première connexion !")
    print(f"{'─' * 60}\n")


if __name__ == "__main__":
    init_users()