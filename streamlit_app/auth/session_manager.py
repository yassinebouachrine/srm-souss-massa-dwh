# auth/session_manager.py
import streamlit as st
from datetime import datetime, timedelta
from auth.authentication import AuthManager
from config.settings import SESSION_TIMEOUT_MINUTES, ROLE_PERMISSIONS


class SessionManager:
    """Gestion de la session Streamlit avec timeout d'inactivité."""

    # Clés de session à effacer lors du logout
    SESSION_KEYS_TO_CLEAR = [
        "authenticated",
        "user",
        "token",
        "last_activity",
        "current_page",
    ]

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
            # Nouvelle session : toujours démarrer sur dashboard
            st.session_state["current_page"] = "dashboard"

            # Nettoyer d'éventuels états résiduels
            if "logout_reason" in st.session_state:
                del st.session_state["logout_reason"]

        return result

    @staticmethod
    def logout(reason: str = "manual"):
        """
        Déconnecte l'utilisateur et nettoie complètement la session.
        
        Args:
            reason: 'manual', 'timeout', ou 'expired'
        """
        # Notifier la base de données de la déconnexion
        if st.session_state.get("user") and st.session_state.get("token"):
            try:
                AuthManager.logout(
                    st.session_state["user"]["id"],
                    st.session_state["token"],
                )
            except Exception:
                pass

        # Effacer toutes les clés de session liées à l'auth
        for key in SessionManager.SESSION_KEYS_TO_CLEAR:
            if key in st.session_state:
                del st.session_state[key]

        # Réinitialiser les valeurs par défaut pour éviter les KeyError
        st.session_state["authenticated"] = False
        st.session_state["user"] = None
        st.session_state["token"] = None
        st.session_state["last_activity"] = None

        # Nettoyer les états liés aux pages (brouillons, sélections, etc.)
        SessionManager._clear_page_states()

        # Stocker la raison pour l'affichage sur la page login
        if reason == "timeout":
            st.session_state["logout_reason"] = "timeout"
        elif reason == "expired":
            st.session_state["logout_reason"] = "expired"

    @staticmethod
    def _clear_page_states():
        """
        Nettoie les états liés aux différentes pages
        (brouillons, sélections multiples, confirmations, etc.).
        """
        # Préfixes des clés à supprimer
        prefixes_to_clear = [
            "sel_",          # sélections multiples validation DP
            "selr_",         # sélections multiples validation régionale
            "confirm_",      # confirmations de suppression
            "confirm_del_",  # confirmations de suppression brouillons
            "editor_",       # data editors
            "editorR_",      # data editors régional
            "draft_",        # brouillons
            "edit_",         # édition rejetés
            "nb_custom_",    # réclamations personnalisées
            "val_",          # valeurs saisies
            "vm_",           # valeurs mensuelles (ancien)
            "vr_",           # valeurs récap (ancien)
            "nb_",           # nombre réclamations
            "tmc_",          # TMC
            "dmt_",          # DMT
            "vb_",           # valeur brute
            "custom_nom_",   # noms custom
            "custom_val_",   # valeurs custom
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