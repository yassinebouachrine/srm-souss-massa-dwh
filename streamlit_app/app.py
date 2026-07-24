# app.py
import streamlit as st
import sys
import os
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auth.session_manager import SessionManager
from config.settings import APP_NAME, APP_VERSION, SESSION_TIMEOUT_MINUTES, ROLE_PERMISSIONS
from config.provinces import get_province_name
from utils.styles import (
    get_login_css, get_global_css, get_logo_base64,
    Icon, get_role_label, get_initials
)


# ══════════════════════════════════════════════════════════════
# CONFIGURATION DE L'APP
# ══════════════════════════════════════════════════════════════
_icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "assets", "logo_srm.png")
_app_icon = Image.open(_icon_path) if os.path.exists(_icon_path) else None

st.set_page_config(
    page_title=APP_NAME,
    page_icon=_app_icon,
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': f"# {APP_NAME}\nVersion {APP_VERSION}\n© 2026 SRM Souss-Massa"
    }
)

SessionManager.init_session()


# ══════════════════════════════════════════════════════════════
# ROUTES DE L'APPLICATION
# ══════════════════════════════════════════════════════════════
PAGES_CONFIG = {
    "dashboard": {
        "title": "Tableau de bord",
        "icon": "DASHBOARD",
        "module": "views.page_dashboard",
        "function": "render_dashboard",
        "section": "Général",
    },
    "indicateurs": {
        "title": "Indicateurs DP",
        "icon": "CHART_BAR",
        "module": "views.page_indicateurs",
        "function": "render_indicateurs",
        "section": "Saisie",
    },
    "reclamations": {
        "title": "Réclamations",
        "icon": "MESSAGE",
        "module": "views.page_reclamations",
        "function": "render_reclamations",
        "section": "Saisie",
    },
    "validation_dp": {
        "title": "Validation DP",
        "icon": "CHECK_CIRCLE",
        "module": "views.page_validation_dp",
        "function": "render_validation_dp",
        "section": "Validation",
    },
    "validation_regionale": {
        "title": "Validation régionale",
        "icon": "SHIELD",
        "module": "views.page_validation_regionale",
        "function": "render_validation_regionale",
        "section": "Validation",
    },
    "administration": {
        "title": "Utilisateurs",
        "icon": "USERS",
        "module": "views.page_administration",
        "function": "render_administration",
        "section": "Administration",
    },
    "profil": {
        "title": "Mon profil",
        "icon": "USER",
        "module": "views.page_profil",
        "function": "render_profil",
        "section": "Compte",
    },
}


# ══════════════════════════════════════════════════════════════
# NAVIGATION
# ══════════════════════════════════════════════════════════════
def get_current_page() -> str:
    """Détermine la page courante."""
    if "current_page" in st.session_state and st.session_state["current_page"]:
        page = st.session_state["current_page"]
        if page in PAGES_CONFIG:
            return page

    query_params = st.query_params
    if "page" in query_params:
        page_from_url = query_params["page"]
        if page_from_url in PAGES_CONFIG:
            st.session_state["current_page"] = page_from_url
            return page_from_url

    st.session_state["current_page"] = "dashboard"
    return "dashboard"


def navigate_to(page_key: str):
    """Navigue vers une page."""
    if page_key in PAGES_CONFIG:
        st.session_state["current_page"] = page_key
        st.query_params["page"] = page_key
        # Conserver le sid dans l'URL
        SessionManager._update_url_sid()
        SessionManager.update_activity()


def clear_navigation():
    """Nettoie l'URL et la page courante."""
    st.query_params.clear()
    if "current_page" in st.session_state:
        del st.session_state["current_page"]


def force_url_cleanup():
    """
    Injecte du JavaScript pour NETTOYER complètement l'URL côté navigateur.
    Utilise history.replaceState pour ne pas laisser d'entrée dans l'historique.
    """
    st.markdown("""
        <script>
            (function() {
                if (window.location.search) {
                    const cleanUrl = window.location.protocol + '//' + 
                                     window.location.host + 
                                     window.location.pathname;
                    window.history.replaceState({}, document.title, cleanUrl);
                }
            })();
        </script>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# LOGIN PAGE
# ══════════════════════════════════════════════════════════════
def render_login_page():
    st.markdown(get_login_css(), unsafe_allow_html=True)

    # ✅ NETTOYER l'URL immédiatement au chargement de la page login
    force_url_cleanup()

    logo_b64 = get_logo_base64()
    logo_html = (
        f'<img src="data:image/png;base64,{logo_b64}" class="login-logo-img" alt="SRM"/>'
        if logo_b64 else
        f'<div style="width:70px;height:70px;background:#111827;border-radius:12px;'
        f'margin:0 auto 1rem;display:flex;align-items:center;justify-content:center;">'
        f'{Icon.render("DROPLET", 32, "white")}</div>'
    )

    st.markdown(f"""
    <div class="login-card">
        <div class="login-header">
            {logo_html}
            <div class="login-title">SRM Souss-Massa</div>
            <div class="login-sub">Plateforme régionale de données</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        logout_reason = st.session_state.pop("logout_reason", None)
        if logout_reason == "timeout":
            st.warning(
                f"Votre session a expiré après {SESSION_TIMEOUT_MINUTES} minutes "
                f"d'inactivité. Veuillez vous reconnecter."
            )
        elif logout_reason == "expired":
            st.info("Votre session a expiré. Veuillez vous reconnecter.")

        with st.form("login_form"):
            username = st.text_input("Nom d'utilisateur", placeholder="Ex: agent_dp_tata")
            password = st.text_input("Mot de passe", type="password",
                                     placeholder="Votre mot de passe")

            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button("Se connecter", use_container_width=True,
                                              type="primary")

            if submitted:
                if not username or not password:
                    st.error("Veuillez remplir tous les champs.")
                else:
                    with st.spinner("Authentification..."):
                        result = SessionManager.login(username, password)
                    if result["success"]:
                        st.session_state["current_page"] = "dashboard"
                        st.query_params["page"] = "dashboard"
                        st.rerun()
                    else:
                        st.error(result["message"])

    st.markdown(f"""
    <div class="login-footer">
        {APP_NAME} · v{APP_VERSION}<br>
        © 2026 Société Régionale Multiservices — Souss-Massa
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════
def render_sidebar(current_page: str):
    user = SessionManager.get_user()
    role = user["role"]
    province_name = (get_province_name(user["id_province"])
                     if user["id_province"] else "Région complète")

    logo_b64 = get_logo_base64()
    logo_html = (
        f'<img src="data:image/png;base64,{logo_b64}" class="sb-logo-img" alt="SRM"/>'
        if logo_b64 else
        f'<div style="width:55px;height:55px;background:#111827;border-radius:10px;'
        f'margin:0 auto 0.5rem;display:flex;align-items:center;justify-content:center;">'
        f'{Icon.render("DROPLET", 26, "white")}</div>'
    )

    remaining_sec = SessionManager.get_remaining_session_time()
    remaining_min = remaining_sec // 60

    with st.sidebar:
        # ── Logo ──
        st.markdown(f"""
        <div class="sb-logo-wrap">
            {logo_html}
            <div class="sb-logo-title">SRM Souss-Massa</div>
            <div class="sb-logo-sub">DATA PLATFORM</div>
        </div>
        """, unsafe_allow_html=True)

        # ── User info ──
        st.markdown(f"""
        <div class="sb-user">
            <div class="sb-user-avatar">{get_initials(user['nom_complet'])}</div>
            <div class="sb-user-name">{user['nom_complet']}</div>
            <div class="sb-user-role">{get_role_label(role)}</div>
            <div class="sb-user-province">
                {Icon.render("MAP_PIN", 10)}<span>{province_name}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Navigation ──
        def nav_btn(page_key: str, key: str):
            if not SessionManager.can_access_page(page_key):
                return

            config = PAGES_CONFIG[page_key]
            is_active = (current_page == page_key)
            active_class = "nav-active" if is_active else ""

            st.markdown(f'<div class="{active_class}">', unsafe_allow_html=True)
            if st.button(config["title"], key=key, use_container_width=True):
                navigate_to(page_key)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        sections = {}
        for page_key, config in PAGES_CONFIG.items():
            if SessionManager.can_access_page(page_key):
                section = config["section"]
                sections.setdefault(section, []).append(page_key)

        section_order = ["Général", "Saisie", "Validation", "Administration", "Compte"]
        for section in section_order:
            if section in sections:
                st.markdown(f'<div class="nav-section">{section}</div>',
                            unsafe_allow_html=True)
                for page_key in sections[section]:
                    nav_btn(page_key, f"nav_{page_key}")

        st.markdown("---")

        # ── Indicateur de session ──
        if remaining_min <= 1:
            timeout_color = "#DC2626"
            timeout_text = f"Session expire dans {remaining_sec}s"
        elif remaining_min <= 2:
            timeout_color = "#D97706"
            timeout_text = f"Session : {remaining_min} min restantes"
        else:
            timeout_color = "#6B7280"
            timeout_text = f"Session : {remaining_min} min restantes"

        st.markdown(f"""
        <div style="text-align:center;font-size:0.7rem;color:{timeout_color};
                    padding:0.35rem 0.75rem;background:#F9FAFB;border-radius:5px;
                    margin-bottom:0.5rem;">
            {timeout_text}
        </div>
        """, unsafe_allow_html=True)

        # ══════════════════════════════════════════════════════
        # ── DÉCONNEXION AVEC FORCE REFRESH ──
        # ══════════════════════════════════════════════════════
                # ── Déconnexion ──
        if st.button("Déconnexion", key="btn_logout", use_container_width=True):
            SessionManager.logout()
            clear_navigation()
            st.markdown("""
                <meta http-equiv="refresh" content="0; url=./" />
                <script>window.location.replace(window.location.protocol + '//' + window.location.host + window.location.pathname);</script>
                <style>body { display: none; }</style>
            """, unsafe_allow_html=True)
            st.stop()

        # ── Version ──
        st.markdown(f"""
        <div style="text-align:center;font-size:0.68rem;color:#9CA3AF;margin-top:1.5rem;">
            v{APP_VERSION}
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════
def secure_route(page: str) -> str:
    """Vérifie que l'utilisateur peut accéder à la page."""
    if page not in PAGES_CONFIG or not SessionManager.can_access_page(page):
        return "dashboard"
    return page


def render_page(page_key: str):
    """Charge dynamiquement et affiche une page."""
    if page_key not in PAGES_CONFIG:
        page_key = "dashboard"

    config = PAGES_CONFIG[page_key]

    try:
        module = __import__(config["module"], fromlist=[config["function"]])
        render_func = getattr(module, config["function"])
        render_func()
    except ImportError as e:
        st.error(f"Impossible de charger la page « {config['title']} »")
        with st.expander("Détails de l'erreur"):
            st.code(f"Module: {config['module']}\nFunction: {config['function']}\n\n{e}")
    except Exception as e:
        st.error(f"Erreur lors du chargement de la page : {e}")
        import traceback
        with st.expander("Détails techniques"):
            st.code(traceback.format_exc())


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
def main():
    if not SessionManager.is_authenticated():
        # Nettoyer l'URL
        if "page" in st.query_params or "sid" in st.query_params:
            st.query_params.clear()
        if "current_page" in st.session_state:
            del st.session_state["current_page"]

        # Nettoyer l'URL côté navigateur
        force_url_cleanup()

        render_login_page()
    else:
        st.markdown(get_global_css(), unsafe_allow_html=True)
        SessionManager.update_activity()

        current_page = get_current_page()
        current_page = secure_route(current_page)

        # Mettre à jour l'URL avec page + sid
        st.query_params["page"] = current_page
        SessionManager._update_url_sid()

        render_sidebar(current_page)
        render_page(current_page)


if __name__ == "__main__":
    main()