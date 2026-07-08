# app.py
import streamlit as st
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auth.session_manager import SessionManager
from config.settings import APP_NAME, APP_VERSION
from config.provinces import get_province_name
from utils.styles import (
    get_login_css, get_global_css, get_logo_base64,
    Icon, get_role_label, get_initials
)



from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Charger l'icône correctement
_icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo_srm.png")
_app_icon = Image.open(_icon_path) if os.path.exists(_icon_path) else "💧"

st.set_page_config(
    page_title=APP_NAME,
    page_icon=_app_icon,   # ← PIL.Image au lieu du chemin string
    layout="wide",
    initial_sidebar_state="expanded",
)

SessionManager.init_session()


# ══════════════════════════════════════════════════════════════
# LOGIN — Logo INTÉGRÉ dans le card
# ══════════════════════════════════════════════════════════════
def render_login_page():
    st.markdown(get_login_css(), unsafe_allow_html=True)

    logo_b64 = get_logo_base64()
    logo_html = (
        f'<img src="data:image/png;base64,{logo_b64}" class="login-logo-img" alt="SRM"/>'
        if logo_b64 else
        f'<div style="width:70px;height:70px;background:#111827;border-radius:12px;margin:0 auto 1rem;display:flex;align-items:center;justify-content:center;">{Icon.render("DROPLET", 32, "white")}</div>'
    )

    # Card unique contenant logo + titre + formulaire
    st.markdown(f"""
    <div class="login-card">
        <div class="login-header">
            {logo_html}
            <div class="login-title">SRM Souss-Massa</div>
            <div class="login-sub">Plateforme régionale de données</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Formulaire (Streamlit ne peut pas être dans le HTML)
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        with st.form("login_form"):
            username = st.text_input("Nom d'utilisateur", placeholder="Ex: agent_dp_tata")
            password = st.text_input("Mot de passe", type="password", placeholder="Votre mot de passe")

            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button("Se connecter", use_container_width=True, type="primary")

            if submitted:
                if not username or not password:
                    st.error("Veuillez remplir tous les champs.")
                else:
                    with st.spinner("Authentification..."):
                        result = SessionManager.login(username, password)
                    if result["success"]:
                        st.rerun()
                    else:
                        st.error(result["message"])

        with st.expander("Comptes de démonstration"):
            st.markdown("""
| Rôle | Identifiant |
|------|-------------|
| Agent DP | `agent_dp_tata` |
| Admin DP | `admin_dp_tata` |
| Admin Régional | `admin_regional` |

Mot de passe : `SRM2024!`
            """)

    st.markdown(f"""
    <div class="login-footer">
        {APP_NAME} · v{APP_VERSION}<br>
        © 2024 Société Régionale Multiservices — Souss-Massa
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════
def render_sidebar():
    user = SessionManager.get_user()
    role = user["role"]
    current_page = st.session_state.get("current_page", "dashboard")
    province_name = get_province_name(user["id_province"]) if user["id_province"] else "Région complète"

    logo_b64 = get_logo_base64()
    logo_html = (
        f'<img src="data:image/png;base64,{logo_b64}" class="sb-logo-img" alt="SRM"/>'
        if logo_b64 else
        f'<div style="width:55px;height:55px;background:#111827;border-radius:10px;margin:0 auto 0.5rem;display:flex;align-items:center;justify-content:center;">{Icon.render("DROPLET", 26, "white")}</div>'
    )

    with st.sidebar:
        st.markdown(f"""
        <div class="sb-logo-wrap">
            {logo_html}
            <div class="sb-logo-title">SRM Souss-Massa</div>
            <div class="sb-logo-sub">DATA PLATFORM</div>
        </div>
        """, unsafe_allow_html=True)

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

        def nav_btn(label, page_key, key):
            active = "nav-active" if current_page == page_key else ""
            st.markdown(f'<div class="{active}">', unsafe_allow_html=True)
            if st.button(label, key=key, use_container_width=True):
                st.session_state["current_page"] = page_key
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="nav-section">Général</div>', unsafe_allow_html=True)
        nav_btn("Tableau de bord", "dashboard", "nav_dash")

        if role in ["agent_dp", "admin_dp", "super_admin"]:
            st.markdown('<div class="nav-section">Saisie</div>', unsafe_allow_html=True)
            nav_btn("Indicateurs DP", "indicateurs", "nav_ind")
            nav_btn("Réclamations", "reclamations", "nav_rec")

        if role in ["admin_dp", "admin_regional", "super_admin"]:
            st.markdown('<div class="nav-section">Validation</div>', unsafe_allow_html=True)
            if role in ["admin_dp", "super_admin"]:
                nav_btn("Validation DP", "validation_dp", "nav_vdp")
            if role in ["admin_regional", "super_admin"]:
                nav_btn("Validation régionale", "validation_regionale", "nav_vreg")

        if role in ["admin_regional", "super_admin"]:
            st.markdown('<div class="nav-section">Administration</div>', unsafe_allow_html=True)
            nav_btn("Utilisateurs", "administration", "nav_adm")

        st.markdown('<div class="nav-section">Compte</div>', unsafe_allow_html=True)
        nav_btn("Mon profil", "profil", "nav_prof")

        st.markdown("---")
        if st.button("Déconnexion", key="btn_logout", use_container_width=True):
            SessionManager.logout()
            st.rerun()

        st.markdown(f"""
        <div style="text-align:center;font-size:0.68rem;color:#9CA3AF;margin-top:1.5rem;">
            v{APP_VERSION}
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
def main():
    if not SessionManager.is_authenticated():
        render_login_page()
    else:
        st.markdown(get_global_css(), unsafe_allow_html=True)
        render_sidebar()

        page = st.session_state.get("current_page", "dashboard")

        # ⚠️ IMPORT DEPUIS views/ (pas pages/)
        if page == "dashboard":
            from views.page_dashboard import render_dashboard
            render_dashboard()
        elif page == "indicateurs":
            from views.page_indicateurs import render_indicateurs
            render_indicateurs()
        elif page == "reclamations":
            from views.page_reclamations import render_reclamations
            render_reclamations()
        elif page == "validation_dp":
            from views.page_validation_dp import render_validation_dp
            render_validation_dp()
        elif page == "validation_regionale":
            from views.page_validation_regionale import render_validation_regionale
            render_validation_regionale()
        elif page == "administration":
            from views.page_administration import render_administration
            render_administration()
        elif page == "profil":
            from views.page_profil import render_profil
            render_profil()
        else:
            from views.page_dashboard import render_dashboard
            render_dashboard()


if __name__ == "__main__":
    main()