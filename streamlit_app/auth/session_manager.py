# auth/session_manager.py
import streamlit as st
from datetime import datetime, timedelta
from auth.authentication import AuthManager
from config.settings import SESSION_TIMEOUT_MINUTES, ROLE_PERMISSIONS
import hashlib


# Clé secrète pour le hash (ne pas exposer)
_SESSION_SALT = "srm-souss-massa-2026-session"


def _make_session_id(token: str) -> str:
    """Crée un identifiant de session court et opaque à partir du token."""
    return hashlib.sha256(f"{_SESSION_SALT}{token}".encode()).hexdigest()[:16]


class SessionManager:
    """Gestion de la session Streamlit avec persistance après F5."""

    SESSION_KEYS_TO_CLEAR = [
        "authenticated", "user", "token",
        "last_activity", "current_page",
    ]

    @staticmethod
    def init_session():
        """Initialise les variables de session et tente la restauration."""
        defaults = {
            "authenticated": False,
            "user": None,
            "token": None,
            "current_page": "dashboard",
            "last_activity": None,
        }
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

        # Tenter la restauration automatique
        if not st.session_state.get("authenticated"):
            SessionManager._try_restore()

    @staticmethod
    def _try_restore():
        """
        Restaure la session si un session_id valide existe dans les query params.
        Le session_id est un hash court (16 chars) du vrai token — pas le token lui-même.
        """
        sid = st.query_params.get("sid")
        if not sid or len(sid) != 16:
            return

        # Chercher en base un token actif dont le hash correspond
        try:
            from db.connection import execute_query
            result = execute_query(
                """
                SELECT s.token_session, s.id_utilisateur, s.date_expiration,
                       u.username, u.nom_complet, u.role, u.id_province,
                       u.code_province, u.est_actif
                FROM app_auth.sessions s
                JOIN app_auth.utilisateurs u ON s.id_utilisateur = u.id_utilisateur
                WHERE s.est_active = TRUE
                  AND s.date_expiration > CURRENT_TIMESTAMP
                  AND u.est_actif = TRUE
                ORDER BY s.date_creation DESC
                LIMIT 50
                """,
                fetch="all",
            )

            if not result:
                return

            # Vérifier quel token correspond au session_id
            for row in result:
                token = row["token_session"]
                if _make_session_id(token) == sid:
                    # ✅ Match trouvé — restaurer la session
                    st.session_state["authenticated"] = True
                    st.session_state["user"] = {
                        "id": row["id_utilisateur"],
                        "username": row["username"],
                        "nom_complet": row["nom_complet"],
                        "role": row["role"],
                        "id_province": row["id_province"],
                        "code_province": row["code_province"],
                        "token": token,
                    }
                    st.session_state["token"] = token
                    st.session_state["last_activity"] = datetime.now()

                    # Restaurer la page
                    page = st.query_params.get("page", "dashboard")
                    st.session_state["current_page"] = page
                    return
        except Exception:
            pass

    @staticmethod
    def _update_url_sid():
        """Met à jour le session_id dans l'URL (hash court, pas le vrai token)."""
        token = st.session_state.get("token")
        if token:
            st.query_params["sid"] = _make_session_id(token)
        else:
            if "sid" in st.query_params:
                # Garder seulement page
                page = st.query_params.get("page")
                st.query_params.clear()
                if page:
                    st.query_params["page"] = page

    @staticmethod
    def login(username: str, password: str) -> dict:
        """Traite une tentative de connexion."""
        result = AuthManager.authenticate(username, password)
        if result["success"]:
            st.session_state["authenticated"] = True
            st.session_state["user"] = result["user"]
            st.session_state["token"] = result["user"]["token"]
            st.session_state["last_activity"] = datetime.now()
            st.session_state["current_page"] = "dashboard"

            # Mettre le session_id hashé dans l'URL
            SessionManager._update_url_sid()

            if "logout_reason" in st.session_state:
                del st.session_state["logout_reason"]

        return result

    @staticmethod
    def logout(reason: str = "manual"):
        """Déconnecte l'utilisateur et nettoie complètement."""
        if st.session_state.get("user") and st.session_state.get("token"):
            try:
                AuthManager.logout(
                    st.session_state["user"]["id"],
                    st.session_state["token"],
                )
            except Exception:
                pass

        for key in SessionManager.SESSION_KEYS_TO_CLEAR:
            if key in st.session_state:
                del st.session_state[key]

        st.session_state["authenticated"] = False
        st.session_state["user"] = None
        st.session_state["token"] = None
        st.session_state["last_activity"] = None

        SessionManager._clear_page_states()

        if reason == "timeout":
            st.session_state["logout_reason"] = "timeout"
        elif reason == "expired":
            st.session_state["logout_reason"] = "expired"

    @staticmethod
    def _clear_page_states():
        """Nettoie les états liés aux pages."""
        prefixes_to_clear = [
            "sel_", "selr_", "confirm_", "confirm_del_",
            "editor_", "editorR_", "draft_", "edit_",
            "nb_custom_", "val_", "vm_", "vr_",
            "nb_", "tmc_", "dmt_", "vb_",
            "custom_nom_", "custom_val_",
        ]

        keys_to_delete = []
        for key in list(st.session_state.keys()):
            for prefix in prefixes_to_clear:
                if key.startswith(prefix):
                    keys_to_delete.append(key)
                    break

        for key in keys_to_delete:
            try:
                del st.session_state[key]
            except KeyError:
                pass

    @staticmethod
    def check_session_timeout() -> bool:
        if not st.session_state.get("authenticated"):
            return False

        last_activity = st.session_state.get("last_activity")
        if last_activity is None:
            st.session_state["last_activity"] = datetime.now()
            return True

        elapsed = datetime.now() - last_activity
        timeout = timedelta(minutes=SESSION_TIMEOUT_MINUTES)

        if elapsed > timeout:
            SessionManager.logout(reason="timeout")
            return False

        return True

    @staticmethod
    def update_activity():
        if st.session_state.get("authenticated"):
            st.session_state["last_activity"] = datetime.now()

    @staticmethod
    def is_authenticated() -> bool:
        if not st.session_state.get("authenticated"):
            return False

        if not SessionManager.check_session_timeout():
            return False

        token = st.session_state.get("token")
        if token:
            user = AuthManager.validate_session(token)
            if user:
                SessionManager.update_activity()
                return True

        SessionManager.logout(reason="expired")
        return False

    @staticmethod
    def get_user() -> dict:
        return st.session_state.get("user")

    @staticmethod
    def get_role() -> str:
        user = st.session_state.get("user")
        return user["role"] if user else None

    @staticmethod
    def get_province_id() -> int:
        user = st.session_state.get("user")
        return user["id_province"] if user else None

    @staticmethod
    def has_role(roles: list) -> bool:
        return SessionManager.get_role() in roles

    @staticmethod
    def can_access_page(page: str) -> bool:
        role = SessionManager.get_role()
        if not role:
            return False
        allowed_pages = ROLE_PERMISSIONS.get(role, [])
        return page in allowed_pages

    @staticmethod
    def require_auth():
        if not SessionManager.is_authenticated():
            st.warning("Session expirée. Veuillez vous reconnecter.")
            st.stop()

    @staticmethod
    def require_role(roles: list):
        SessionManager.require_auth()
        if not SessionManager.has_role(roles):
            st.error("Vous n'avez pas les droits nécessaires.")
            st.stop()

    @staticmethod
    def get_remaining_session_time() -> int:
        last_activity = st.session_state.get("last_activity")
        if last_activity is None:
            return SESSION_TIMEOUT_MINUTES * 60

        elapsed = (datetime.now() - last_activity).total_seconds()
        remaining = (SESSION_TIMEOUT_MINUTES * 60) - elapsed
        return max(0, int(remaining))