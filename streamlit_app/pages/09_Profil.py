"""
Page Profil Utilisateur
"""

import streamlit as st
import pandas as pd

from streamlit_app.auth.simple_auth import (
    check_authentication, show_login_page,
    show_user_info_sidebar, get_current_user, logout
)
from streamlit_app.db.connection import get_engine


st.set_page_config(page_title="Profil", page_icon="👤", layout="wide")

if not check_authentication():
    show_login_page()
    st.stop()

show_user_info_sidebar()
user = get_current_user()


st.title("Mon Profil")
st.markdown("---")


# Info principales
col1, col2 = st.columns([1, 2])

with col1:
    with st.container(border=True):
        st.markdown(f"""
            <div style="text-align:center; padding:2rem 0;">
                <div style="font-size:5rem;">👤</div>
                <h3 style="color:#1976D2; margin:1rem 0 0.5rem 0;">
                    {user['nom_complet']}
                </h3>
                <div style="background:#1976D2; color:white; padding:0.3rem 1rem;
                            border-radius:20px; display:inline-block;">
                    {user['role']}
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        if st.button("Se deconnecter", type="primary", use_container_width=True):
            logout()


with col2:
    # Informations
    with st.container(border=True):
        st.subheader("Informations")
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Nom d'utilisateur**")
            st.code(user['username'])
            
            st.markdown("**Email**")
            st.code(user.get('email', 'Non defini'))
        
        with col_b:
            st.markdown("**Departement**")
            st.code(user.get('departement', 'Non defini'))
            
            st.markdown("**Niveau**")
            st.code(user.get('niveau', 'N/A'))
    
    # Permissions
    with st.container(border=True):
        st.subheader("Mes Permissions")
        
        perms = [
            ("Saisir des donnees", user.get('peut_saisir', False)),
            ("Valider des saisies", user.get('peut_valider', False)),
            ("Administrer le systeme", user.get('peut_administrer', False)),
            ("Recevoir des alertes", user.get('recoit_alertes', False))
        ]
        
        for label, val in perms:
            if val:
                st.success(f"✅ {label}")
            else:
                st.error(f"❌ {label}")
    
    # Statistiques
    with st.container(border=True):
        st.subheader("Mes Statistiques")
        
        try:
            engine = get_engine()
            
            nb_saisies = pd.read_sql(f"""
                SELECT COUNT(*) as n FROM staging.indicateurs_dp 
                WHERE saisi_par = '{user['username']}'
            """, engine)['n'][0]
            
            nb_val = pd.read_sql(f"""
                SELECT COUNT(*) as n FROM staging.indicateurs_dp 
                WHERE saisi_par = '{user['username']}' AND statut = 'VALIDE'
            """, engine)['n'][0]
            
            nb_att = pd.read_sql(f"""
                SELECT COUNT(*) as n FROM staging.indicateurs_dp 
                WHERE saisi_par = '{user['username']}' AND statut = 'EN_ATTENTE'
            """, engine)['n'][0]
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total saisies", nb_saisies)
            col2.metric("Validees", nb_val)
            col3.metric("En attente", nb_att)
        
        except Exception as e:
            st.warning(f"Statistiques indisponibles: {e}")


st.markdown("---")

# Info theme
with st.container(border=True):
    st.subheader("Preferences")
    st.info("""
    **Pour changer le theme (Clair / Sombre) :**
    
    1. Cliquer sur les **3 points ⋮** en haut a droite
    2. Selectionner **Settings**
    3. Choisir **Theme** : Light, Dark ou Custom
    """)