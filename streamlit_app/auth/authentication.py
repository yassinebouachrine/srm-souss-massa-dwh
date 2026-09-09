# auth/authentication.py
"""
Authentification sécurisée (bcrypt, sessions, audit, reset password).
"""
import bcrypt
import secrets
import hashlib
import logging
import json
from datetime import datetime, timedelta
import streamlit as st

from db.connection import execute_query, execute_insert
from config.settings import MAX_LOGIN_ATTEMPTS, LOCKOUT_DURATION_MINUTES, TOKEN_EXPIRY_HOURS

logger = logging.getLogger(__name__)


def _hash_token(token: str) -> str:
    """Hash SHA-256 du token pour stockage sécurisé en base."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _get_client_info():
    """Récupère l'adresse IP et le User-Agent du client sans inclure le Host/Port."""
    ip = "127.0.0.1"
    user_agent = "Unknown Browser"
    try:
        headers = getattr(st.context, "headers", {})
        # On extrait la vraie IP sans le port ni le header Host
        ip_raw = headers.get("X-Forwarded-For", headers.get("X-Real-Ip", "127.0.0.1"))
        ip = ip_raw.split(",")[0].split(":")[0].strip() or "127.0.0.1"
        user_agent = headers.get("User-Agent", "Unknown Browser")
    except Exception:
        pass
    return ip, user_agent


class AuthManager:
    """Gestionnaire d'authentification (Modèle Normalisé 3NF)."""

    # ═══════════════════════════════════════════════════
    # UTILITAIRES
    # ═══════════════════════════════════════════════════

    @staticmethod
    def hash_password(password: str) -> str:
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except Exception:
            return False

    @staticmethod
    def generate_token() -> str:
        return secrets.token_urlsafe(64)

    # ═══════════════════════════════════════════════════
    # AUDIT (méthode manquante — cause de l'erreur)
    # ═══════════════════════════════════════════════════

    @staticmethod
    def log_action(
        user_id: int,
        action: str,
        table_cible: str = None,
        id_enregistrement: int = None,
        details: dict = None,
    ):
        """Enregistre une action dans app_auth.audit_logs."""
        try:
            execute_insert(
                """
                INSERT INTO app_auth.audit_logs
                    (id_utilisateur, action, table_cible, id_enregistrement, details)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    action,
                    table_cible,
                    id_enregistrement,
                    json.dumps(details) if details else None,
                ),
            )
        except Exception as e:
            logger.error(f"Erreur audit log : {e}")

    # ═══════════════════════════════════════════════════
    # AUTHENTIFICATION
    # ═══════════════════════════════════════════════════

    @staticmethod
    def authenticate(username: str, password: str) -> dict:
        user = execute_query(
            """
            SELECT 
                u.id_utilisateur, u.username, u.password_hash, u.nom_complet, u.email,
                u.id_role, r.code_role, r.libelle_role,
                u.id_province, p.code_province, p.nom_province,
                u.est_actif, u.tentatives_echouees, u.verrouille_jusqua
            FROM app_auth.utilisateurs u
            JOIN app_auth.ref_role r ON u.id_role = r.id_role
            LEFT JOIN app_staging.ref_province p ON u.id_province = p.id_province
            WHERE lower(u.username) = %s
               OR lower(COALESCE(u.email, '')) = %s
            """,
            (username.lower().strip(), username.lower().strip()),
            fetch="one",
        )

        if not user:
            return {"success": False, "message": "Identifiants incorrects."}

        if not user["est_actif"]:
            return {"success": False, "message": "Ce compte a été désactivé. Contactez l'administrateur."}

        if user["verrouille_jusqua"] and user["verrouille_jusqua"] > datetime.now():
            remaining = (user["verrouille_jusqua"] - datetime.now()).seconds // 60
            return {
                "success": False,
                "message": f"Compte verrouillé. Réessayez dans {remaining + 1} minutes.",
            }

        if not AuthManager.verify_password(password, user["password_hash"]):
            return AuthManager._handle_failed_attempt(user)

        return AuthManager._create_session(user)

    @staticmethod
    def _handle_failed_attempt(user: dict) -> dict:
        attempts = user["tentatives_echouees"] + 1
        lock_until = None

        if attempts >= MAX_LOGIN_ATTEMPTS:
            lock_until = datetime.now() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
            logger.warning(f"Compte verrouillé : {user['username']} après {attempts} tentatives")

        execute_insert(
            """
            UPDATE app_auth.utilisateurs
            SET tentatives_echouees = %s, verrouille_jusqua = %s,
                date_modification = CURRENT_TIMESTAMP
            WHERE id_utilisateur = %s
            """,
            (attempts, lock_until, user["id_utilisateur"]),
        )

        remaining = MAX_LOGIN_ATTEMPTS - attempts
        if remaining > 0:
            return {
                "success": False,
                "message": f"Identifiants incorrects. {remaining} tentative(s) restante(s).",
            }
        return {
            "success": False,
            "message": f"Compte verrouillé pour {LOCKOUT_DURATION_MINUTES} minutes.",
        }

    @staticmethod
    def _create_session(user: dict) -> dict:
        token = AuthManager.generate_token()
        token_hash = _hash_token(token)
        sid_public = hashlib.sha256(f"srm-sid-{token}".encode()).hexdigest()[:16]
        expiry = datetime.now() + timedelta(hours=TOKEN_EXPIRY_HOURS)
        ip_addr, user_agent = _get_client_info()

        execute_insert(
            """
            UPDATE app_auth.utilisateurs
            SET tentatives_echouees = 0, verrouille_jusqua = NULL,
                derniere_connexion = CURRENT_TIMESTAMP,
                date_modification = CURRENT_TIMESTAMP
            WHERE id_utilisateur = %s
            """,
            (user["id_utilisateur"],),
        )

        execute_insert(
            """
            INSERT INTO app_auth.sessions
                (id_utilisateur, token_hash, sid_public, date_expiration, est_active, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, TRUE, %s, %s)
            """,
            (user["id_utilisateur"], token_hash, sid_public, expiry, ip_addr, user_agent),
        )

        AuthManager.log_action(
            user["id_utilisateur"], "LOGIN", "utilisateurs", user["id_utilisateur"]
        )

        return {
            "success": True,
            "user": {
                "id": user["id_utilisateur"],
                "username": user["username"],
                "nom_complet": user["nom_complet"],
                "email": user["email"],
                "id_role": user["id_role"],
                "role": user["code_role"],
                "role_libelle": user["libelle_role"],
                "id_province": user["id_province"],
                "code_province": user["code_province"],
                "nom_province": user["nom_province"],
                "token": token,
                "sid_public": sid_public,
            },
        }

    # ═══════════════════════════════════════════════════
    # SESSION / MOT DE PASSE
    # ═══════════════════════════════════════════════════

    @staticmethod
    def validate_session(token: str) -> dict:
        if not token:
            return None
        token_hash = _hash_token(token)
        result = execute_query(
            """
            SELECT 
                s.id_utilisateur, s.date_expiration, s.est_active,
                u.username, u.nom_complet, u.est_actif,
                u.id_role, r.code_role,
                u.id_province, p.code_province, p.nom_province
            FROM app_auth.sessions s
            JOIN app_auth.utilisateurs u ON s.id_utilisateur = u.id_utilisateur
            JOIN app_auth.ref_role r ON u.id_role = r.id_role
            LEFT JOIN app_staging.ref_province p ON u.id_province = p.id_province
            WHERE s.token_hash = %s
              AND s.est_active = TRUE
              AND s.date_expiration > CURRENT_TIMESTAMP
            """,
            (token_hash,),
            fetch="one",
        )
        if result and result["est_actif"]:
            return {
                "id": result["id_utilisateur"],
                "username": result["username"],
                "nom_complet": result["nom_complet"],
                "id_role": result["id_role"],
                "role": result["code_role"],
                "id_province": result["id_province"],
                "code_province": result["code_province"],
                "nom_province": result["nom_province"],
            }
        return None

    @staticmethod
    def logout(user_id: int, token: str):
        try:
            token_hash = _hash_token(token)
            execute_insert(
                """
                UPDATE app_auth.sessions
                SET est_active = FALSE
                WHERE id_utilisateur = %s AND token_hash = %s
                """,
                (user_id, token_hash),
            )
            AuthManager.log_action(user_id, "LOGOUT", "sessions")
        except Exception as e:
            logger.error(f"Erreur logout : {e}")

    @staticmethod
    def change_password(user_id: int, old_password: str, new_password: str) -> dict:
        user = execute_query(
            "SELECT password_hash FROM app_auth.utilisateurs WHERE id_utilisateur = %s",
            (user_id,),
            fetch="one",
        )
        if not user:
            return {"success": False, "message": "Utilisateur non trouvé."}
        if not AuthManager.verify_password(old_password, user["password_hash"]):
            return {"success": False, "message": "Ancien mot de passe incorrect."}
        if len(new_password) < 8:
            return {"success": False, "message": "Le nouveau mot de passe doit avoir au moins 8 caractères."}

        new_hash = AuthManager.hash_password(new_password)
        execute_insert(
            """
            UPDATE app_auth.utilisateurs
            SET password_hash = %s, date_modification = CURRENT_TIMESTAMP
            WHERE id_utilisateur = %s
            """,
            (new_hash, user_id),
        )
        AuthManager.log_action(user_id, "CHANGE_PASSWORD", "utilisateurs", user_id)
        return {"success": True, "message": "Mot de passe modifié avec succès."}

    # ═══════════════════════════════════════════════════
    # RESET PASSWORD
    # ═══════════════════════════════════════════════════

    @staticmethod
    def verify_reset_token(token: str) -> dict:
        if not token:
            return {"valid": False, "message": "Lien invalide."}
        token_hash = _hash_token(token.strip())
        row = execute_query(
            """
            SELECT t.id_reset, t.date_expiration, t.utilise, u.est_actif
            FROM app_auth.password_reset_tokens t
            JOIN app_auth.utilisateurs u ON u.id_utilisateur = t.id_utilisateur
            WHERE t.token_hash = %s
            """,
            (token_hash,),
            fetch="one",
        )
        if not row:
            return {"valid": False, "message": "Lien invalide ou inexistant."}
        if row["utilise"]:
            return {"valid": False, "message": "Ce lien a déjà été utilisé."}
        if row["date_expiration"] < datetime.now():
            return {"valid": False, "message": "Ce lien a expiré (valable 8 minutes). Veuillez refaire une demande."}
        if not row["est_actif"]:
            return {"valid": False, "message": "Compte désactivé. Contactez l'administrateur."}
        return {"valid": True, "message": "Token valide."}

    @staticmethod
    def request_password_reset(username_or_email: str) -> dict:
        import os

        ident = (username_or_email or "").strip().lower()
        if not ident:
            return {"success": False, "message": "Veuillez saisir votre email ou identifiant."}

        generic = {
            "success": True,
            "message": (
                "Si un compte correspondant existe, un email de réinitialisation "
                "a été envoyé. Le lien expire dans 8 minutes."
            ),
        }

        user = execute_query(
            """
            SELECT id_utilisateur, username, email, nom_complet, est_actif
            FROM app_auth.utilisateurs
            WHERE lower(username) = %s OR lower(COALESCE(email, '')) = %s
            """,
            (ident, ident),
            fetch="one",
        )
        if not user or not user["est_actif"]:
            return generic
        if not user.get("email"):
            return {
                "success": False,
                "message": "Aucun email n'est associé à ce compte. Contactez l'administrateur.",
            }

        execute_insert(
            """
            UPDATE app_auth.password_reset_tokens
            SET utilise = TRUE
            WHERE id_utilisateur = %s AND utilise = FALSE
            """,
            (user["id_utilisateur"],),
        )

        raw_token = secrets.token_urlsafe(48)
        token_hash = _hash_token(raw_token)
        expiry = datetime.now() + timedelta(minutes=8)

        execute_insert(
            """
            INSERT INTO app_auth.password_reset_tokens
                (id_utilisateur, token_hash, date_expiration, utilise)
            VALUES (%s, %s, %s, FALSE)
            """,
            (user["id_utilisateur"], token_hash, expiry),
        )
        AuthManager.log_action(user["id_utilisateur"], "REQUEST_PASSWORD_RESET", "password_reset_tokens")

        app_url = os.getenv("APP_URL", "http://localhost:8501").rstrip("/")
        reset_link = f"{app_url}/?reset_token={raw_token}"

        env = os.getenv("ENVIRONMENT", "development_local")
        if env.lower().startswith("dev"):
            return {
                "success": True,
                "message": "Mode développement : email non envoyé (SMTP non configuré).",
                "dev_link": reset_link,
                "dev_token": raw_token,
            }
        return generic

    @staticmethod
    def reset_password_with_token(token: str, new_password: str) -> dict:
        if not token or not new_password:
            return {"success": False, "message": "Token et nouveau mot de passe requis."}
        if len(new_password) < 8:
            return {"success": False, "message": "Le mot de passe doit avoir au moins 8 caractères."}

        token_hash = _hash_token(token.strip())
        row = execute_query(
            """
            SELECT t.id_reset, t.id_utilisateur, t.date_expiration, t.utilise,
                   u.est_actif, u.username
            FROM app_auth.password_reset_tokens t
            JOIN app_auth.utilisateurs u ON u.id_utilisateur = t.id_utilisateur
            WHERE t.token_hash = %s
            """,
            (token_hash,),
            fetch="one",
        )
        if not row:
            return {"success": False, "message": "Lien invalide."}
        if row["utilise"]:
            return {"success": False, "message": "Ce lien a déjà été utilisé."}
        if row["date_expiration"] < datetime.now():
            return {"success": False, "message": "Ce lien a expiré (8 min). Refaites une demande."}
        if not row["est_actif"]:
            return {"success": False, "message": "Compte désactivé. Contactez l'administrateur."}

        new_hash = AuthManager.hash_password(new_password)
        execute_insert(
            """
            UPDATE app_auth.utilisateurs
            SET password_hash = %s, tentatives_echouees = 0, verrouille_jusqua = NULL,
                date_modification = CURRENT_TIMESTAMP
            WHERE id_utilisateur = %s
            """,
            (new_hash, row["id_utilisateur"]),
        )
        execute_insert(
            "UPDATE app_auth.password_reset_tokens SET utilise = TRUE WHERE id_reset = %s",
            (row["id_reset"],),
        )
        execute_insert(
            """
            UPDATE app_auth.sessions SET est_active = FALSE
            WHERE id_utilisateur = %s AND est_active = TRUE
            """,
            (row["id_utilisateur"],),
        )
        AuthManager.log_action(row["id_utilisateur"], "RESET_PASSWORD", "utilisateurs", row["id_utilisateur"])
        return {"success": True, "message": "Mot de passe modifié avec succès. Vous pouvez vous connecter."}

    # ═══════════════════════════════════════════════════
    # ADMINISTRATION UTILISATEURS
    # ═══════════════════════════════════════════════════

    @staticmethod
    def create_user(
        username: str,
        password: str,
        nom_complet: str,
        email: str,
        id_role: int,
        id_province: int = None,
    ) -> dict:
        existing = execute_query(
            "SELECT id_utilisateur FROM app_auth.utilisateurs WHERE username = %s",
            (username.lower().strip(),),
            fetch="one",
        )
        if existing:
            return {"success": False, "message": "Ce nom d'utilisateur existe déjà."}

        password_hash = AuthManager.hash_password(password)
        execute_insert(
            """
            INSERT INTO app_auth.utilisateurs
                (username, password_hash, nom_complet, email, id_role, id_province)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (username.lower().strip(), password_hash, nom_complet, email, id_role, id_province),
        )
        return {"success": True, "message": f"Utilisateur '{username}' créé avec succès."}

    @staticmethod
    def get_all_users() -> list:
        return execute_query(
            """
            SELECT 
                u.id_utilisateur, u.username, u.nom_complet, u.email,
                u.id_role, r.code_role, r.libelle_role,
                u.id_province, p.code_province, p.nom_province,
                u.est_actif, u.derniere_connexion, u.date_creation
            FROM app_auth.utilisateurs u
            JOIN app_auth.ref_role r ON u.id_role = r.id_role
            LEFT JOIN app_staging.ref_province p ON u.id_province = p.id_province
            ORDER BY r.id_role, u.username
            """
        )

    @staticmethod
    def toggle_user_status(user_id: int, activate: bool):
        execute_insert(
            """
            UPDATE app_auth.utilisateurs
            SET est_actif = %s, date_modification = CURRENT_TIMESTAMP
            WHERE id_utilisateur = %s
            """,
            (activate, user_id),
        )

    @staticmethod
    def delete_user(user_id: int) -> dict:
        try:
            check = execute_query(
                "SELECT COUNT(*) c FROM app_staging.lot_saisie WHERE cree_par = %s",
                (user_id,),
                fetch="one",
            )
            if check and check["c"] > 0:
                return {
                    "success": False,
                    "message": "Impossible : cet utilisateur a créé des lots. Désactivez-le à la place.",
                }
            check = execute_query(
                "SELECT COUNT(*) c FROM app_staging.validation WHERE valide_par = %s",
                (user_id,),
                fetch="one",
            )
            if check and check["c"] > 0:
                return {
                    "success": False,
                    "message": "Impossible : cet utilisateur a des validations. Désactivez-le à la place.",
                }

            execute_insert("DELETE FROM app_auth.sessions WHERE id_utilisateur = %s", (user_id,))
            execute_insert("DELETE FROM app_auth.password_reset_tokens WHERE id_utilisateur = %s", (user_id,))
            execute_insert("DELETE FROM app_auth.audit_logs WHERE id_utilisateur = %s", (user_id,))
            execute_insert("DELETE FROM app_auth.utilisateurs WHERE id_utilisateur = %s", (user_id,))
            return {"success": True, "message": "Compte supprimé avec succès."}
        except Exception as e:
            logger.error(f"Erreur suppression : {e}")
            return {"success": False, "message": f"Erreur : {e}"}