"""
Page : Matrice Affectation Localite/Secteur/Etage
"""
import streamlit as st
from streamlit_app.auth.simple_auth import (
    check_authentication, show_login_page,
    show_user_info_sidebar, get_current_user, user_can_validate
)
from streamlit_app.db.connection import get_db_connection
from streamlit_app.utils.audit import log_action

st.set_page_config(page_title="Matrice", page_icon="🗺️", layout="wide")

if not check_authentication():
    show_login_page()
    st.stop()

show_user_info_sidebar()
user = get_current_user()

st.title("Matrice d'Affectation")
st.caption("Correspondance Localite / Secteur / Etage de Pression")
st.markdown("---")

with st.form("form_matrice"):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        num_loc = st.number_input("Numero Localite (loc)", min_value=1, step=1)
    with col2:
        num_sec = st.number_input("Numero Section (sec)", min_value=1, step=1)
    with col3:
        code_etage = st.number_input("Code Etage", min_value=1, step=1)
    
    col4, col5 = st.columns(2)
    with col4:
        code_loc_sec = st.text_input("Code Loc_Sec", value=f"{code_etage}_{num_sec}")
    with col5:
        nom_etage = st.text_input("Nom Etage")
    
    commentaire = st.text_area("Commentaire", height=60)
    submit = st.form_submit_button("Enregistrer", type="primary", use_container_width=True)

if submit:
    statut = "VALIDE" if user_can_validate() else "EN_ATTENTE"
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO staging.matrice_affectation
                    (num_loc, num_sec, code_etage_num, code_loc_sec, nom_etage,
                     commentaire, saisi_par, statut)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (num_loc, num_sec, code_etage_num)
                DO UPDATE SET code_loc_sec=EXCLUDED.code_loc_sec,
                              nom_etage=EXCLUDED.nom_etage,
                              statut=EXCLUDED.statut,
                              modifie_par=EXCLUDED.saisi_par,
                              date_modification=NOW()
                RETURNING id_saisie
            """, (num_loc, num_sec, code_etage, code_loc_sec, nom_etage,
                  commentaire, user['username'], statut))
            id_s = cur.fetchone()['id_saisie']
            conn.commit()
        log_action(user['username'], 'INSERT', 'staging.matrice_affectation', id_s)
        st.success(f"Affectation enregistree ({statut})")
    except Exception as e:
        st.error(str(e))