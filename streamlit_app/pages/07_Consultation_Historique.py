"""
Page : Consultation et Modification des Saisies
"""
import streamlit as st
import pandas as pd
from streamlit_app.auth.simple_auth import (
    check_authentication, show_login_page,
    show_user_info_sidebar, get_current_user, user_can_validate
)
from streamlit_app.db.connection import get_engine, get_db_connection
from streamlit_app.db.queries import get_provinces, get_centres
from streamlit_app.utils.audit import log_action
from streamlit_app.utils.helpers import nom_mois

st.set_page_config(page_title="Consultation", page_icon="📈", layout="wide")

if not check_authentication():
    show_login_page()
    st.stop()

show_user_info_sidebar()
user = get_current_user()

st.title("Consultation et Modification")
st.caption("Voir, modifier ou supprimer les saisies existantes")
st.markdown("---")

engine = get_engine()

# Onglets par type
tab1, tab2, tab3 = st.tabs(["Indicateurs DP", "Reclamations", "Rendements"])

# ============================================================
# TAB 1 : Indicateurs DP
# ============================================================
with tab1:
    st.subheader("Indicateurs DP")
    
    # Filtres
    col1, col2, col3 = st.columns(3)
    with col1:
        df_prov = get_provinces()
        if user['provinces_autorisees'] != "ALL":
            df_prov = df_prov[df_prov['nom_province'].isin(user['provinces_autorisees'])]
        prov_opt = ["Toutes"] + df_prov['nom_province'].tolist()
        f_prov = st.selectbox("Province", prov_opt, key="h_prov")
    
    with col2:
        f_statut = st.selectbox("Statut", 
            ["Tous", "EN_ATTENTE", "VALIDE", "REJETE", "BROUILLON"], key="h_stat")
    
    with col3:
        f_user = st.selectbox("Utilisateur",
            ["Tous", user['username']], key="h_user")
    
    # Requete
    query = """
        SELECT s.id_saisie, p.nom_province, COALESCE(c.nom_centre, 'Global') as centre,
               t.libelle_indicateur, t.unite, s.valeur, s.annee, s.mois,
               s.statut, s.saisi_par, s.date_saisie
        FROM staging.indicateurs_dp s
        JOIN gold.dim_province p ON s.id_province = p.id_province
        LEFT JOIN gold.dim_centre c ON s.id_centre = c.id_centre
        JOIN gold.dim_type_indicateur_dp t ON s.code_indicateur = t.code_indicateur
        WHERE 1=1
    """
    if f_prov != "Toutes":
        query += f" AND p.nom_province = '{f_prov}'"
    if f_statut != "Tous":
        query += f" AND s.statut = '{f_statut}'"
    if f_user != "Tous":
        query += f" AND s.saisi_par = '{f_user}'"
    query += " ORDER BY s.date_saisie DESC LIMIT 200"
    
    try:
        df = pd.read_sql(query, engine)
        
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True,
                        column_config={
                            "date_saisie": st.column_config.DatetimeColumn(format="DD/MM/YY HH:mm"),
                            "valeur": st.column_config.NumberColumn(format="%.2f")
                        })
            
            # Modifier une saisie
            st.markdown("---")
            st.subheader("Modifier une saisie")
            
            id_a_modifier = st.number_input("ID de la saisie a modifier", 
                                           min_value=0, step=1, key="mod_id")
            
            if id_a_modifier > 0:
                saisie = df[df['id_saisie'] == id_a_modifier]
                if not saisie.empty:
                    row = saisie.iloc[0]
                    st.info(f"Saisie: {row['libelle_indicateur']} = {row['valeur']} "
                           f"({row['nom_province']}, {row['centre']})")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        new_val = st.number_input("Nouvelle valeur", 
                                                  value=float(row['valeur']) if row['valeur'] else 0.0,
                                                  key="new_val")
                    with col2:
                        new_statut = st.selectbox("Nouveau statut",
                            ["EN_ATTENTE", "VALIDE", "BROUILLON", "REJETE"],
                            key="new_stat")
                    
                    can_modify = (user['username'] == row['saisi_par'] or user_can_validate())
                    
                    if can_modify:
                        if st.button("Modifier", type="primary"):
                            try:
                                with get_db_connection() as conn:
                                    cur = conn.cursor()
                                    cur.execute("""
                                        UPDATE staging.indicateurs_dp
                                        SET valeur = %s, statut = %s,
                                            modifie_par = %s, date_modification = NOW()
                                        WHERE id_saisie = %s
                                    """, (new_val, new_statut, user['username'], id_a_modifier))
                                    conn.commit()
                                log_action(user['username'], 'UPDATE', 
                                          'staging.indicateurs_dp', id_a_modifier)
                                st.success("Saisie modifiee")
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))
                        
                        if st.button("Supprimer", type="secondary"):
                            try:
                                with get_db_connection() as conn:
                                    cur = conn.cursor()
                                    cur.execute(
                                        "DELETE FROM staging.indicateurs_dp WHERE id_saisie = %s",
                                        (id_a_modifier,)
                                    )
                                    conn.commit()
                                log_action(user['username'], 'DELETE',
                                          'staging.indicateurs_dp', id_a_modifier)
                                st.success("Saisie supprimee")
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))
                    else:
                        st.warning("Vous ne pouvez modifier que vos propres saisies")
                else:
                    st.warning("ID non trouve")
        else:
            st.info("Aucune saisie trouvee")
    except Exception as e:
        st.error(str(e))


# ============================================================
# TAB 2 : Reclamations
# ============================================================
with tab2:
    st.subheader("Reclamations")
    
    try:
        df_rec = pd.read_sql("""
            SELECT s.id_saisie, p.nom_province, t.libelle_reclamation,
                   s.nombre, s.temps_coupure_h, s.delai_traitement_j,
                   s.annee, s.mois, s.statut, s.saisi_par, s.date_saisie
            FROM staging.reclamations_dp s
            JOIN gold.dim_province p ON s.id_province = p.id_province
            JOIN gold.dim_type_reclamation t ON s.code_type_reclam = t.code_type
            ORDER BY s.date_saisie DESC LIMIT 200
        """, engine)
        
        if not df_rec.empty:
            st.dataframe(df_rec, use_container_width=True, hide_index=True)
        else:
            st.info("Aucune reclamation saisie")
    except Exception as e:
        st.error(str(e))


# ============================================================
# TAB 3 : Rendements
# ============================================================
with tab3:
    st.subheader("Rendements Etages")
    
    try:
        df_rend = pd.read_sql("""
            SELECT s.id_saisie, e.nom_etage, s.nombre_clients,
                   s.volume_facture_m3, s.volume_amene_m3,
                   s.rendement * 100 as rendement_pct,
                   s.annee, s.mois, s.statut, s.saisi_par, s.date_saisie
            FROM staging.rendements_etage s
            JOIN gold.dim_etage_pression e ON s.id_etage = e.id_etage
            ORDER BY s.date_saisie DESC LIMIT 200
        """, engine)
        
        if not df_rend.empty:
            st.dataframe(df_rend, use_container_width=True, hide_index=True,
                        column_config={
                            "rendement_pct": st.column_config.NumberColumn(
                                "Rendement %", format="%.1f%%"
                            )
                        })
        else:
            st.info("Aucun rendement saisi")
    except Exception as e:
        st.error(str(e))