"""Page 3 : Rendements par Étage"""

import streamlit as st
from datetime import datetime

from streamlit_app.auth.simple_auth import (
    check_authentication, show_login_page, show_user_info_sidebar, get_current_user
)
from streamlit_app.db.queries import get_etages, insert_rendement_etage
from streamlit_app.utils.audit import log_action
from streamlit_app.utils.helpers import nom_mois

st.set_page_config(page_title="Rendements Étages", page_icon="🚰", layout="wide")

if not check_authentication():
    show_login_page()
    st.stop()

show_user_info_sidebar()
user = get_current_user()

st.title("🚰 Saisie des Rendements par Étage")
st.markdown("---")

df_etages = get_etages()

if df_etages.empty:
    st.warning("⚠️ Aucun étage de pression défini. Créez d'abord des étages dans la Page 5 (Linéaires) ou Administration.")
    st.stop()

with st.sidebar:
    st.markdown("### 📅 Période")
    annee = st.selectbox("Année", list(range(2024, 2027)), index=2)
    mois = st.selectbox("Mois", list(range(1, 13)), format_func=nom_mois, index=datetime.now().month - 1)

st.markdown(f"### 📊 {nom_mois(mois)} {annee}")

with st.form("form_rendements"):
    st.info("💡 Saisir les données pour chaque étage")
    
    donnees = []
    
    for _, etage in df_etages.iterrows():
        with st.expander(f"🏢 {etage['nom_etage']}", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                nb_clients = st.number_input(
                    "Nombre clients", min_value=0, step=1,
                    key=f"nc_{etage['id_etage']}"
                )
            with col2:
                vol_facture = st.number_input(
                    "Vol Facturé (m³)", min_value=0.0, step=100.0,
                    key=f"vf_{etage['id_etage']}"
                )
            with col3:
                vol_amene = st.number_input(
                    "Vol Amené (m³)", min_value=0.0, step=100.0,
                    key=f"va_{etage['id_etage']}"
                )
            
            rendement = (vol_facture / vol_amene * 100) if vol_amene > 0 else 0
            st.metric("Rendement calculé", f"{rendement:.2f}%")
            
            donnees.append({
                'id_etage': int(etage['id_etage']),
                'nombre_clients': nb_clients,
                'volume_facture_m3': vol_facture,
                'volume_amene_m3': vol_amene,
                'rendement': rendement / 100
            })
    
    submit = st.form_submit_button("✅ Enregistrer tous", type="primary")

if submit:
    nb_ok = 0
    for d in donnees:
        if d['volume_amene_m3'] > 0:
            data = {**d, 'annee': annee, 'mois': mois, 'commentaire': '',
                    'saisi_par': user['username'], 'statut': 'VALIDE'}
            try:
                id_saisie, inserted = insert_rendement_etage(data)
                log_action(user['username'], 'INSERT' if inserted else 'UPDATE',
                          'staging.rendements_etage', id_saisie)
                nb_ok += 1
            except Exception as e:
                st.error(f"Erreur: {e}")
    
    st.success(f"✅ {nb_ok} rendements enregistrés")