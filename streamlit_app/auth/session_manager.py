# auth/session_manager.py
"""
Gestionnaire de session haute sécurité & haute disponibilité :
- Restauration F5 instantanée (Native HTTP Cookies + localStorage Fallback)
- Compatible 100% Mode Incognito / InPrivate
- URL propre (aucun SID dans la barre d'adresse)
- Indépendant des bibliothèques tiers obsolètes
"""
from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, timedelta
import logging

from auth.authentication import AuthManager, _get_client_info
from config.settings import SESSION_TIMEOUT_MINUTES, ROLE_PERMISSIONS, TOKEN_EXPIRY_HOURS, IS_PRODUCTION

logger = logging.getLogger(__name__)
COOKIE_NAME = "srm_sm_sid"


class SessionManager:
    SESSION_KEYS_TO_CLEAR = [
        "authenticated", "user", "token", "sid_public",
        "last_activity", "current_page", "restore_attempted"
    ]

    @staticmethod
    def init_session() -> None:
        """Initialise la mémoire de session."""
        defaults = {
            "authenticated": False,
            "user": None,
            "token": None,
            "sid_public": None,
            "current_page": "dashboard",
            "last_activity": None,
            "restore_attempted": False,
        }
        for k, v in defaults.items():
            if k not in st.session_state:
                st.session_state[k] = v

    @staticmethod
    def _get_sid_from_browser() -> str | None:
        """Lit le cookie directement depuis la requête HTTP reçue par le serveur."""
        # 1. Tente via l'API native Streamlit (1.30+)
        try:
            cookies = getattr(st.context, "cookies", {})
            if COOKIE_NAME in cookies:
                return cookies[COOKIE_NAME]
        except Exception:
            pass

        # 2. Tente via les en-têtes HTTP bruts
        try:
            headers = getattr(st.context, "headers", {})
            cookie_str = headers.get("cookie") or headers.get("Cookie") or ""
            for item in cookie_str.split(";"):
                if "=" in item:
                    k, v = item.strip().split("=", 1)
                    if k.strip() == COOKIE_NAME:
                        return v.strip()
        except Exception:
            pass

        return None

    @staticmethod
    def restore_session() -> bool:
        """
        Restaure la session depuis le cookie ou le token de secours.
        """
        if st.session_state.get("authenticated") and st.session_state.get("user"):
            return True

        # 1. Vérifier si un SID est présent dans le Cookie HTTP ou en paramètre de secours
        restore_sid = st.query_params.get("restore_sid")
        sid = restore_sid or SessionManager._get_sid_from_browser()

        if not sid or not isinstance(sid, str) or len(sid) != 16:
            return False

        try:
            from db.connection import execute_query

            row = execute_query(
                """
                SELECT
                    s.id_utilisateur, s.ip_address, s.user_agent,
                    u.username, u.nom_complet, u.email, u.est_actif,
                    u.id_role, r.code_role, r.libelle_role,
                    u.id_province, p.code_province, p.nom_province
                FROM app_auth.sessions s
                JOIN app_auth.utilisateurs u ON u.id_utilisateur = s.id_utilisateur
                JOIN app_auth.ref_role r ON r.id_role = u.id_role
                LEFT JOIN app_staging.ref_province p ON p.id_province = u.id_province
                WHERE s.sid_public = %s
                  AND s.est_active = TRUE
                  AND s.date_expiration > CURRENT_TIMESTAMP
                  AND u.est_actif = TRUE
                """,
                (sid,),
                fetch="one",
            )

            if not row:
                return False

            # Session valide trouvée en BDD !
            st.session_state["authenticated"] = True
            st.session_state["token"] = "active_session"
            st.session_state["sid_public"] = sid
            st.session_state["user"] = {
                "id": row["id_utilisateur"],
                "username": row["username"],
                "nom_complet": row["nom_complet"],
                "email": row["email"],
                "id_role": row["id_role"],
                "role": row["code_role"],
                "role_libelle": row["libelle_role"],
                "id_province": row["id_province"],
                "code_province": row["code_province"],
                "nom_province": row["nom_province"],
                "sid_public": sid,
            }
            st.session_state["last_activity"] = datetime.now()

            # Nettoyer l'URL si on a utilisé le secours de restauration
            page = st.query_params.get("page", "dashboard")
            if "restore_sid" in st.query_params:
                st.query_params.clear()
                st.query_params["page"] = page

            if page in ROLE_PERMISSIONS.get(row["code_role"], []):
                st.session_state["current_page"] = page
            else:
                st.session_state["current_page"] = "dashboard"

            return True

        except Exception as e:
            logger.error(f"Erreur restauration session : {e}")

        return False

    @staticmethod
    def _inject_browser_session(sid: str) -> None:
        """Injecte le cookie et le localStorage au niveau du document principal."""
        js = f"""
        <script>
            (function() {{
                var cookieVal = "{COOKIE_NAME}={sid}; path=/; max-age=28800; SameSite=Lax";
                document.cookie = cookieVal;
                try {{ window.top.document.cookie = cookieVal; }} catch(e) {{}}
                try {{ window.top.localStorage.setItem("{COOKIE_NAME}", "{sid}"); }} catch(e) {{}}
            }})();
        </script>
        """
        components.html(js, height=0, width=0)

    @staticmethod
    def inject_incognito_fallback_js() -> None:
        """Secours Incognito : Si les cookies HTTP sont bloqués, lit le LocalStorage pour restaurer au F5."""
        js = f"""
        <script>
            (function() {{
                try {{
                    var sid = null;
                    try {{ sid = window.top.localStorage.getItem("{COOKIE_NAME}"); }} catch(e) {{}}
                    if (!sid) {{
                        var m = document.cookie.match(new RegExp('(^| )' + "{COOKIE_NAME}" + '=([^;]+)'));
                        if (m) sid = m[2];
                    }}
                    if (sid && sid.length === 16) {{
                        var url = new URL(window.location.href);
                        if (!url.searchParams.has("restore_sid")) {{
                            url.searchParams.set("restore_sid", sid);
                            window.location.href = url.toString();
                        }}
                    }}
                }} catch(e) {{}}
            }})();
        </script>
        """
        components.html(js, height=0, width=0)

    @staticmethod
    def _clear_browser_session() -> None:
        """Nettoie le navigateur au Logout."""
        js = f"""
        <script>
            (function() {{
                var cookieVal = "{COOKIE_NAME}=; path=/; max-age=0; SameSite=Lax";
                document.cookie = cookieVal;
                try {{ window.top.document.cookie = cookieVal; }} catch(e) {{}}
                try {{ window.top.localStorage.removeItem("{COOKIE_NAME}"); }} catch(e) {{}}
            }})();
        </script>
        """
        components.html(js, height=0, width=0)

    @staticmethod
    def login(username: str, password: str) -> dict:
        """Connexion utilisateur."""
        result = AuthManager.authenticate(username, password)
        if not result["success"]:
            return result

        user = result["user"]
        sid = user["sid_public"]

        st.session_state["authenticated"] = True
        st.session_state["user"] = user
        st.session_state["token"] = user.get("token")
        st.session_state["sid_public"] = sid
        st.session_state["last_activity"] = datetime.now()
        st.session_state["current_page"] = "dashboard"

        # Écriture dans le navigateur du client
        SessionManager._inject_browser_session(sid)

        st.query_params.clear()
        st.query_params["page"] = "dashboard"
        st.session_state.pop("logout_reason", None)
        return result

    @staticmethod
    def logout(reason: str = "manual") -> None:
        """Déconnexion complète."""
        sid = st.session_state.get("sid_public")
        if sid:
            try:
                from db.connection import execute_insert
                execute_insert("UPDATE app_auth.sessions SET est_active = FALSE WHERE sid_public = %s", (sid,))
            except Exception:
                pass

        SessionManager._clear_browser_session()

        for k in SessionManager.SESSION_KEYS_TO_CLEAR:
            st.session_state.pop(k, None)

        st.session_state["authenticated"] = False
        st.session_state["user"] = None
        st.session_state["token"] = None
        st.session_state["sid_public"] = None
        st.session_state["last_activity"] = None

        st.query_params.clear()
        SessionManager._clear_page_states()

        if reason in ("timeout", "security_breach", "expired"):
            st.session_state["logout_reason"] = reason

    @staticmethod
    def _clear_page_states() -> None:
        prefixes = (
            "sel_", "selr_", "confirm_", "confirm_del_", "editor_", "editorR_",
            "draft_", "edit_", "val_", "vm_", "vr_", "nb_", "tmc_", "dmt_", "vb_",
            "chk_autres_", "cmt_autres_", "val_autres_", "page_num_", "vh_",
            "chk_corr_", "chk_deleg_",
        )
        for key in list(st.session_state.keys()):
            if any(key.startswith(p) for p in prefixes):
                st.session_state.pop(key, None)

    @staticmethod
    def check_session_timeout() -> bool:
        if not st.session_state.get("authenticated"):
            return False
        last = st.session_state.get("last_activity") or datetime.now()
        st.session_state["last_activity"] = last
        if datetime.now() - last > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
            SessionManager.logout(reason="timeout")
            return False
        return True

    @staticmethod
    def update_activity() -> None:
        if st.session_state.get("authenticated"):
            st.session_state["last_activity"] = datetime.now()

    @staticmethod
    def is_authenticated() -> bool:
        if not st.session_state.get("authenticated"):
            return False
        if not SessionManager.check_session_timeout():
            return False
        SessionManager.update_activity()
        return True

    @staticmethod
    def get_user():
        return st.session_state.get("user")

    @staticmethod
    def get_role():
        u = st.session_state.get("user")
        return u["role"] if u else None

    @staticmethod
    def get_province_id():
        u = st.session_state.get("user")
        return u["id_province"] if u else None

    @staticmethod
    def has_role(roles: list) -> bool:
        return SessionManager.get_role() in roles

    @staticmethod
    def can_access_page(page: str) -> bool:
        role = SessionManager.get_role()
        if not role:
            return False
        return page in ROLE_PERMISSIONS.get(role, [])

    @staticmethod
    def require_auth() -> None:
        if not SessionManager.is_authenticated():
            st.warning("Session expirée. Veuillez vous reconnecter.")
            st.stop()

    @staticmethod
    def require_role(roles: list) -> None:
        SessionManager.require_auth()
        if not SessionManager.has_role(roles):
            st.error("Droits insuffisants.")
            st.stop()

    @staticmethod
    def get_remaining_session_time() -> int:
        last = st.session_state.get("last_activity")
        if last is None:
            return SESSION_TIMEOUT_MINUTES * 60
        rem = SESSION_TIMEOUT_MINUTES * 60 - (datetime.now() - last).total_seconds()
        return max(0, int(rem))