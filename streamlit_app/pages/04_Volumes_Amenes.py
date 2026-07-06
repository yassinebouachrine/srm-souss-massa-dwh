"""
Page : Saisie des Volumes Amenes par Etage
"""
import streamlit as st
from datetime import datetime
from streamlit_app.auth.simple_auth import (
    check_authentication, show_login_page,
    show_user_info_sidebar, get_current_user, user_can_validate
)
from streamlit_app.db.queries import get_etages
from streamlit_app.db.connection import get_db_connection
from streamlit_app.utils.audit import log_action
from streamlit_app.utils.helpers import nom_mois

st.set_page_config(page_title="Volumes Amenes", page_icon="💧", layout="wide")

if not check_authentication():
    show_login_page()
    st.stop()

show_user_info_sidebar()
user = get_current_user()

st.title("Volumes Amenes par Etage")
st.caption("Volume d'eau amene mensuel par etage de pression")
st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    annee = st.selectbox("Annee", list(range(2024, 2028)), index=2)
with col2:
    mois = st.selectbox("Mois", list(range(1,13)), format_func=nom_mois,
                       index=datetime.now().month-1)

df_etages = get_etages()
if df_etages.empty:
    st.warning("Aucun etage defini")
    st.stop()

with st.form("form_volumes"):
    volumes = {}
    cols = st.columns(3)
    
    for idx, (_, etage) in enumerate(df_etages.iterrows()):
        with cols[idx % 3]:
            volumes[int(etage['id_etage'])] = st.number_input(
                f"{etage['nom_etage']} (m3)",
                min_value=0.0, step=100.0,
                key=f"vol_{etage['id_etage']}"
            )
    
    st.markdown("---")
    commentaire = st.text_area("Commentaire", height=60)
    submit = st.form_submit_button("Enregistrer", type="primary", use_container_width=True)

if submit:
    statut = "VALIDE" if user_can_validate() else "EN_ATTENTE"
    nb_ok = 0
    for id_etage, volume in volumes.items():
        if volume > 0:
            try:
                with get_db_connection() as conn:
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO staging.volumes_amenes
                            (id_etage, annee, mois, volume_m3, commentaire, saisi_par, statut)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id_etage, annee, mois)
                        DO UPDATE SET volume_m3=EXCLUDED.volume_m3, 
                                      statut=EXCLUDED.statut,
                                      modifie_par=EXCLUDED.saisi_par,
                                      date_modification=NOW()
                        RETURNING id_saisie
                    """, (id_etage, annee, mois, volume, commentaire, user['username'], statut))
                    id_s = cur.fetchone()['id_saisie']
                    conn.commit()
                log_action(user['username'], 'INSERT', 'staging.volumes_amenes', id_s)
                nb_ok += 1
            except Exception as e:
                st.error(str(e))
    
    if nb_ok > 0:
        st.success(f"{nb_ok} volumes enregistres ({statut})")