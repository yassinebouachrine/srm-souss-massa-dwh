"""
Dashboard Principal - Vue globale de toutes les saisies
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from streamlit_app.auth.simple_auth import (
    check_authentication, show_login_page,
    show_user_info_sidebar, get_current_user,
    user_can_validate
)
from streamlit_app.db.connection import test_connection, get_engine


st.set_page_config(page_title="Dashboard", page_icon="🏠", layout="wide")

if not check_authentication():
    show_login_page()
    st.stop()

show_user_info_sidebar()
user = get_current_user()


# HEADER
col1, col2 = st.columns([3, 1])
with col1:
    st.title("Dashboard Principal")
    st.caption(f"Bienvenue {user['nom_complet']} - {user['role']}")
with col2:
    ok, _ = test_connection()
    st.success("Base connectee" if ok else "Erreur BD", icon="✅" if ok else "❌")

st.markdown("---")


# Charger stats
try:
    engine = get_engine()
    
    stats = {
        'provinces': pd.read_sql("SELECT COUNT(*) as n FROM gold.dim_province", engine)['n'][0],
        'centres': pd.read_sql("SELECT COUNT(*) as n FROM gold.dim_centre", engine)['n'][0],
        'etages': pd.read_sql("SELECT COUNT(*) as n FROM gold.dim_etage_pression", engine)['n'][0],
        'indicateurs_types': pd.read_sql("SELECT COUNT(*) as n FROM gold.dim_type_indicateur_dp", engine)['n'][0],
    }
    
    # Saisies par type
    saisies = {
        'indicateurs': pd.read_sql("SELECT COUNT(*) as n FROM staging.indicateurs_dp", engine)['n'][0],
        'reclamations': pd.read_sql("SELECT COUNT(*) as n FROM staging.reclamations_dp", engine)['n'][0],
        'rendements': pd.read_sql("SELECT COUNT(*) as n FROM staging.rendements_etage", engine)['n'][0],
        'volumes': pd.read_sql("SELECT COUNT(*) as n FROM staging.volumes_amenes", engine)['n'][0],
        'lineaires': pd.read_sql("SELECT COUNT(*) as n FROM staging.lineaires", engine)['n'][0],
        'matrice': pd.read_sql("SELECT COUNT(*) as n FROM staging.matrice_affectation", engine)['n'][0],
    }
    
    # En attente TOTAL
    nb_attente_ind = pd.read_sql("SELECT COUNT(*) as n FROM staging.indicateurs_dp WHERE statut='EN_ATTENTE'", engine)['n'][0]
    nb_attente_rec = pd.read_sql("SELECT COUNT(*) as n FROM staging.reclamations_dp WHERE statut='EN_ATTENTE'", engine)['n'][0]
    nb_attente_rend = pd.read_sql("SELECT COUNT(*) as n FROM staging.rendements_etage WHERE statut='EN_ATTENTE'", engine)['n'][0]
    nb_attente_vol = pd.read_sql("SELECT COUNT(*) as n FROM staging.volumes_amenes WHERE statut='EN_ATTENTE'", engine)['n'][0]
    nb_attente_lin = pd.read_sql("SELECT COUNT(*) as n FROM staging.lineaires WHERE statut='EN_ATTENTE'", engine)['n'][0]
    nb_attente_mat = pd.read_sql("SELECT COUNT(*) as n FROM staging.matrice_affectation WHERE statut='EN_ATTENTE'", engine)['n'][0]
    
    total_attente = nb_attente_ind + nb_attente_rec + nb_attente_rend + nb_attente_vol + nb_attente_lin + nb_attente_mat

except Exception as e:
    st.error(f"Erreur: {e}")
    st.stop()


# ALERTE ADMIN
if user_can_validate() and total_attente > 0:
    st.warning(
        f"**{total_attente} saisie(s) en attente de validation** - "
        f"Consultez la page Administration."
    )


# METRIQUES
st.subheader("Infrastructure")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Provinces", stats['provinces'])
col2.metric("Centres", stats['centres'])
col3.metric("Etages Pression", stats['etages'])
col4.metric("Types Indicateurs", stats['indicateurs_types'])


st.subheader("Volume des Saisies par Module")
col1, col2, col3 = st.columns(3)
col1.metric("Indicateurs DP", saisies['indicateurs'])
col2.metric("Reclamations", saisies['reclamations'])
col3.metric("Rendements Etages", saisies['rendements'])

col1, col2, col3 = st.columns(3)
col1.metric("Volumes Amenes", saisies['volumes'])
col2.metric("Lineaires", saisies['lineaires'])
col3.metric("Matrice Affectation", saisies['matrice'])


st.subheader("En Attente de Validation")
col1, col2, col3 = st.columns(3)
col1.metric("Indicateurs", nb_attente_ind)
col2.metric("Reclamations", nb_attente_rec)
col3.metric("Rendements", nb_attente_rend)

col1, col2, col3 = st.columns(3)
col1.metric("Volumes", nb_attente_vol)
col2.metric("Lineaires", nb_attente_lin)
col3.metric("Matrice", nb_attente_mat)


st.markdown("---")


# HISTORIQUE UNIFIE
st.subheader("Consultation des Saisies")

col1, col2, col3 = st.columns(3)
with col1:
    type_data = st.selectbox("Type", 
        ["Indicateurs DP", "Reclamations", "Rendements", "Volumes", "Lineaires", "Matrice"])
with col2:
    filtre_statut = st.selectbox("Statut",
        ["Tous", "EN_ATTENTE", "VALIDE", "REJETE", "BROUILLON"])
with col3:
    filtre_periode = st.selectbox("Periode",
        ["Tout", "Aujourd'hui", "7 jours", "30 jours"])


# Requetes selon type
queries = {
    "Indicateurs DP": """
        SELECT s.id_saisie, p.nom_province, COALESCE(c.nom_centre, 'Global') as centre,
               t.libelle_indicateur, t.unite, s.valeur, s.annee, s.mois,
               s.statut, s.saisi_par, s.date_saisie
        FROM staging.indicateurs_dp s
        JOIN gold.dim_province p ON s.id_province = p.id_province
        LEFT JOIN gold.dim_centre c ON s.id_centre = c.id_centre
        JOIN gold.dim_type_indicateur_dp t ON s.code_indicateur = t.code_indicateur
        WHERE 1=1
    """,
    "Reclamations": """
        SELECT s.id_saisie, p.nom_province, COALESCE(c.nom_centre, 'Global') as centre,
               t.libelle_reclamation as element, s.nombre, s.temps_coupure_h, s.delai_traitement_j,
               s.annee, s.mois, s.statut, s.saisi_par, s.date_saisie
        FROM staging.reclamations_dp s
        JOIN gold.dim_province p ON s.id_province = p.id_province
        LEFT JOIN gold.dim_centre c ON s.id_centre = c.id_centre
        JOIN gold.dim_type_reclamation t ON s.code_type_reclam = t.code_type
        WHERE 1=1
    """,
    "Rendements": """
        SELECT s.id_saisie, e.nom_etage, s.nombre_clients,
               s.volume_facture_m3, s.volume_amene_m3, s.rendement * 100 as rendement_pct,
               s.annee, s.mois, s.statut, s.saisi_par, s.date_saisie
        FROM staging.rendements_etage s
        JOIN gold.dim_etage_pression e ON s.id_etage = e.id_etage
        WHERE 1=1
    """,
    "Volumes": """
        SELECT s.id_saisie, e.nom_etage, s.volume_m3, s.annee, s.mois,
               s.statut, s.saisi_par, s.date_saisie
        FROM staging.volumes_amenes s
        JOIN gold.dim_etage_pression e ON s.id_etage = e.id_etage
        WHERE 1=1
    """,
    "Lineaires": """
        SELECT s.id_saisie, s.type_element, s.nom_element, s.lineaire_km, s.lineaire_m,
               s.annee_reference, s.statut, s.saisi_par, s.date_saisie
        FROM staging.lineaires s WHERE 1=1
    """,
    "Matrice": """
        SELECT s.id_saisie, s.num_loc, s.num_sec, s.code_etage_num, s.code_loc_sec,
               s.nom_etage, s.statut, s.saisi_par, s.date_saisie
        FROM staging.matrice_affectation s WHERE 1=1
    """
}

query = queries[type_data]
if filtre_statut != "Tous":
    query += f" AND s.statut = '{filtre_statut}'"

today = datetime.now()
if filtre_periode == "Aujourd'hui":
    query += f" AND s.date_saisie >= '{today.strftime('%Y-%m-%d')}'"
elif filtre_periode == "7 jours":
    query += f" AND s.date_saisie >= '{(today - timedelta(days=7)).strftime('%Y-%m-%d')}'"
elif filtre_periode == "30 jours":
    query += f" AND s.date_saisie >= '{(today - timedelta(days=30)).strftime('%Y-%m-%d')}'"

query += " ORDER BY s.date_saisie DESC LIMIT 200"

try:
    df = pd.read_sql(query, engine)
    st.caption(f"{len(df)} enregistrement(s)")
    
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True,
                    column_config={
                        "date_saisie": st.column_config.DatetimeColumn(format="DD/MM/YY HH:mm")
                    })
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Telecharger CSV", csv, 
                          f"{type_data}_{today.strftime('%Y%m%d')}.csv", "text/csv")
    else:
        st.info("Aucune donnee")
except Exception as e:
    st.error(str(e))