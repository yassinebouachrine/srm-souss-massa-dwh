"""
Saisie des Volumes Amenes par Etage
Reproduit la structure du fichier: Volume Amene par etage.xlsx
Colonnes: NOM_ETAGE, Mois, Vol Amene (m3)
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from streamlit_app.auth.simple_auth import (
    check_authentication, show_login_page,
    show_user_info_sidebar, get_current_user, user_can_validate
)
from streamlit_app.db.queries import get_etages
from streamlit_app.db.connection import get_engine, get_db_connection
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


# Periode
st.subheader("1. Periode")
with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        annee = st.selectbox("Annee", list(range(2020, 2028)), index=6)
    with col2:
        mois = st.selectbox("Mois", list(range(1,13)), format_func=nom_mois,
                           index=datetime.now().month-1)


df_etages = get_etages()
if df_etages.empty:
    st.warning("Aucun etage defini")
    st.stop()


# Mode
if user_can_validate():
    st.success("**Mode Administrateur** : Validation directe")
else:
    st.info("**Mode Agent** : Soumission pour validation")


# Charger valeurs existantes
try:
    engine = get_engine()
    df_existant = pd.read_sql(f"""
        SELECT id_etage, volume_m3
        FROM staging.volumes_amenes
        WHERE annee = {annee} AND mois = {mois}
    """, engine)
    valeurs_existantes = dict(zip(df_existant['id_etage'], df_existant['volume_m3']))
except Exception:
    valeurs_existantes = {}


# Formulaire
st.subheader(f"2. Saisir les volumes - {nom_mois(mois)} {annee}")

with st.form("form_volumes"):
    volumes = {}
    
    # Affichage en 3 colonnes
    cols = st.columns(3)
    
    for idx, (_, etage) in enumerate(df_etages.iterrows()):
        id_etage = int(etage['id_etage'])
        val_prev = float(valeurs_existantes.get(id_etage, 0.0)) if valeurs_existantes.get(id_etage) else 0.0
        
        with cols[idx % 3]:
            volumes[id_etage] = st.number_input(
                f"**{etage['nom_etage']}** (m3)",
                min_value=0.0,
                step=100.0,
                value=val_prev,
                key=f"vol_{id_etage}"
            )
    
    st.markdown("---")
    commentaire = st.text_area("Commentaire", height=60)
    
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        submit = st.form_submit_button("Soumettre", use_container_width=True)
    with col2:
        if user_can_validate():
            submit_val = st.form_submit_button("Valider", type="primary", use_container_width=True)
        else:
            submit_val = False


if submit or submit_val:
    statut = "VALIDE" if (submit_val and user_can_validate()) else "EN_ATTENTE"
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
        if statut == "VALIDE":
            st.success(f"{nb_ok} volumes valides")
            st.balloons()
        else:
            st.success(f"{nb_ok} volumes soumis pour validation")


# Historique
st.markdown("---")
st.subheader("Historique - Format Excel")

try:
    df = pd.read_sql("""
        SELECT 
            e.nom_etage AS "NOM_ETAGE",
            TO_CHAR(TO_DATE(s.mois::TEXT, 'MM'), 'FMMonth') || '-' || RIGHT(s.annee::TEXT, 2) AS "Mois",
            s.volume_m3 AS "Vol Amene",
            s.statut AS "Statut",
            s.date_saisie AS "Date"
        FROM staging.volumes_amenes s
        JOIN gold.dim_etage_pression e ON s.id_etage = e.id_etage
        ORDER BY s.annee DESC, s.mois DESC, e.nom_etage
        LIMIT 100
    """, engine)
    
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True,
                    column_config={
                        "Vol Amene": st.column_config.NumberColumn(format="%.0f"),
                        "Date": st.column_config.DatetimeColumn(format="DD/MM/YY HH:mm")
                    })
        
        csv = df.to_csv(index=False, sep=';').encode('utf-8-sig')
        st.download_button("Telecharger CSV", csv, 
                          f"volumes_amenes_{datetime.now().strftime('%Y%m%d')}.csv",
                          "text/csv")
except Exception as e:
    st.error(str(e))