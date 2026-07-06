"""
Saisie des Indicateurs de Performance DP
Remplace le fichier Excel "Indicateurs de Performance - DP"
"""

import streamlit as st
from datetime import datetime

from streamlit_app.auth.simple_auth import (
    check_authentication, show_login_page,
    show_user_info_sidebar, get_current_user,
    user_can_validate
)
from streamlit_app.db.queries import (
    get_provinces, get_centres, get_types_indicateurs,
    insert_indicateur_dp, get_indicateurs_saisis
)
from streamlit_app.utils.validators import valider_indicateur, valider_annee_mois
from streamlit_app.utils.audit import log_action
from streamlit_app.utils.helpers import nom_mois


st.set_page_config(page_title="Indicateurs DP", page_icon="📊", layout="wide")

if not check_authentication():
    show_login_page()
    st.stop()

show_user_info_sidebar()
user = get_current_user()


# ============================================================
# HEADER
# ============================================================
st.title("Saisie des Indicateurs DP")
st.caption("21 indicateurs mensuels par province et centre")
st.markdown("---")


# ============================================================
# ETAPE 1 : CONTEXTE
# ============================================================
st.subheader("1. Selectionner le contexte")

with st.container(border=True):
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        df_provinces = get_provinces()
        
        if df_provinces.empty:
            st.error("Aucune province disponible")
            st.stop()
        
        province_sel = st.selectbox("Province", df_provinces['nom_province'].tolist())
        id_province = int(
            df_provinces[df_provinces['nom_province'] == province_sel]['id_province'].values[0]
        )
    
    with col2:
        df_centres = get_centres(id_province)
        if not df_centres.empty:
            centre_opt = ["-- Global Province --"] + df_centres['nom_centre'].tolist()
            centre_sel = st.selectbox("Centre", centre_opt)
            id_centre = None if centre_sel == "-- Global Province --" else int(
                df_centres[df_centres['nom_centre'] == centre_sel]['id_centre'].values[0]
            )
        else:
            id_centre = None
            centre_sel = "Global"
            st.warning("Aucun centre defini pour cette province")
    
    with col3:
        annee = st.selectbox("Annee", list(range(2024, 2028)), index=2)
    
    with col4:
        mois = st.selectbox(
            "Mois",
            list(range(1, 13)),
            format_func=nom_mois,
            index=datetime.now().month - 1
        )


# ============================================================
# INFO MODE
# ============================================================
if user_can_validate():
    st.success("**Mode Administrateur** : Vos saisies sont validees directement.")
else:
    st.info("**Mode Agent** : Vos saisies seront soumises pour validation.")


# ============================================================
# CHARGEMENT
# ============================================================
try:
    valeurs_existantes = get_indicateurs_saisis(id_province, id_centre, annee, mois)
    nb_deja = len(valeurs_existantes)
except Exception:
    valeurs_existantes = {}
    nb_deja = 0

if nb_deja > 0:
    st.caption(f"{nb_deja} valeur(s) deja saisie(s) pour ce contexte (pre-remplies)")


# ============================================================
# ETAPE 2 : FORMULAIRE
# ============================================================
st.subheader("2. Saisir les valeurs")

df_indicateurs = get_types_indicateurs()
categories = df_indicateurs['categorie'].unique()

with st.form("form_indicateurs"):
    valeurs_saisies = {}
    
    for categorie in categories:
        ind_cat = df_indicateurs[df_indicateurs['categorie'] == categorie]
        
        with st.expander(f"**{categorie}** ({len(ind_cat)} indicateurs)", expanded=True):
            cols = st.columns(3)
            
            for idx, (_, ind) in enumerate(ind_cat.iterrows()):
                with cols[idx % 3]:
                    val = valeurs_existantes.get(ind['code_indicateur'], 0.0)
                    
                    valeurs_saisies[ind['code_indicateur']] = st.number_input(
                        f"{ind['libelle_indicateur']} ({ind['unite']})",
                        value=float(val) if val else 0.0,
                        min_value=0.0,
                        step=0.01,
                        key=f"ind_{ind['code_indicateur']}"
                    )
    
    st.markdown("---")
    commentaire = st.text_area("Commentaire (optionnel)", height=60)
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        submit_attente = st.form_submit_button(
            "Soumettre",
            use_container_width=True
        )
    
    with col2:
        if user_can_validate():
            submit_valide = st.form_submit_button(
                "Valider directement",
                type="primary",
                use_container_width=True
            )
        else:
            submit_valide = False


# ============================================================
# TRAITEMENT
# ============================================================
if submit_attente or submit_valide:
    ok, msg = valider_annee_mois(annee, mois)
    if not ok:
        st.error(msg)
        st.stop()
    
    statut = "VALIDE" if (submit_valide and user_can_validate()) else "EN_ATTENTE"
    
    nb_ok = 0
    erreurs = []
    
    with st.spinner("Enregistrement..."):
        for code, valeur in valeurs_saisies.items():
            ok, msg = valider_indicateur(code, valeur)
            if not ok:
                erreurs.append(f"{code}: {msg}")
                continue
            
            try:
                data = {
                    'id_province': id_province,
                    'id_centre': id_centre,
                    'code_indicateur': code,
                    'annee': annee,
                    'mois': mois,
                    'valeur': valeur if valeur > 0 else None,
                    'commentaire': commentaire,
                    'saisi_par': user['username'],
                    'statut': statut
                }
                
                id_saisie, _ = insert_indicateur_dp(data)
                nb_ok += 1
                
                log_action(user['username'], 'INSERT', 'staging.indicateurs_dp', id_saisie)
            except Exception as e:
                erreurs.append(f"{code}: {str(e)[:80]}")
    
    if erreurs:
        with st.expander(f"{len(erreurs)} erreur(s)"):
            for e in erreurs:
                st.error(e)
    
    if nb_ok > 0:
        if statut == "VALIDE":
            st.success(f"**{nb_ok} indicateurs valides et enregistres !**")
            st.balloons()
        else:
            st.success(
                f"**{nb_ok} indicateurs soumis pour validation.**\n\n"
                f"L'administrateur sera notifie pour valider ou rejeter."
            )