"""
Page : Saisie des Lineaires Reseau
"""
import streamlit as st
from streamlit_app.auth.simple_auth import (
    check_authentication, show_login_page,
    show_user_info_sidebar, get_current_user, user_can_validate
)
from streamlit_app.db.connection import get_db_connection
from streamlit_app.utils.audit import log_action

st.set_page_config(page_title="Lineaires", page_icon="📏", layout="wide")

if not check_authentication():
    show_login_page()
    st.stop()

show_user_info_sidebar()
user = get_current_user()

st.title("Lineaires Reseau")
st.caption("Lineaire par etage de pression ou secteur hydraulique")
st.markdown("---")

type_elem = st.radio("Type d'element", ["ETAGE", "SECTEUR"], horizontal=True)

with st.form("form_lineaires"):
    nom = st.text_input("Nom de l'element")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        lineaire_km = st.number_input("Lineaire (km)", min_value=0.0, step=0.1)
    with col2:
        lineaire_m = st.number_input("Lineaire (m)", min_value=0.0, step=1.0,
                                     value=lineaire_km * 1000)
    with col3:
        annee_ref = st.selectbox("Annee reference", list(range(2020, 2028)), index=6)
    
    commentaire = st.text_area("Commentaire", height=60)
    submit = st.form_submit_button("Enregistrer", type="primary", use_container_width=True)

if submit and nom:
    statut = "VALIDE" if user_can_validate() else "EN_ATTENTE"
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO staging.lineaires
                    (type_element, id_element, nom_element, lineaire_km, lineaire_m,
                     annee_reference, commentaire, saisi_par, statut)
                VALUES (%s, 0, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id_saisie
            """, (type_elem, nom, lineaire_km, lineaire_m, annee_ref,
                  commentaire, user['username'], statut))
            id_s = cur.fetchone()['id_saisie']
            conn.commit()
        log_action(user['username'], 'INSERT', 'staging.lineaires', id_s)
        st.success(f"Lineaire '{nom}' enregistre ({statut})")
    except Exception as e:
        st.error(str(e))
elif submit:
    st.warning("Veuillez saisir un nom")