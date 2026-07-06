"""
Administration - Validation des Saisies par Date
Reserve a l'administrateur uniquement
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from streamlit_app.auth.simple_auth import (
    check_authentication, show_login_page,
    show_user_info_sidebar, get_current_user,
    user_can_administer
)
from streamlit_app.db.connection import get_engine, get_db_connection
from streamlit_app.utils.audit import log_action
from streamlit_app.utils.helpers import nom_mois


st.set_page_config(page_title="Administration", page_icon="⚙️", layout="wide")

if not check_authentication():
    show_login_page()
    st.stop()

show_user_info_sidebar()
user = get_current_user()


# CONTROLE ACCES
if not user_can_administer():
    st.error("Acces refuse")
    st.info("Cette page est reservee aux administrateurs uniquement.")
    st.stop()


st.title("Administration - Validation des Saisies")
st.caption("Valider ou rejeter les saisies soumises par les agents")
st.markdown("---")


engine = get_engine()


# ============================================================
# FONCTIONS
# ============================================================
def valider_saisie(table, id_saisie, action, valideur, raison=""):
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            if action == "VALIDE":
                cur.execute(f"""
                    UPDATE {table}
                    SET statut = 'VALIDE', 
                        modifie_par = %s, 
                        date_modification = NOW()
                    WHERE id_saisie = %s
                """, (valideur, id_saisie))
            else:
                cur.execute(f"""
                    UPDATE {table}
                    SET statut = 'REJETE', 
                        commentaire = COALESCE(commentaire, '') || ' [REJETE: ' || %s || ']',
                        modifie_par = %s, 
                        date_modification = NOW()
                    WHERE id_saisie = %s
                """, (raison, valideur, id_saisie))
            conn.commit()
        log_action(valideur, action, table, id_saisie)
        return True
    except Exception as e:
        st.error(str(e))
        return False


# ============================================================
# COMPTEURS EN HAUT
# ============================================================
try:
    counts = {
        'ind': pd.read_sql("SELECT COUNT(*) as n FROM staging.indicateurs_dp WHERE statut='EN_ATTENTE'", engine)['n'][0],
        'rec': pd.read_sql("SELECT COUNT(*) as n FROM staging.reclamations_dp WHERE statut='EN_ATTENTE'", engine)['n'][0],
        'rend': pd.read_sql("SELECT COUNT(*) as n FROM staging.rendements_etage WHERE statut='EN_ATTENTE'", engine)['n'][0],
        'vol': pd.read_sql("SELECT COUNT(*) as n FROM staging.volumes_amenes WHERE statut='EN_ATTENTE'", engine)['n'][0],
        'lin': pd.read_sql("SELECT COUNT(*) as n FROM staging.lineaires WHERE statut='EN_ATTENTE'", engine)['n'][0],
        'mat': pd.read_sql("SELECT COUNT(*) as n FROM staging.matrice_affectation WHERE statut='EN_ATTENTE'", engine)['n'][0],
    }
    total = sum(counts.values())
    
    st.info(f"**Total : {total} saisie(s) en attente**")
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Indicateurs", counts['ind'])
    col2.metric("Reclamations", counts['rec'])
    col3.metric("Rendements", counts['rend'])
    col4.metric("Volumes", counts['vol'])
    col5.metric("Lineaires", counts['lin'])
    col6.metric("Matrice", counts['mat'])

except Exception as e:
    st.error(f"Erreur: {e}")
    st.stop()


st.markdown("---")


# ============================================================
# ONGLETS PAR TYPE
# ============================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    f"Indicateurs ({counts['ind']})", 
    f"Reclamations ({counts['rec']})", 
    f"Rendements ({counts['rend']})",
    f"Volumes ({counts['vol']})",
    f"Lineaires ({counts['lin']})",
    f"Matrice ({counts['mat']})"
])


def afficher_saisies_par_date(tab, table_nom, query, cle):
    """Afficher les saisies groupees par date"""
    with tab:
        try:
            df = pd.read_sql(query, engine)
            
            if df.empty:
                st.success("Aucune saisie en attente pour ce type")
                return
            
            # Convertir date_saisie en date (sans heure)
            df['date_seule'] = pd.to_datetime(df['date_saisie']).dt.date
            
            # Grouper par date
            dates = sorted(df['date_seule'].unique(), reverse=True)
            
            # Bouton valider tout
            col_all1, col_all2 = st.columns(2)
            with col_all1:
                if st.button(f"VALIDER TOUT ({len(df)})", 
                           type="primary", key=f"all_v_{cle}"):
                    nb = 0
                    for _, row in df.iterrows():
                        if valider_saisie(table_nom, row['id_saisie'], 'VALIDE', user['username']):
                            nb += 1
                    st.success(f"{nb} saisies validees")
                    st.rerun()
            
            with col_all2:
                if st.button(f"REJETER TOUT ({len(df)})", key=f"all_r_{cle}"):
                    nb = 0
                    for _, row in df.iterrows():
                        if valider_saisie(table_nom, row['id_saisie'], 'REJETE', 
                                        user['username'], "Rejete en masse"):
                            nb += 1
                    st.warning(f"{nb} saisies rejetees")
                    st.rerun()
            
            st.markdown("---")
            
            # Grouper par date
            for date_g in dates:
                df_date = df[df['date_seule'] == date_g]
                
                with st.expander(
                    f"**{date_g.strftime('%d/%m/%Y')}** - {len(df_date)} saisie(s)",
                    expanded=True
                ):
                    # Boutons valider/rejeter cette date
                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        if st.button(f"Valider tout du {date_g.strftime('%d/%m')}",
                                   key=f"vd_{cle}_{date_g}", type="primary",
                                   use_container_width=True):
                            nb = 0
                            for _, row in df_date.iterrows():
                                if valider_saisie(table_nom, row['id_saisie'], 
                                                'VALIDE', user['username']):
                                    nb += 1
                            st.success(f"{nb} saisies validees")
                            st.rerun()
                    
                    with col_d2:
                        if st.button(f"Rejeter tout du {date_g.strftime('%d/%m')}",
                                   key=f"rd_{cle}_{date_g}",
                                   use_container_width=True):
                            nb = 0
                            for _, row in df_date.iterrows():
                                if valider_saisie(table_nom, row['id_saisie'],
                                                'REJETE', user['username'],
                                                f"Rejete groupe du {date_g}"):
                                    nb += 1
                            st.warning(f"{nb} saisies rejetees")
                            st.rerun()
                    
                    st.markdown("---")
                    
                    # Afficher chaque saisie individuellement
                    for _, row in df_date.iterrows():
                        with st.container(border=True):
                            col_info, col_v, col_r = st.columns([3, 1, 1])
                            
                            with col_info:
                                # Construire info selon type
                                info_html = "<div style='font-size:0.9rem;'>"
                                
                                cols_to_show = [c for c in row.index 
                                              if c not in ['id_saisie', 'date_saisie', 'date_seule']]
                                
                                for c in cols_to_show:
                                    val = row[c]
                                    if val is not None and str(val) != 'nan':
                                        info_html += f"<b>{c}</b>: {val} | "
                                
                                info_html = info_html.rstrip(" | ") + "</div>"
                                info_html += f"<div style='color:#666; font-size:0.75rem; margin-top:0.3rem;'>"
                                info_html += f"ID: {row['id_saisie']} | "
                                info_html += f"Heure: {row['date_saisie'].strftime('%H:%M:%S')}</div>"
                                
                                st.markdown(info_html, unsafe_allow_html=True)
                            
                            with col_v:
                                if st.button("✅ Valider", 
                                           key=f"v_{cle}_{row['id_saisie']}",
                                           type="primary",
                                           use_container_width=True):
                                    if valider_saisie(table_nom, row['id_saisie'], 
                                                    'VALIDE', user['username']):
                                        st.rerun()
                            
                            with col_r:
                                if st.button("❌ Rejeter", 
                                           key=f"r_{cle}_{row['id_saisie']}",
                                           use_container_width=True):
                                    if valider_saisie(table_nom, row['id_saisie'],
                                                    'REJETE', user['username'],
                                                    "Rejete individuellement"):
                                        st.rerun()
        
        except Exception as e:
            st.error(str(e))


# TAB 1 : Indicateurs
afficher_saisies_par_date(tab1, 'staging.indicateurs_dp', """
    SELECT s.id_saisie, p.nom_province as province, 
           COALESCE(c.nom_centre, 'Global') as centre,
           t.libelle_indicateur as indicateur, s.valeur, 
           s.annee, s.mois, s.saisi_par, s.date_saisie
    FROM staging.indicateurs_dp s
    JOIN gold.dim_province p ON s.id_province = p.id_province
    LEFT JOIN gold.dim_centre c ON s.id_centre = c.id_centre
    JOIN gold.dim_type_indicateur_dp t ON s.code_indicateur = t.code_indicateur
    WHERE s.statut = 'EN_ATTENTE'
    ORDER BY s.date_saisie DESC
""", 'ind')

# TAB 2 : Reclamations
afficher_saisies_par_date(tab2, 'staging.reclamations_dp', """
    SELECT s.id_saisie, p.nom_province as province, 
           t.libelle_reclamation as reclamation,
           s.nombre, s.temps_coupure_h, s.delai_traitement_j,
           s.annee, s.mois, s.saisi_par, s.date_saisie
    FROM staging.reclamations_dp s
    JOIN gold.dim_province p ON s.id_province = p.id_province
    JOIN gold.dim_type_reclamation t ON s.code_type_reclam = t.code_type
    WHERE s.statut = 'EN_ATTENTE'
    ORDER BY s.date_saisie DESC
""", 'rec')

# TAB 3 : Rendements
afficher_saisies_par_date(tab3, 'staging.rendements_etage', """
    SELECT s.id_saisie, e.nom_etage as etage, s.nombre_clients,
           s.volume_facture_m3 as vol_facture, s.volume_amene_m3 as vol_amene,
           s.rendement, s.annee, s.mois, s.saisi_par, s.date_saisie
    FROM staging.rendements_etage s
    JOIN gold.dim_etage_pression e ON s.id_etage = e.id_etage
    WHERE s.statut = 'EN_ATTENTE'
    ORDER BY s.date_saisie DESC
""", 'rend')

# TAB 4 : Volumes
afficher_saisies_par_date(tab4, 'staging.volumes_amenes', """
    SELECT s.id_saisie, e.nom_etage as etage, s.volume_m3 as volume,
           s.annee, s.mois, s.saisi_par, s.date_saisie
    FROM staging.volumes_amenes s
    JOIN gold.dim_etage_pression e ON s.id_etage = e.id_etage
    WHERE s.statut = 'EN_ATTENTE'
    ORDER BY s.date_saisie DESC
""", 'vol')

# TAB 5 : Lineaires
afficher_saisies_par_date(tab5, 'staging.lineaires', """
    SELECT s.id_saisie, s.type_element as type, s.nom_element as nom, 
           s.lineaire_km as km, s.annee_reference as annee, 
           s.saisi_par, s.date_saisie
    FROM staging.lineaires s
    WHERE s.statut = 'EN_ATTENTE'
    ORDER BY s.date_saisie DESC
""", 'lin')

# TAB 6 : Matrice
afficher_saisies_par_date(tab6, 'staging.matrice_affectation', """
    SELECT s.id_saisie, s.num_loc as loc, s.num_sec as sec, 
           s.code_etage_num as code_etage, s.nom_etage,
           s.saisi_par, s.date_saisie
    FROM staging.matrice_affectation s
    WHERE s.statut = 'EN_ATTENTE'
    ORDER BY s.date_saisie DESC
""", 'mat')