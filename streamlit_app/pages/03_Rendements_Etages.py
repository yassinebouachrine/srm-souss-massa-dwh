"""
Page : Saisie des Rendements par Etage
"""
import streamlit as st
from datetime import datetime
from streamlit_app.auth.simple_auth import (
    check_authentication, show_login_page,
    show_user_info_sidebar, get_current_user, user_can_validate
)
from streamlit_app.db.queries import get_etages, insert_rendement_etage
from streamlit_app.utils.audit import log_action
from streamlit_app.utils.helpers import nom_mois

st.set_page_config(page_title="Rendements", page_icon="🚰", layout="wide")

if not check_authentication():
    show_login_page()
    st.stop()

show_user_info_sidebar()
user = get_current_user()

st.title("Rendements par Etage de Pression")
st.caption("Volume facture, volume amene et rendement par etage")
st.markdown("---")

# Contexte
st.subheader("1. Periode")
with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        annee = st.selectbox("Annee", list(range(2024, 2028)), index=2)
    with col2:
        mois = st.selectbox("Mois", list(range(1,13)), format_func=nom_mois,
                           index=datetime.now().month-1)

df_etages = get_etages()

if df_etages.empty:
    st.warning("Aucun etage defini. Ajoutez des etages dans la page Lineaires.")
    st.stop()

if user_can_validate():
    st.success("Mode Directeur : validation directe")
else:
    st.info("Mode Agent : soumission pour validation")

# Formulaire
st.subheader("2. Saisir les rendements")

with st.form("form_rendements"):
    donnees = []
    
    for _, etage in df_etages.iterrows():
        with st.expander(f"{etage['nom_etage']}", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                nb_cli = st.number_input("Nb clients", min_value=0, step=1,
                                        key=f"nc_{etage['id_etage']}")
            with col2:
                vol_f = st.number_input("Vol Facture (m3)", min_value=0.0, step=100.0,
                                       key=f"vf_{etage['id_etage']}")
            with col3:
                vol_a = st.number_input("Vol Amene (m3)", min_value=0.0, step=100.0,
                                       key=f"va_{etage['id_etage']}")
            with col4:
                rend = (vol_f / vol_a * 100) if vol_a > 0 else 0
                st.metric("Rendement", f"{rend:.1f}%")
            
            donnees.append({
                'id_etage': int(etage['id_etage']),
                'nombre_clients': nb_cli,
                'volume_facture_m3': vol_f,
                'volume_amene_m3': vol_a,
                'rendement': rend / 100
            })
    
    st.markdown("---")
    commentaire = st.text_area("Commentaire", height=60)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        submit = st.form_submit_button("Soumettre", use_container_width=True)
    with col2:
        if user_can_validate():
            submit_val = st.form_submit_button("Valider", type="primary", 
                                               use_container_width=True)
        else:
            submit_val = False

if submit or submit_val:
    statut = "VALIDE" if (submit_val and user_can_validate()) else "EN_ATTENTE"
    nb_ok = 0
    for d in donnees:
        if d['volume_amene_m3'] > 0:
            try:
                data = {**d, 'annee': annee, 'mois': mois, 'commentaire': commentaire,
                        'saisi_par': user['username'], 'statut': statut}
                id_s, _ = insert_rendement_etage(data)
                log_action(user['username'], 'INSERT', 'staging.rendements_etage', id_s)
                nb_ok += 1
            except Exception as e:
                st.error(f"Erreur: {e}")
    
    if nb_ok > 0:
        st.success(f"{nb_ok} rendements enregistres ({statut})")
        if statut == "VALIDE":
            st.balloons()