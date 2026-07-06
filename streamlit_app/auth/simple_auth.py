"""
SRM Souss-Massa - Authentification (2 comptes)
"""

import streamlit as st
from pathlib import Path
import base64


DEV_USERS = {
    "admin": {
        "password": "admin123",
        "role": "Administrateur",
        "niveau": "ADMIN",
        "nom_complet": "Administrateur SRM",
        "email": "admin@srm-soussmassa.ma",
        "departement": "Direction Regionale",
        "peut_valider": True,
        "peut_saisir": True,
        "peut_administrer": True,
        "recoit_alertes": True
    },
    "agent_regional": {
        "password": "agent123",
        "role": "Agent Regional",
        "niveau": "AGENT",
        "nom_complet": "Agent Regional SRM",
        "email": "agent@srm-soussmassa.ma",
        "departement": "Region Souss-Massa",
        "peut_valider": False,
        "peut_saisir": True,
        "peut_administrer": False,
        "recoit_alertes": False
    }
}


def get_logo_base64():
    logo_path = Path(__file__).parent.parent / "assets" / "logo_srm.png"
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None


def hide_sidebar():
    st.markdown("""
        <style>
            [data-testid="stSidebar"] { display: none !important; }
            [data-testid="collapsedControl"] { display: none !important; }
            .main .block-container { max-width: 600px; margin: auto; }
        </style>
    """, unsafe_allow_html=True)


def check_authentication():
    if "user" not in st.session_state:
        st.session_state.user = None
    return st.session_state.user is not None


def show_login_page():
    hide_sidebar()
    logo_b64 = get_logo_base64()
    if logo_b64:
        st.markdown(f"""
            <div style="text-align:center; margin-top:1rem;">
                <img src="data:image/png;base64,{logo_b64}" style="max-width:150px;">
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("""
        <h2 style="text-align:center; color:#1976D2;">SRM Souss-Massa</h2>
        <p style="text-align:center; color:#888;">Plateforme de saisie des donnees</p>
    """, unsafe_allow_html=True)
    
    with st.form("login"):
        username = st.text_input("Utilisateur")
        password = st.text_input("Mot de passe", type="password")
        submit = st.form_submit_button("Connexion", type="primary", use_container_width=True)
        
        if submit:
            if username in DEV_USERS and DEV_USERS[username]["password"] == password:
                st.session_state.user = {"username": username, **DEV_USERS[username]}
                st.rerun()
            else:
                st.error("Identifiants incorrects")
    
    with st.expander("Comptes disponibles"):
        st.markdown("""
        | Utilisateur | Mot de passe | Role |
        |---|---|---|
        | `admin` | `admin123` | Administrateur (valide les saisies) |
        | `agent_regional` | `agent123` | Agent Regional (saisit les donnees) |
        """)


def logout():
    st.session_state.user = None
    st.rerun()


def show_user_info_sidebar():
    if not st.session_state.user:
        return
    
    user = st.session_state.user
    logo_b64 = get_logo_base64()
    
    if logo_b64:
        st.markdown(f"""
            <style>
                section[data-testid="stSidebar"] {{ background-color: #FFFFFF !important; }}
                [data-testid="stSidebarNav"] li:first-child {{ display: none !important; }}
                [data-testid="stSidebarNav"]::before {{
                    content: "";
                    display: block;
                    height: 90px;
                    background-image: url("data:image/png;base64,{logo_b64}");
                    background-repeat: no-repeat;
                    background-position: center;
                    background-size: contain;
                    margin: 1rem;
                }}
                [data-testid="stSidebarNav"]::after {{
                    content: "SRM Souss-Massa";
                    display: block;
                    text-align: center;
                    color: #1976D2;
                    font-weight: bold;
                    padding-bottom: 0.8rem;
                    border-bottom: 2px solid #1976D2;
                    margin: 0 1rem 0.5rem 1rem;
                }}
                [data-testid="stSidebarNav"] a {{
                    padding: 0.5rem 1rem !important;
                    border-radius: 6px !important;
                    margin: 0.2rem 0.5rem !important;
                }}
                [data-testid="stSidebarNav"] a:hover {{ background: rgba(25,118,210,0.08) !important; }}
                [data-testid="stSidebarNav"] a[aria-current="page"] {{
                    background: rgba(25,118,210,0.15) !important;
                    font-weight: 600 !important;
                }}
            </style>
        """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown("---")
        st.markdown(f"""
            <div style="padding:0.7rem; background:rgba(25,118,210,0.08);
                        border-radius:6px; border-left:3px solid #1976D2;">
                <div style="font-weight:600; color:#1976D2;">{user['nom_complet']}</div>
                <div style="color:#666; font-size:0.75rem;">{user['role']}</div>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("Deconnexion", use_container_width=True, key="logout"):
            logout()


def get_current_user():
    return st.session_state.get("user")


def user_can_validate():
    u = get_current_user()
    return u and u.get("peut_valider", False)


def user_can_administer():
    u = get_current_user()
    return u and u.get("peut_administrer", False)


def user_receives_alerts():
    u = get_current_user()
    return u and u.get("recoit_alertes", False)