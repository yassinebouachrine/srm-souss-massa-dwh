"""
Saisie des Lineaires Reseau
Reproduit les fichiers:
- Lineaire Par etage.xlsx (colonnes: NOM_ETAGE, Lineaire (km))
- Lineaire Par Secteur 2026.xlsx (colonnes: NOM_SEC_HY, Lineaire (m))
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from streamlit_app.auth.simple_auth import (
    check_authentication, show_login_page,
    show_user_info_sidebar, get_current_user, user_can_validate
)
from streamlit_app.db.connection import get_db_connection, get_engine
from streamlit_app.utils.audit import log_action


st.set_page_config(page_title="Lineaires", page_icon="📏", layout="wide")

if not check_authentication():
    show_login_page()
    st.stop()

show_user_info_sidebar()
user = get_current_user()


st.title("Lineaires Reseau")
st.caption("Lineaire par etage ou secteur (fichiers Excel: Lineaire Par etage / Lineaire Par Secteur)")
st.markdown("---")


# Type d'element
type_elem = st.radio(
    "Type d'element",
    ["ETAGE", "SECTEUR"],
    horizontal=True,
    help="ETAGE = fichier 'Lineaire Par etage.xlsx' | SECTEUR = fichier 'Lineaire Par Secteur.xlsx'"
)


if user_can_validate():
    st.success("**Mode Administrateur** : Validation directe")
else:
    st.info("**Mode Agent** : Soumission pour validation")


# Formulaire
st.subheader(f"Ajouter un lineaire de type {type_elem}")

with st.form("form_lineaire"):
    col1, col2 = st.columns(2)
    
    with col1:
        nom = st.text_input(
            "Nom" if type_elem == "ETAGE" else "Nom Secteur (NOM_SEC_HY)",
            placeholder="Ex: ANZA 70" if type_elem == "ETAGE" else "Ex: ADRAR"
        )
    
    with col2:
        annee_ref = st.selectbox("Annee de reference", list(range(2020, 2028)), index=6)
    
    col3, col4 = st.columns(2)
    
    with col3:
        if type_elem == "ETAGE":
            lineaire_km = st.number_input(
                "Lineaire (km)",
                min_value=0.0,
                step=0.1,
                help="Comme dans le fichier Excel"
            )
            lineaire_m = lineaire_km * 1000
        else:
            lineaire_m = st.number_input(
                "Lineaire (m)",
                min_value=0.0,
                step=1.0,
                help="Comme dans le fichier Excel"
            )
            lineaire_km = lineaire_m / 1000
    
    with col4:
        st.markdown("**Equivalent :**")
        if type_elem == "ETAGE":
            st.info(f"{lineaire_m:,.0f} m")
        else:
            st.info(f"{lineaire_km:,.3f} km")
    
    commentaire = st.text_area("Commentaire", height=60)
    submit = st.form_submit_button("Enregistrer", type="primary", use_container_width=True)


if submit:
    if not nom:
        st.warning("Veuillez saisir un nom")
    else:
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
            
            if statut == "VALIDE":
                st.success(f"Lineaire '{nom}' enregistre et valide")
                st.balloons()
            else:
                st.success(f"Lineaire '{nom}' soumis pour validation")
        except Exception as e:
            st.error(str(e))


# Historique
st.markdown("---")
st.subheader("Historique - Format Excel")

engine = get_engine()

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Lineaires par ETAGE")
    try:
        df_etages = pd.read_sql("""
            SELECT 
                nom_element AS "NOM_ETAGE",
                lineaire_km AS "Lineaire (km)",
                statut AS "Statut"
            FROM staging.lineaires
            WHERE type_element = 'ETAGE'
            ORDER BY nom_element
        """, engine)
        
        if not df_etages.empty:
            st.dataframe(df_etages, use_container_width=True, hide_index=True,
                        column_config={
                            "Lineaire (km)": st.column_config.NumberColumn(format="%.3f")
                        })
        else:
            st.info("Aucun etage saisi")
    except Exception as e:
        st.error(str(e))

with col2:
    st.markdown("### Lineaires par SECTEUR")
    try:
        df_secteurs = pd.read_sql("""
            SELECT 
                nom_element AS "NOM_SEC_HY",
                lineaire_m AS "Lineaire (m)",
                statut AS "Statut"
            FROM staging.lineaires
            WHERE type_element = 'SECTEUR'
            ORDER BY nom_element
        """, engine)
        
        if not df_secteurs.empty:
            st.dataframe(df_secteurs, use_container_width=True, hide_index=True,
                        column_config={
                            "Lineaire (m)": st.column_config.NumberColumn(format="%.0f")
                        })
        else:
            st.info("Aucun secteur saisi")
    except Exception as e:
        st.error(str(e))