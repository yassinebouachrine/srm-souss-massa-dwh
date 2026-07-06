"""
Saisie de la Matrice d'Affectation Loc/Sec/Etage
Reproduit le fichier: Matrice Affectation Loc_Sec Etage.xlsx
Colonnes: loc, sec, code_etage, code_loc_sec, NOM_ETAGE
"""

import streamlit as st
import pandas as pd
from streamlit_app.auth.simple_auth import (
    check_authentication, show_login_page,
    show_user_info_sidebar, get_current_user, user_can_validate
)
from streamlit_app.db.connection import get_db_connection, get_engine
from streamlit_app.utils.audit import log_action


st.set_page_config(page_title="Matrice Affectation", page_icon="🗺️", layout="wide")

if not check_authentication():
    show_login_page()
    st.stop()

show_user_info_sidebar()
user = get_current_user()


st.title("Matrice d'Affectation")
st.caption("Correspondance Localite / Secteur / Etage de Pression (fichier Excel: Matrice Affectation Loc_Sec Etage)")
st.markdown("---")


if user_can_validate():
    st.success("**Mode Administrateur** : Validation directe")
else:
    st.info("**Mode Agent** : Soumission pour validation")


# Formulaire
st.subheader("Ajouter une affectation")

with st.form("form_matrice"):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        num_loc = st.number_input(
            "loc (numero localite)", 
            min_value=1, step=1,
            help="Colonne 'loc' du fichier Excel"
        )
    
    with col2:
        num_sec = st.number_input(
            "sec (numero section)", 
            min_value=1, step=1,
            help="Colonne 'sec' du fichier Excel"
        )
    
    with col3:
        code_etage = st.number_input(
            "code_etage", 
            min_value=1, step=1,
            help="Colonne 'code_etage' du fichier Excel"
        )
    
    col4, col5 = st.columns(2)
    
    with col4:
        code_loc_sec = st.text_input(
            "code_loc_sec (auto)",
            value=f"{code_etage}_{num_sec}",
            help="Genere automatiquement : code_etage_num_sec"
        )
    
    with col5:
        nom_etage = st.text_input(
            "NOM_ETAGE",
            placeholder="Ex: TAGADIRT 129, TASSILA 75...",
            help="Colonne 'NOM_ETAGE' du fichier Excel"
        )
    
    commentaire = st.text_area("Commentaire", height=60)
    submit = st.form_submit_button("Enregistrer", type="primary", use_container_width=True)


if submit:
    if not nom_etage:
        st.warning("Veuillez saisir le nom de l'etage")
    else:
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
            
            if statut == "VALIDE":
                st.success(f"Affectation enregistree et validee")
                st.balloons()
            else:
                st.success(f"Affectation soumise pour validation")
        except Exception as e:
            st.error(str(e))


# Historique
st.markdown("---")
st.subheader("Historique - Format Excel")

engine = get_engine()

try:
    df = pd.read_sql("""
        SELECT 
            num_loc AS "loc",
            num_sec AS "sec",
            code_etage_num AS "code_etage",
            code_loc_sec AS "code_loc_sec",
            nom_etage AS "NOM_ETAGE",
            statut AS "Statut",
            saisi_par AS "Utilisateur",
            date_saisie AS "Date"
        FROM staging.matrice_affectation
        ORDER BY code_etage_num, num_sec
    """, engine)
    
    if not df.empty:
        st.caption(f"{len(df)} affectation(s)")
        st.dataframe(df, use_container_width=True, hide_index=True,
                    column_config={
                        "Date": st.column_config.DatetimeColumn(format="DD/MM/YY HH:mm")
                    })
        
        csv = df.to_csv(index=False, sep=';').encode('utf-8-sig')
        st.download_button("Telecharger CSV (format Excel)", csv,
                          "matrice_affectation.csv", "text/csv")
    else:
        st.info("Aucune affectation saisie")
except Exception as e:
    st.error(str(e))