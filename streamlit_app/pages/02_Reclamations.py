"""
Saisie des Reclamations
Remplace le fichier Excel des reclamations
"""

import streamlit as st
from datetime import datetime

from streamlit_app.auth.simple_auth import (
    check_authentication, show_login_page,
    show_user_info_sidebar, get_current_user, user_can_validate
)
from streamlit_app.db.queries import (
    get_provinces, get_centres, get_types_reclamations, insert_reclamation_dp
)
from streamlit_app.utils.audit import log_action
from streamlit_app.utils.helpers import nom_mois


st.set_page_config(page_title="Reclamations", page_icon="📢", layout="wide")

if not check_authentication():
    show_login_page()
    st.stop()

show_user_info_sidebar()
user = get_current_user()


st.title("Saisie des Reclamations")
st.caption("10 types de reclamations par province et centre")
st.markdown("---")


# Contexte
st.subheader("1. Contexte")
with st.container(border=True):
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        df_prov = get_provinces()
        if df_prov.empty:
            st.error("Aucune province")
            st.stop()
        province = st.selectbox("Province", df_prov['nom_province'].tolist())
        id_prov = int(df_prov[df_prov['nom_province']==province]['id_province'].values[0])
    
    with col2:
        df_c = get_centres(id_prov)
        c_opt = ["-- Global --"] + (df_c['nom_centre'].tolist() if not df_c.empty else [])
        centre = st.selectbox("Centre", c_opt)
        id_centre = None if centre == "-- Global --" else int(
            df_c[df_c['nom_centre']==centre]['id_centre'].values[0])
    
    with col3:
        annee = st.selectbox("Annee", list(range(2024, 2028)), index=2)
    
    with col4:
        mois = st.selectbox("Mois", list(range(1,13)), format_func=nom_mois,
                           index=datetime.now().month-1)


# Info mode
if user_can_validate():
    st.success("**Mode Administrateur** : Validation directe")
else:
    st.info("**Mode Agent** : Soumission pour validation")


# Formulaire
st.subheader("2. Saisir les reclamations")

df_types = get_types_reclamations()

with st.form("form_reclamations"):
    valeurs = {}
    
    # Types comptage
    with st.expander("Reclamations (nombre)", expanded=True):
        comptage = df_types[df_types['est_comptage']==True]
        cols = st.columns(3)
        for idx, (_, r) in enumerate(comptage.iterrows()):
            with cols[idx % 3]:
                valeurs[r['code_type']] = {
                    'nombre': st.number_input(
                        f"{r['libelle_reclamation']}", 
                        min_value=0, step=1,
                        key=f"rec_{r['code_type']}"
                    ),
                    'temps_coupure_h': None,
                    'delai_traitement_j': None
                }
    
    # Types duree
    with st.expander("Durees et delais", expanded=True):
        duree = df_types[df_types['est_duree']==True]
        cols = st.columns(2)
        for idx, (_, r) in enumerate(duree.iterrows()):
            with cols[idx % 2]:
                if r['code_type'] == 'TPS_COUP':
                    val = st.number_input(
                        f"{r['libelle_reclamation']} (heures)",
                        min_value=0.0, step=0.5,
                        key=f"rec_{r['code_type']}"
                    )
                    valeurs[r['code_type']] = {
                        'nombre': None,
                        'temps_coupure_h': val,
                        'delai_traitement_j': None
                    }
                else:
                    val = st.number_input(
                        f"{r['libelle_reclamation']} (jours)",
                        min_value=0.0, step=0.5,
                        key=f"rec_{r['code_type']}"
                    )
                    valeurs[r['code_type']] = {
                        'nombre': None,
                        'temps_coupure_h': None,
                        'delai_traitement_j': val
                    }
    
    st.markdown("---")
    commentaire = st.text_area("Commentaire", height=60)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        submit = st.form_submit_button("Soumettre", use_container_width=True)
    with col2:
        if user_can_validate():
            submit_val = st.form_submit_button("Valider directement", 
                                               type="primary", use_container_width=True)
        else:
            submit_val = False


if submit or submit_val:
    statut = "VALIDE" if (submit_val and user_can_validate()) else "EN_ATTENTE"
    nb_ok = 0
    
    for code, vals in valeurs.items():
        # Ignorer si toutes les valeurs sont nulles/zero
        if (vals['nombre'] is None or vals['nombre'] == 0) and \
           (vals['temps_coupure_h'] is None or vals['temps_coupure_h'] == 0) and \
           (vals['delai_traitement_j'] is None or vals['delai_traitement_j'] == 0):
            continue
        
        try:
            data = {
                'id_province': id_prov, 'id_centre': id_centre,
                'code_type_reclam': code, 'annee': annee, 'mois': mois,
                'nombre': vals['nombre'],
                'temps_coupure_h': vals['temps_coupure_h'],
                'delai_traitement_j': vals['delai_traitement_j'],
                'commentaire': commentaire,
                'saisi_par': user['username'], 'statut': statut
            }
            id_s, _ = insert_reclamation_dp(data)
            log_action(user['username'], 'INSERT', 'staging.reclamations_dp', id_s)
            nb_ok += 1
        except Exception as e:
            st.error(f"{code}: {e}")
    
    if nb_ok > 0:
        if statut == "VALIDE":
            st.success(f"{nb_ok} reclamations validees et enregistrees")
            st.balloons()
        else:
            st.success(
                f"{nb_ok} reclamations soumises pour validation.\n\n"
                f"L'administrateur sera notifie."
            )
    else:
        st.warning("Aucune valeur a enregistrer")