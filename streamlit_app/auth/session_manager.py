# auth/session_manager.py
import streamlit as st
from datetime import datetime, timedelta
from auth.authentication import AuthManager
from config.settings import SESSION_TIMEOUT_MINUTES, ROLE_PERMISSIONS


class SessionManager:
    """Gestion de la session Streamlit avec timeout d'inactivité."""

    @staticmethod
    def init_session():
        """Initialise les variables de session."""
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
        return result

    @staticmethod
    def logout(reason: str = "manual"):
        """Déconnecte l'utilisateur."""
        if st.session_state.get("user") and st.session_state.get("token"):
            try:
                AuthManager.logout(
                    st.session_state["user"]["id"],
                    st.session_state["token"],
                )
            except Exception:
                pass

        # Effacer toutes les infos sensibles
        st.session_state["authenticated"] = False
        st.session_state["user"] = None
        st.session_state["token"] = None
        st.session_state["last_activity"] = None
        st.session_state["current_page"] = "dashboard"

        # Stocker la raison pour l'affichage sur la page login
        if reason == "timeout":
            st.session_state["logout_reason"] = "timeout"
        elif reason == "expired":
            st.session_state["logout_reason"] = "expired"

    @staticmethod
    def check_session_timeout() -> bool:
        """
        Vérifie si la session a expiré par inactivité.
        Retourne True si la session est encore valide, False sinon.
        """
        if not st.session_state.get("authenticated"):
            return False

        last_activity = st.session_state.get("last_activity")
        if last_activity is None:
            st.session_state["last_activity"] = datetime.now()
            return True

        # Vérifier le temps écoulé
        elapsed = datetime.now() - last_activity
        timeout = timedelta(minutes=SESSION_TIMEOUT_MINUTES)

        if elapsed > timeout:
            # Session expirée
            SessionManager.logout(reason="timeout")
            return False

        return True

    @staticmethod
    def update_activity():
        """Met à jour le timestamp de dernière activité."""
        if st.session_state.get("authenticated"):
            st.session_state["last_activity"] = datetime.now()

    @staticmethod
    def is_authenticated() -> bool:
        """Vérifie si l'utilisateur est authentifié ET si la session est valide."""
        if not st.session_state.get("authenticated"):
            return False

        # Vérifier le timeout d'inactivité
        if not SessionManager.check_session_timeout():
            return False

        # Vérifier le token en base
        token = st.session_state.get("token")
        if token:
            user = AuthManager.validate_session(token)
            if user:
                # Mettre à jour l'activité
                SessionManager.update_activity()
                return True

        # Token invalide ou expiré
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
        """Vérifie si l'utilisateur a le droit d'accéder à une page."""
        role = SessionManager.get_role()
        if not role:
            return False
        allowed_pages = ROLE_PERMISSIONS.get(role, [])
        return page in allowed_pages

    @staticmethod
    def require_auth():
        """Bloque l'accès si l'utilisateur n'est pas connecté."""
        if not SessionManager.is_authenticated():
            st.warning("Session expirée. Veuillez vous reconnecter.")
            st.stop()

    @staticmethod
    def require_role(roles: list):
        """Vérifie que l'utilisateur a un des rôles requis."""
        SessionManager.require_auth()
        if not SessionManager.has_role(roles):
            st.error("Vous n'avez pas les droits nécessaires pour accéder à cette page.")
            st.stop()

    @staticmethod
    def get_remaining_session_time() -> int:
        """Retourne le nombre de secondes restantes avant expiration."""
        last_activity = st.session_state.get("last_activity")
        if last_activity is None:
            return SESSION_TIMEOUT_MINUTES * 60

        elapsed = (datetime.now() - last_activity).total_seconds()
        remaining = (SESSION_TIMEOUT_MINUTES * 60) - elapsed
        return max(0, int(remaining))