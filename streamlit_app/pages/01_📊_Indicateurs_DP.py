"""
============================================================
Page 1 : Saisie des Indicateurs de Performance DP
============================================================
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from streamlit_app.auth.simple_auth import (
    check_authentication, show_login_page, 
    show_user_info_sidebar, get_current_user, check_permission_province
)
from streamlit_app.db.queries import (
    get_provinces, get_centres, get_types_indicateurs,
    insert_indicateur_dp, get_indicateurs_saisis
)
from streamlit_app.utils.validators import valider_indicateur, valider_annee_mois
from streamlit_app.utils.audit import log_action
from streamlit_app.utils.helpers import nom_mois, mois_avec_noms


# ============================================================
# CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="Indicateurs DP",
    page_icon="📊",
    layout="wide"
)


# ============================================================
# AUTHENTIFICATION
# ============================================================
if not check_authentication():
    show_login_page()
    st.stop()

show_user_info_sidebar()
user = get_current_user()


# ============================================================
# HEADER
# ============================================================
st.title("📊 Saisie des Indicateurs de Performance DP")
st.markdown("Saisir les **21 indicateurs mensuels** par province et centre")
st.markdown("---")


# ============================================================
# SIDEBAR - FILTRES
# ============================================================
with st.sidebar:
    st.markdown("### 🔍 Contexte de saisie")
    
    # Charger provinces
    df_provinces = get_provinces()
    
    # Filtrer selon permissions
    if user['provinces_autorisees'] != "ALL":
        df_provinces = df_provinces[
            df_provinces['nom_province'].isin(user['provinces_autorisees'])
        ]
    
    if df_provinces.empty:
        st.error("Aucune province autorisée")
        st.stop()
    
    # Sélection province
    province_selectionnee = st.selectbox(
        "🏛️ Province",
        options=df_provinces['nom_province'].tolist()
    )
    id_province = int(df_provinces[
        df_provinces['nom_province'] == province_selectionnee
    ]['id_province'].values[0])
    
    # Charger centres
    df_centres = get_centres(id_province)
    
    if not df_centres.empty:
        centre_options = ["-- Global Province --"] + df_centres['nom_centre'].tolist()
        centre_selectionne = st.selectbox("🏘️ Centre (optionnel)", options=centre_options)
        
        if centre_selectionne == "-- Global Province --":
            id_centre = None
        else:
            id_centre = int(df_centres[
                df_centres['nom_centre'] == centre_selectionne
            ]['id_centre'].values[0])
    else:
        id_centre = None
        st.info("Aucun centre défini pour cette province")
    
    # Période
    st.markdown("### 📅 Période")
    col1, col2 = st.columns(2)
    with col1:
        annee = st.selectbox(
            "Année",
            options=list(range(2024, 2027)),
            index=2  # 2026 par défaut
        )
    with col2:
        mois = st.selectbox(
            "Mois",
            options=list(range(1, 13)),
            format_func=lambda x: nom_mois(x),
            index=datetime.now().month - 1
        )


# ============================================================
# FORMULAIRE DE SAISIE
# ============================================================
st.markdown(f"### 📝 Saisie pour : **{province_selectionnee}**")
if id_centre:
    st.markdown(f"**Centre** : {centre_selectionne}")
st.markdown(f"**Période** : {nom_mois(mois)} {annee}")

# Charger les indicateurs
df_indicateurs = get_types_indicateurs()

# Charger valeurs existantes
try:
    valeurs_existantes = get_indicateurs_saisis(id_province, id_centre, annee, mois)
except Exception as e:
    st.warning(f"Erreur chargement valeurs existantes: {e}")
    valeurs_existantes = {}

# Grouper par catégorie
categories = df_indicateurs['categorie'].unique()

# Formulaire
with st.form("form_indicateurs"):
    st.info("💡 Remplissez les indicateurs (les valeurs existantes sont pré-remplies)")
    
    valeurs_saisies = {}
    
    for categorie in categories:
        indicateurs_cat = df_indicateurs[df_indicateurs['categorie'] == categorie]
        
        with st.expander(f"📁 **{categorie}** ({len(indicateurs_cat)} indicateurs)", expanded=True):
            cols = st.columns(3)
            
            for idx, (_, ind) in enumerate(indicateurs_cat.iterrows()):
                col = cols[idx % 3]
                
                with col:
                    valeur_existante = valeurs_existantes.get(
                        ind['code_indicateur'], 
                        0.0
                    )
                    
                    valeur = st.number_input(
                        f"**{ind['libelle_indicateur']}** ({ind['unite']})",
                        value=float(valeur_existante) if valeur_existante else 0.0,
                        min_value=0.0,
                        step=0.01,
                        key=f"ind_{ind['code_indicateur']}",
                        help=f"Code: {ind['code_indicateur']}"
                    )
                    valeurs_saisies[ind['code_indicateur']] = valeur
    
    st.markdown("---")
    commentaire = st.text_area("💬 Commentaire (optionnel)", height=80)
    
    # Boutons
    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        submit_brouillon = st.form_submit_button(
            "💾 Enregistrer brouillon", 
            type="secondary",
            use_container_width=True
        )
    with col2:
        submit_valide = st.form_submit_button(
            "✅ Valider et envoyer", 
            type="primary",
            use_container_width=True
        )


# ============================================================
# TRAITEMENT SOUMISSION
# ============================================================
if submit_brouillon or submit_valide:
    # Validation période
    valide, msg = valider_annee_mois(annee, mois)
    if not valide:
        st.error(f"❌ {msg}")
        st.stop()
    
    statut = "VALIDE" if submit_valide else "BROUILLON"
    
    nb_insertions = 0
    nb_maj = 0
    erreurs = []
    
    progress = st.progress(0)
    status = st.empty()
    
    for i, (code, valeur) in enumerate(valeurs_saisies.items()):
        progress.progress((i + 1) / len(valeurs_saisies))
        status.text(f"Traitement de {code}...")
        
        # Validation métier
        valide, msg = valider_indicateur(code, valeur)
        if not valide:
            erreurs.append(f"{code}: {msg}")
            continue
        
        # Insertion
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
            
            id_saisie, inserted = insert_indicateur_dp(data)
            
            if inserted:
                nb_insertions += 1
            else:
                nb_maj += 1
            
            # Audit
            log_action(
                utilisateur=user['username'],
                action='INSERT' if inserted else 'UPDATE',
                table_cible='staging.indicateurs_dp',
                id_enregistrement=id_saisie,
                donnees_apres={'code': code, 'valeur': valeur, 'statut': statut}
            )
        
        except Exception as e:
            erreurs.append(f"{code}: {e}")
    
    progress.empty()
    status.empty()
    
    # Résultat
    if erreurs:
        st.error(f"❌ {len(erreurs)} erreur(s) :")
        for err in erreurs:
            st.write(f"- {err}")
    
    if nb_insertions > 0 or nb_maj > 0:
        st.success(
            f"✅ Saisie enregistrée !\n\n"
            f"- **{nb_insertions}** nouvelle(s) valeur(s)\n"
            f"- **{nb_maj}** valeur(s) mise(s) à jour\n"
            f"- **Statut** : {statut}"
        )
        
        if submit_valide:
            st.info("🚀 Les données seront intégrées dans le Data Warehouse dans l'heure.")
            st.balloons()


# ============================================================
# HISTORIQUE
# ============================================================
st.markdown("---")
st.markdown("### 📋 Historique des saisies")

try:
    from streamlit_app.db.queries import get_historique_saisies
    df_historique = get_historique_saisies(id_province, id_centre, limit=50)
    
    if not df_historique.empty:
        st.dataframe(
            df_historique,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Aucune saisie pour ce contexte")

except Exception as e:
    st.error(f"Erreur historique: {e}")