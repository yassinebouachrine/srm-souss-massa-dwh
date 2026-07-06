"""
============================================================
SRM Souss-Massa - Application Streamlit Principale
============================================================
Point d'entrée de l'application
"""

import streamlit as st
from streamlit_app.config.settings import settings
from streamlit_app.auth.simple_auth import (
    check_authentication, 
    show_login_page, 
    show_user_info_sidebar,
    get_current_user
)
from streamlit_app.db.connection import test_connection


# ============================================================
# CONFIGURATION PAGE
# ============================================================
st.set_page_config(
    page_title=settings.APP_TITLE,
    page_icon=settings.APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# CSS PERSONNALISÉ
# ============================================================
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1976D2;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1976D2;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# VÉRIFICATION AUTHENTIFICATION
# ============================================================
if not check_authentication():
    show_login_page()
    st.stop()


# ============================================================
# HEADER
# ============================================================
st.markdown('<h1 class="main-header">🌊 SRM Souss-Massa</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Système de saisie et consultation des données</p>', 
            unsafe_allow_html=True)


# ============================================================
# SIDEBAR
# ============================================================
show_user_info_sidebar()

with st.sidebar:
    st.markdown("---")
    st.markdown("### 📋 Menu")
    st.info("👈 Sélectionnez une page dans le menu à gauche")


# ============================================================
# PAGE D'ACCUEIL
# ============================================================
st.markdown("## 🏠 Tableau de Bord")

user = get_current_user()
st.success(f"👋 Bienvenue **{user['nom_complet']}** ({user['role']})")

# Test connexion DB
success, msg = test_connection()
if success:
    st.info(f"🐘 PostgreSQL connecté")
else:
    st.error(f"❌ Erreur connexion PostgreSQL: {msg}")


# ============================================================
# APERÇU DES FONCTIONNALITÉS
# ============================================================
st.markdown("---")
st.markdown("## 📊 Modules Disponibles")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    ### 📝 Saisie de Données
    - 📊 Indicateurs DP
    - 📢 Réclamations
    - 🚰 Rendements Étages
    - 💧 Volumes Amenés
    """)

with col2:
    st.markdown("""
    ### 🗺️ Configuration
    - 📏 Linéaires Réseau
    - 🗺️ Matrice Affectation
    - ⚙️ Administration
    """)

with col3:
    st.markdown("""
    ### 📈 Consultation
    - 📈 Historique
    - 📤 Import Fichier
    - 📊 Statistiques
    """)


# ============================================================
# STATISTIQUES RAPIDES
# ============================================================
st.markdown("---")
st.markdown("## 📈 Statistiques Rapides")

try:
    from streamlit_app.db.connection import get_engine
    import pandas as pd
    
    engine = get_engine()
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Nombre de provinces
    nb_provinces = pd.read_sql(
        "SELECT COUNT(*) as nb FROM gold.dim_province", engine
    )['nb'][0]
    
    # Nombre d'indicateurs
    nb_indicateurs = pd.read_sql(
        "SELECT COUNT(*) as nb FROM gold.dim_type_indicateur_dp", engine
    )['nb'][0]
    
    # Nombre de saisies
    nb_saisies = pd.read_sql(
        "SELECT COUNT(*) as nb FROM staging.indicateurs_dp", engine
    )['nb'][0]
    
    # Nombre d'actions audit
    nb_actions = pd.read_sql(
        "SELECT COUNT(*) as nb FROM audit.log_saisies", engine
    )['nb'][0]
    
    with col1:
        st.metric("🏛️ Provinces", nb_provinces)
    with col2:
        st.metric("📊 Indicateurs", nb_indicateurs)
    with col3:
        st.metric("📝 Saisies", nb_saisies)
    with col4:
        st.metric("📋 Actions Audit", nb_actions)

except Exception as e:
    st.warning(f"⚠️ Impossible de charger les statistiques: {e}")


# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #888;'>"
    "🌊 SRM Souss-Massa | Version 1.0 | Développement Local"
    "</div>",
    unsafe_allow_html=True
)