# auth/authentication.py
import bcrypt
import secrets
import hashlib
from datetime import datetime, timedelta
from db.connection import execute_query, execute_insert
from config.settings import MAX_LOGIN_ATTEMPTS, LOCKOUT_DURATION_MINUTES, TOKEN_EXPIRY_HOURS
import logging

logger = logging.getLogger(__name__)


class AuthManager:
    """Gestionnaire d'authentification sécurisé."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify a password against its hash."""
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except Exception:
            return False

    @staticmethod
    def generate_token() -> str:
        """Generate a secure session token."""
        return secrets.token_urlsafe(64)

    @staticmethod
    def authenticate(username: str, password: str) -> dict:
        """
        Authenticate a user. Returns user dict on success, None on failure.
        Implements account lockout after MAX_LOGIN_ATTEMPTS.
        """
        # Fetch user
        user = execute_query(
            """
            SELECT id_utilisateur, username, password_hash, nom_complet, email,
                   role, id_province, code_province, est_actif,
                   tentatives_echouees, verrouille_jusqua
            FROM app_auth.utilisateurs
            WHERE username = %s
            """,
            (username.lower().strip(),),
            fetch="one",
        )

        if not user:
            logger.warning(f"Tentative de connexion - utilisateur inconnu: {username}")
            return {"success": False, "message": "Identifiants incorrects."}

        # Check if account is active
        if not user["est_actif"]:
            logger.warning(f"Tentative de connexion - compte désactivé: {username}")
            return {"success": False, "message": "Ce compte a été désactivé. Contactez l'administrateur."}

        # Check if account is locked
        if user["verrouille_jusqua"] and user["verrouille_jusqua"] > datetime.now():
            remaining = (user["verrouille_jusqua"] - datetime.now()).seconds // 60
            logger.warning(f"Tentative de connexion - compte verrouillé: {username}")
            return {
                "success": False,
                "message": f"Compte verrouillé. Réessayez dans {remaining + 1} minutes.",
            }

        # Verify password
        if not AuthManager.verify_password(password, user["password_hash"]):
            # Increment failed attempts
            attempts = user["tentatives_echouees"] + 1
            lock_until = None

            if attempts >= MAX_LOGIN_ATTEMPTS:
                lock_until = datetime.now() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
                logger.warning(f"Compte verrouillé après {attempts} tentatives: {username}")

            execute_insert(
                """
                UPDATE app_auth.utilisateurs 
                SET tentatives_echouees = %s, verrouille_jusqua = %s, date_modification = CURRENT_TIMESTAMP
                WHERE id_utilisateur = %s
                """,
                (attempts, lock_until, user["id_utilisateur"]),
            )

            remaining_attempts = MAX_LOGIN_ATTEMPTS - attempts
            if remaining_attempts > 0:
                return {
                    "success": False,
                    "message": f"Identifiants incorrects. {remaining_attempts} tentative(s) restante(s).",
                }
            else:
                return {
                    "success": False,
                    "message": f"Compte verrouillé pour {LOCKOUT_DURATION_MINUTES} minutes.",
                }

        # Successful login - reset attempts and update last login
        token = AuthManager.generate_token()
        expiry = datetime.now() + timedelta(hours=TOKEN_EXPIRY_HOURS)

        # Reset failed attempts and update last login
        execute_insert(
            """
            UPDATE app_auth.utilisateurs 
            SET tentatives_echouees = 0, verrouille_jusqua = NULL,
                derniere_connexion = CURRENT_TIMESTAMP, date_modification = CURRENT_TIMESTAMP
            WHERE id_utilisateur = %s
            """,
            (user["id_utilisateur"],),
        )

        # Create session
        execute_insert(
            """
            INSERT INTO app_auth.sessions (id_utilisateur, token_session, date_expiration, est_active)
            VALUES (%s, %s, %s, TRUE)
            """,
            (user["id_utilisateur"], token, expiry),
        )

        # Log the action
        AuthManager.log_action(user["id_utilisateur"], "LOGIN", "utilisateurs", user["id_utilisateur"])

        logger.info(f"Connexion réussie: {username}")
        return {
            "success": True,
            "user": {
                "id": user["id_utilisateur"],
                "username": user["username"],
                "nom_complet": user["nom_complet"],
                "email": user["email"],
                "role": user["role"],
                "id_province": user["id_province"],
                "code_province": user["code_province"],
                "token": token,
            },
        }

    @staticmethod
    def logout(user_id: int, token: str):
        """Invalidate a user session."""
        try:
            execute_insert(
                """
                UPDATE app_auth.sessions 
                SET est_active = FALSE 
                WHERE id_utilisateur = %s AND token_session = %s
                """,
                (user_id, token),
            )
            AuthManager.log_action(user_id, "LOGOUT", "sessions")
        except Exception as e:
            logger.error(f"Erreur logout: {e}")

    @staticmethod
    def validate_session(token: str) -> dict:
        """Validate if a session token is still valid."""
        if not token:
            return None
        result = execute_query(
            """
            SELECT s.id_utilisateur, s.date_expiration, s.est_active,
                   u.username, u.nom_complet, u.role, u.id_province, u.code_province, u.est_actif
            FROM app_auth.sessions s
            JOIN app_auth.utilisateurs u ON s.id_utilisateur = u.id_utilisateur
            WHERE s.token_session = %s AND s.est_active = TRUE AND s.date_expiration > CURRENT_TIMESTAMP
            """,
            (token,),
            fetch="one",
        )
        if result and result["est_actif"]:
            return {
                "id": result["id_utilisateur"],
                "username": result["username"],
                "nom_complet": result["nom_complet"],
                "role": result["role"],
                "id_province": result["id_province"],
                "code_province": result["code_province"],
            }
        return None

    @staticmethod
    def change_password(user_id: int, old_password: str, new_password: str) -> dict:
        """Change user password."""
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

    @staticmethod
    def log_action(user_id: int, action: str, table_cible: str = None, 
                   id_enregistrement: int = None, details: dict = None):
        """Log an audit action."""
        try:
            import json
            execute_insert(
                """
                INSERT INTO app_auth.audit_logs 
                    (id_utilisateur, action, table_cible, id_enregistrement, details)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, action, table_cible, id_enregistrement, 
                 json.dumps(details) if details else None),
            )
        except Exception as e:
            logger.error(f"Erreur audit log: {e}")

    @staticmethod
    def create_user(username: str, password: str, nom_complet: str, email: str,
                    role: str, id_province: int = None, code_province: str = None) -> dict:
        """Create a new user (admin only)."""
        # Check if username exists
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
                (username, password_hash, nom_complet, email, role, id_province, code_province)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (username.lower().strip(), password_hash, nom_complet, email, role, id_province, code_province),
        )
        return {"success": True, "message": f"Utilisateur '{username}' créé avec succès."}

    @staticmethod
    def get_all_users() -> list:
        """Get all users (admin only)."""
        return execute_query(
            """
            SELECT id_utilisateur, username, nom_complet, email, role, 
                   id_province, code_province, est_actif, derniere_connexion, date_creation
            FROM app_auth.utilisateurs
            ORDER BY role, username
            """
        )

    @staticmethod
    def toggle_user_status(user_id: int, activate: bool):
        """Enable or disable a user account."""
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
        """Supprime définitivement un compte utilisateur et ses dépendances (sessions/logs)."""
        try:
            # 1. Vérifier si l'utilisateur a des données métiers (Staging)
            # S'il a déjà saisi des données, on ne peut pas le supprimer car cela casserait la traçabilité
            # Dans ce cas, il vaut mieux désactiver le compte.
            from db.connection import execute_query
            
            check_data = execute_query(
                """
                SELECT 
                    (SELECT COUNT(*) FROM app_staging.staging_indicateurs_dp WHERE soumis_par = %s OR valide_par_dp = %s OR valide_par_regional = %s) +
                    (SELECT COUNT(*) FROM app_staging.staging_reclamations_dp WHERE soumis_par = %s OR valide_par_dp = %s OR valide_par_regional = %s) 
                as total_actions
                """,
                (user_id, user_id, user_id, user_id, user_id, user_id),
                fetch="one"
            )

            if check_data and check_data["total_actions"] > 0:
                return {
                    "success": False, 
                    "message": "Impossible de supprimer ce compte car il est lié à des saisies ou validations existantes. Veuillez plutôt désactiver le compte pour préserver la traçabilité."
                }

            # 2. Supprimer les sessions de cet utilisateur (pour lever la contrainte FK)
            execute_insert(
                "DELETE FROM app_auth.sessions WHERE id_utilisateur = %s",
                (user_id,)
            )
            
            # 3. Supprimer les logs d'audit de cet utilisateur
            execute_insert(
                "DELETE FROM app_auth.audit_logs WHERE id_utilisateur = %s",
                (user_id,)
            )

            # 4. Supprimer le compte utilisateur
            execute_insert(
                "DELETE FROM app_auth.utilisateurs WHERE id_utilisateur = %s",
                (user_id,)
            )
            
            return {"success": True, "message": "Compte et historique d'activité supprimés avec succès."}
            
        except Exception as e:
            logger.error(f"Erreur suppression utilisateur {user_id}: {e}")
            return {"success": False, "message": f"Erreur lors de la suppression : {e}"}