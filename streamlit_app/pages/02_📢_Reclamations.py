"""Page 2 : Réclamations DP"""

import streamlit as st
from datetime import datetime

from streamlit_app.auth.simple_auth import (
    check_authentication, show_login_page, show_user_info_sidebar, get_current_user
)
from streamlit_app.db.queries import (
    get_provinces, get_centres, get_types_reclamations, insert_reclamation_dp
)
from streamlit_app.utils.audit import log_action
from streamlit_app.utils.helpers import nom_mois

st.set_page_config(page_title="Réclamations", page_icon="📢", layout="wide")

if not check_authentication():
    show_login_page()
    st.stop()

show_user_info_sidebar()
user = get_current_user()

st.title("📢 Saisie des Réclamations DP")
st.markdown("Saisir les **10 types de réclamations** par province et mois")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.markdown("### 🔍 Contexte")
    df_provinces = get_provinces()
    if user['provinces_autorisees'] != "ALL":
        df_provinces = df_provinces[df_provinces['nom_province'].isin(user['provinces_autorisees'])]
    
    province_sel = st.selectbox("Province", df_provinces['nom_province'].tolist())
    id_province = int(df_provinces[df_provinces['nom_province'] == province_sel]['id_province'].values[0])
    
    df_centres = get_centres(id_province)
    centre_options = ["-- Global --"] + df_centres['nom_centre'].tolist() if not df_centres.empty else ["-- Global --"]
    centre_sel = st.selectbox("Centre", centre_options)
    id_centre = None if centre_sel == "-- Global --" else int(df_centres[df_centres['nom_centre'] == centre_sel]['id_centre'].values[0])
    
    annee = st.selectbox("Année", list(range(2024, 2027)), index=2)
    mois = st.selectbox("Mois", list(range(1, 13)), format_func=nom_mois, index=datetime.now().month - 1)

# Formulaire
st.markdown(f"### 📝 {province_sel} - {nom_mois(mois)} {annee}")

df_types = get_types_reclamations()

with st.form("form_reclamations"):
    valeurs = {}
    
    for _, rec in df_types.iterrows():
        st.markdown(f"**{rec['libelle_reclamation']}** ({rec['categorie_reclamation']})")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if rec['est_comptage']:
                valeurs[f"{rec['code_type']}_nombre"] = st.number_input(
                    "Nombre", min_value=0, step=1, key=f"n_{rec['code_type']}"
                )
        with col2:
            if rec['code_type'] == 'TPS_COUP':
                valeurs[f"{rec['code_type']}_temps"] = st.number_input(
                    "Temps coupure (h)", min_value=0.0, step=0.5, key=f"t_{rec['code_type']}"
                )
        with col3:
            if rec['code_type'] == 'DELAI_TRAIT':
                valeurs[f"{rec['code_type']}_delai"] = st.number_input(
                    "Délai (jours)", min_value=0.0, step=0.5, key=f"d_{rec['code_type']}"
                )
        
        st.markdown("---")
    
    commentaire = st.text_area("Commentaire")
    submit = st.form_submit_button("✅ Enregistrer", type="primary")

if submit:
    nb_ok = 0
    for _, rec in df_types.iterrows():
        data = {
            'id_province': id_province,
            'id_centre': id_centre,
            'code_type_reclam': rec['code_type'],
            'annee': annee,
            'mois': mois,
            'nombre': valeurs.get(f"{rec['code_type']}_nombre"),
            'temps_coupure_h': valeurs.get(f"{rec['code_type']}_temps"),
            'delai_traitement_j': valeurs.get(f"{rec['code_type']}_delai"),
            'commentaire': commentaire,
            'saisi_par': user['username'],
            'statut': 'VALIDE'
        }
        try:
            id_saisie, inserted = insert_reclamation_dp(data)
            log_action(user['username'], 'INSERT' if inserted else 'UPDATE', 
                      'staging.reclamations_dp', id_saisie)
            nb_ok += 1
        except Exception as e:
            st.error(f"Erreur {rec['code_type']}: {e}")
    
    st.success(f"✅ {nb_ok} réclamations enregistrées")