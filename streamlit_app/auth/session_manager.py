# auth/session_manager.py
import streamlit as st
from auth.authentication import AuthManager


class SessionManager:
    """Manage Streamlit session state for authentication."""

    @staticmethod
    def init_session():
        """Initialize session state variables."""
        defaults = {
            "authenticated": False,
            "user": None,
            "token": None,
            "current_page": "login",
        }
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    @staticmethod
    def login(username: str, password: str) -> dict:
        """Process login."""
        result = AuthManager.authenticate(username, password)
        if result["success"]:
            st.session_state["authenticated"] = True
            st.session_state["user"] = result["user"]
            st.session_state["token"] = result["user"]["token"]
        return result

    @staticmethod
    def logout():
        """Process logout."""
        if st.session_state.get("user") and st.session_state.get("token"):
            AuthManager.logout(
                st.session_state["user"]["id"],
                st.session_state["token"],
            )
        st.session_state["authenticated"] = False
        st.session_state["user"] = None
        st.session_state["token"] = None
        st.session_state["current_page"] = "login"

    @staticmethod
    def is_authenticated() -> bool:
        """Check if user is authenticated."""
        if not st.session_state.get("authenticated"):
            return False
        # Validate session token
        token = st.session_state.get("token")
        if token:
            user = AuthManager.validate_session(token)
            if user:
                return True
        # Session expired
        st.session_state["authenticated"] = False
        st.session_state["user"] = None
        return False

    @staticmethod
    def get_user() -> dict:
        """Get current user info."""
        return st.session_state.get("user")

    @staticmethod
    def get_role() -> str:
        """Get current user role."""
        user = st.session_state.get("user")
        return user["role"] if user else None

    @staticmethod
    def get_province_id() -> int:
        """Get current user's province ID."""
        user = st.session_state.get("user")
        return user["id_province"] if user else None

    @staticmethod
    def has_role(roles: list) -> bool:
        """Check if current user has one of the specified roles."""
        return SessionManager.get_role() in roles

    @staticmethod
    def require_auth():
        """Decorator-like function to require authentication."""
        if not SessionManager.is_authenticated():
            st.warning("⚠️ Veuillez vous connecter pour accéder à cette page.")
            st.stop()

    @staticmethod
    def require_role(roles: list):
        """Require specific roles to access a page."""
        SessionManager.require_auth()
        if not SessionManager.has_role(roles):
            st.error("🚫 Vous n'avez pas les droits nécessaires pour accéder à cette page.")
            st.stop()