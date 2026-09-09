# app.py
import streamlit as st
import sys
import os
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auth.session_manager import SessionManager
from config.settings import APP_NAME, APP_VERSION, SESSION_TIMEOUT_MINUTES
from config.provinces import get_province_name
from utils.styles import (
    get_login_css,
    get_global_css,
    get_logo_base64,
    Icon,
    get_role_label,
    get_initials,
)

_icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo_srm.png")
_app_icon = Image.open(_icon_path) if os.path.exists(_icon_path) else None

st.set_page_config(
    page_title=APP_NAME,
    page_icon=_app_icon,
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"Get Help": None, "Report a bug": None, "About": f"# {APP_NAME}\nv{APP_VERSION}"},
)

# 1. Initialiser le state en mémoire
SessionManager.init_session()

PAGES_CONFIG = {
    "dashboard": {"title": "Tableau de bord", "module": "views.page_dashboard", "function": "render_dashboard", "section": "Général"},
    "indicateurs": {"title": "Indicateurs DP", "module": "views.page_indicateurs", "function": "render_indicateurs", "section": "Saisie"},
    "reclamations": {"title": "Réclamations", "module": "views.page_reclamations", "function": "render_reclamations", "section": "Saisie"},
    "validation_dp": {"title": "Validation DP", "module": "views.page_validation_dp", "function": "render_validation_dp", "section": "Validation"},
    "validation_regionale": {"title": "Validation régionale", "module": "views.page_validation_regionale", "function": "render_validation_regionale", "section": "Validation"},
    "administration": {"title": "Utilisateurs", "module": "views.page_administration", "function": "render_administration", "section": "Administration"},
    "profil": {"title": "Mon profil", "module": "views.page_profil", "function": "render_profil", "section": "Compte"},
}


def get_current_page() -> str:
    if st.session_state.get("current_page") in PAGES_CONFIG:
        return st.session_state["current_page"]
    page_from_url = st.query_params.get("page")
    if page_from_url in PAGES_CONFIG:
        st.session_state["current_page"] = page_from_url
        return page_from_url
    st.session_state["current_page"] = "dashboard"
    return "dashboard"


def navigate_to(page_key: str):
    if page_key in PAGES_CONFIG:
        st.session_state["current_page"] = page_key
        st.query_params.clear()
        st.query_params["page"] = page_key
        SessionManager.update_activity()


def render_login_page():
    st.markdown(get_login_css(), unsafe_allow_html=True)

    if "login_view" not in st.session_state:
        st.session_state["login_view"] = "login"

    url_token = st.query_params.get("reset_token")
    if url_token:
        from auth.authentication import AuthManager
        check = AuthManager.verify_reset_token(url_token)
        if not check["valid"]:
            st.query_params.clear()
            st.session_state.pop("reset_token_value", None)
            st.session_state["login_view"] = "login"
            st.session_state["reset_error_msg"] = check["message"]
            st.rerun()
        else:
            st.session_state["login_view"] = "reset"
            st.session_state["reset_token_value"] = url_token

    logo_b64 = get_logo_base64()
    logo_html = (
        f'<img src="data:image/png;base64,{logo_b64}" class="login-logo-img" alt="SRM"/>'
        if logo_b64
        else f'<div style="width:70px;height:70px;background:#111827;border-radius:12px;margin:0 auto 1rem;display:flex;align-items:center;justify-content:center;">{Icon.render("DROPLET", 32, "white")}</div>'
    )

    _, mid, _ = st.columns([1.8, 2.4, 1.8])
    with mid:
        view = st.session_state.get("login_view", "login")

        if view == "login":
            reset_err = st.session_state.pop("reset_error_msg", None)
            if reset_err:
                st.error(f"⚠️ {reset_err}")
            reason = st.session_state.pop("logout_reason", None)
            if reason == "timeout":
                st.warning(f"Session expirée après {SESSION_TIMEOUT_MINUTES} min.")
            elif reason == "security_breach":
                st.error("Session interrompue (sécurité).")
            elif reason == "expired":
                st.info("Session expirée. Reconnectez-vous.")

            with st.form("login_form"):
                st.markdown(
                    f'<div class="login-header">{logo_html}'
                    f'<div class="login-title">SRM Souss-Massa</div>'
                    f'<div class="login-sub">Plateforme régionale de données</div></div>',
                    unsafe_allow_html=True,
                )
                username = st.text_input("Email ou identifiant", placeholder="Ex: agent_dp_tata")
                password = st.text_input("Mot de passe", type="password")
                st.markdown("<div style='height:0.25rem'></div>", unsafe_allow_html=True)

                if st.form_submit_button("Se connecter", use_container_width=True, type="primary"):
                    if not username or not password:
                        st.error("Veuillez remplir tous les champs.")
                    else:
                        result = SessionManager.login(username, password)
                        if result["success"]:
                            st.rerun()
                        else:
                            st.error(result["message"])

            if st.button("Mot de passe oublié ?", key="go_forgot", use_container_width=True):
                st.session_state["login_view"] = "forgot"
                st.rerun()

        elif view == "forgot":
            with st.form("forgot_form"):
                st.markdown(
                    f'<div class="login-header">{logo_html}'
                    f'<div class="login-title">Mot de passe oublié</div>'
                    f'<div class="login-sub">Email ou identifiant</div></div>',
                    unsafe_allow_html=True,
                )
                ident = st.text_input("Email ou identifiant")
                if st.form_submit_button("Envoyer le lien", use_container_width=True, type="primary"):
                    from auth.authentication import AuthManager
                    res = AuthManager.request_password_reset(ident)
                    if res["success"]:
                        st.success(res["message"])
                        if res.get("dev_link"):
                            st.code(res["dev_link"])
                    else:
                        st.error(res["message"])
            if st.button("← Retour", key="back1", use_container_width=True):
                st.session_state["login_view"] = "login"
                st.rerun()

        elif view == "reset":
            token_val = st.session_state.get("reset_token_value")
            with st.form("reset_form"):
                st.markdown(
                    f'<div class="login-header">{logo_html}'
                    f'<div class="login-title">Nouveau mot de passe</div></div>',
                    unsafe_allow_html=True,
                )
                new_pwd = st.text_input("Nouveau mot de passe", type="password")
                conf_pwd = st.text_input("Confirmer", type="password")
                if st.form_submit_button("Enregistrer", use_container_width=True, type="primary"):
                    from auth.authentication import AuthManager
                    if not new_pwd or new_pwd != conf_pwd:
                        st.error("Mots de passe invalides ou différents.")
                    else:
                        res = AuthManager.reset_password_with_token(token_val, new_pwd)
                        st.query_params.clear()
                        st.session_state["login_view"] = "login"
                        st.session_state.pop("reset_token_value", None)
                        if res["success"]:
                            st.success(res["message"])
                        else:
                            st.session_state["reset_error_msg"] = res["message"]
                        st.rerun()
            if st.button("← Retour", key="back2", use_container_width=True):
                st.query_params.clear()
                st.session_state["login_view"] = "login"
                st.session_state.pop("reset_token_value", None)
                st.rerun()

    st.markdown(
        f'<div class="login-footer">{APP_NAME} · v{APP_VERSION}<br>© 2026 SRM Souss-Massa</div>',
        unsafe_allow_html=True,
    )


def render_sidebar(current_page: str):
    user = SessionManager.get_user()
    role = user["role"]
    province_name = get_province_name(user["id_province"]) if user.get("id_province") else "Région complète"
    logo_b64 = get_logo_base64()
    logo_html = (
        f'<img src="data:image/png;base64,{logo_b64}" class="sb-logo-img" alt="SRM"/>'
        if logo_b64
        else ""
    )
    remaining_sec = SessionManager.get_remaining_session_time()
    remaining_min = remaining_sec // 60

    with st.sidebar:
        st.markdown('<div class="srm-close-row">', unsafe_allow_html=True)
        _, btn_col = st.columns([5, 1])
        with btn_col:
            if st.button("«", key="btn_sidebar_close"):
                st.session_state["sidebar_open"] = False
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(
            f'<div class="sb-logo-wrap">{logo_html}'
            f'<div class="sb-logo-title">SRM Souss-Massa</div>'
            f'<div class="sb-logo-sub">DATA PLATFORM</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="sb-user"><div class="sb-user-avatar">{get_initials(user["nom_complet"])}</div>'
            f'<div class="sb-user-name">{user["nom_complet"]}</div>'
            f'<div class="sb-user-role">{get_role_label(role)}</div>'
            f'<div class="sb-user-province">{Icon.render("MAP_PIN", 10)}'
            f'<span>{province_name}</span></div></div>',
            unsafe_allow_html=True,
        )

        sections = {}
        for page_key, config in PAGES_CONFIG.items():
            if SessionManager.can_access_page(page_key):
                sections.setdefault(config["section"], []).append(page_key)

        section_colors = {
            "Général": "#3B82F6", "Saisie": "#10B981", "Validation": "#F59E0B",
            "Administration": "#8B5CF6", "Compte": "#6B7280",
        }
        for section in ["Général", "Saisie", "Validation", "Administration", "Compte"]:
            if section not in sections:
                continue
            color = section_colors.get(section, "#6B7280")
            st.markdown(
                f'<div class="nav-section-header">'
                f'<span class="nav-section-dot" style="background:{color};"></span>'
                f'<span class="nav-section-label">{section}</span></div>'
                f'<div class="nav-section-wrapper">',
                unsafe_allow_html=True,
            )
            for page_key in sections[section]:
                active = "nav-active" if current_page == page_key else ""
                st.markdown(f'<div class="{active}">', unsafe_allow_html=True)
                if st.button(PAGES_CONFIG[page_key]["title"], key=f"nav_{page_key}", use_container_width=True):
                    navigate_to(page_key)
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("---")
        color = "#DC2626" if remaining_min <= 1 else "#D97706" if remaining_min <= 2 else "#6B7280"
        txt = (
            f"Session expire dans {remaining_sec}s"
            if remaining_min <= 1
            else f"Session : {remaining_min} min restantes"
        )
        st.markdown(
            f'<div style="text-align:center;font-size:0.7rem;color:{color};padding:0.35rem;'
            f'background:#F9FAFB;border-radius:5px;margin-bottom:0.5rem;">{txt}</div>',
            unsafe_allow_html=True,
        )
        if st.button("Déconnexion", key="btn_logout", use_container_width=True):
            SessionManager.logout()
            st.rerun()
        st.markdown(
            f'<div style="text-align:center;font-size:0.68rem;color:#9CA3AF;margin-top:1rem;">v{APP_VERSION}</div>',
            unsafe_allow_html=True,
        )


def render_open_sidebar_button():
    st.markdown('<div class="srm-open-wrap">', unsafe_allow_html=True)
    c1, _ = st.columns([0.08, 0.92])
    with c1:
        if st.button("»", key="btn_sidebar_open"):
            st.session_state["sidebar_open"] = True
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def secure_route(page: str) -> str:
    if page not in PAGES_CONFIG or not SessionManager.can_access_page(page):
        return "dashboard"
    return page


def render_page(page_key: str):
    config = PAGES_CONFIG.get(page_key) or PAGES_CONFIG["dashboard"]
    try:
        module = __import__(config["module"], fromlist=[config["function"]])
        getattr(module, config["function"])()
    except Exception as e:
        st.error(f"Erreur page « {config['title']} » : {e}")
        import traceback
        with st.expander("Détails"):
            st.code(traceback.format_exc())


def main():
    # ── 2. Essayer de restaurer la session via Cookie HTTP direct ──
    restored = SessionManager.restore_session()

    # ── 3. Si non restauré, tenter le secours Incognito (localStorage) UNE seule fois ──
    if not restored and not st.session_state.get("restore_attempted"):
        st.session_state["restore_attempted"] = True
        SessionManager.inject_incognito_fallback_js()

    # ── 4. Contrôle de l'accès ──
    if not SessionManager.is_authenticated():
        st.session_state.pop("current_page", None)
        render_login_page()
        return

    # ── 5. Utilisateur connecté -> Rendu de l'application ──
    st.session_state["restore_attempted"] = False

    if "sidebar_open" not in st.session_state:
        st.session_state["sidebar_open"] = True

    sidebar_open = st.session_state["sidebar_open"]
    st.markdown(get_global_css(sidebar_open=sidebar_open), unsafe_allow_html=True)

    current_page = secure_route(get_current_page())

    # URL propre : uniquement ?page=...
    st.query_params.clear()
    st.query_params["page"] = current_page

    if sidebar_open:
        render_sidebar(current_page)
    else:
        render_open_sidebar_button()

    render_page(current_page)


if __name__ == "__main__":
    main()