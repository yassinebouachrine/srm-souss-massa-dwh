"""
============================================================
SRM Souss-Massa - Authentification simple (dev)
============================================================
Pour production: remplacer par LDAP/AD
"""

import streamlit as st
from streamlit_app.config.settings import settings


# Utilisateurs de développement
DEV_USERS = {
    "admin": {
        "password": "admin123",
        "role": "Admin",
        "provinces_autorisees": "ALL",  # Toutes provinces
        "nom_complet": "Administrateur SRM"
    },
    "agent_agadir": {
        "password": "agadir123",
        "role": "Agent DP",
        "provinces_autorisees": ["Agadir"],
        "nom_complet": "Agent DP Agadir"
    },
    "agent_tiznit": {
        "password": "tiznit123",
        "role": "Agent DP",
        "provinces_autorisees": ["Tiznit"],
        "nom_complet": "Agent DP Tiznit"
    },
    "directeur": {
        "password": "dir123",
        "role": "Directeur",
        "provinces_autorisees": "ALL",
        "nom_complet": "Directeur Régional"
    }
}


def check_authentication():
    """Vérifier si l'utilisateur est authentifié"""
    if "user" not in st.session_state:
        st.session_state.user = None
    
    return st.session_state.user is not None


def show_login_page():
    """Afficher la page de login"""
    st.markdown("## 🔐 Connexion")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            st.markdown("### 🌊 SRM Souss-Massa")
            st.markdown("Système de saisie des données")
            
            username = st.text_input("👤 Utilisateur", placeholder="ex: admin")
            password = st.text_input("🔑 Mot de passe", type="password")
            
            submitted = st.form_submit_button("Se connecter", type="primary", use_container_width=True)
            
            if submitted:
                if username in DEV_USERS and DEV_USERS[username]["password"] == password:
                    st.session_state.user = {
                        "username": username,
                        "role": DEV_USERS[username]["role"],
                        "provinces_autorisees": DEV_USERS[username]["provinces_autorisees"],
                        "nom_complet": DEV_USERS[username]["nom_complet"]
                    }
                    st.success(f"✅ Bienvenue {DEV_USERS[username]['nom_complet']} !")
                    st.rerun()
                else:
                    st.error("❌ Utilisateur ou mot de passe incorrect")
        
        # Info dev
        with st.expander("💡 Comptes de test (dev)"):
            st.markdown("""
            | Utilisateur | Mot de passe | Rôle |
            |-------------|--------------|------|
            | admin | admin123 | Admin |
            | agent_agadir | agadir123 | Agent DP |
            | agent_tiznit | tiznit123 | Agent DP |
            | directeur | dir123 | Directeur |
            """)


def logout():
    """Déconnexion"""
    st.session_state.user = None
    st.rerun()


def show_user_info_sidebar():
    """Afficher les infos utilisateur dans la sidebar"""
    if st.session_state.user:
        with st.sidebar:
            st.markdown("---")
            st.markdown(f"### 👤 {st.session_state.user['nom_complet']}")
            st.markdown(f"**Rôle** : {st.session_state.user['role']}")
            
            if isinstance(st.session_state.user['provinces_autorisees'], list):
                st.markdown(f"**Provinces** : {', '.join(st.session_state.user['provinces_autorisees'])}")
            else:
                st.markdown(f"**Provinces** : Toutes")
            
            if st.button("🚪 Déconnexion", use_container_width=True):
                logout()


def get_current_user():
    """Retourner l'utilisateur courant"""
    return st.session_state.get("user")


def check_permission_province(nom_province):
    """Vérifier si l'utilisateur peut accéder à cette province"""
    user = get_current_user()
    if not user:
        return False
    
    if user["provinces_autorisees"] == "ALL":
        return True
    
    return nom_province in user["provinces_autorisees"]