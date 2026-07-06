"""
Saisie des Rendements par Etage de Pression
Reproduit la structure du fichier Excel: etages_rendements_Histo PBI
Colonnes: NOM_ETAGE, Mois_annee, Nombre de clients, Vol Facture, Rendement
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from streamlit_app.auth.simple_auth import (
    check_authentication, show_login_page,
    show_user_info_sidebar, get_current_user, user_can_validate
)
from streamlit_app.db.queries import get_etages, insert_rendement_etage
from streamlit_app.db.connection import get_engine
from streamlit_app.utils.audit import log_action
from streamlit_app.utils.helpers import nom_mois


st.set_page_config(page_title="Rendements Etages", page_icon="🚰", layout="wide")

if not check_authentication():
    show_login_page()
    st.stop()

show_user_info_sidebar()
user = get_current_user()


# ============================================================
# HEADER
# ============================================================
st.title("Rendements par Etage de Pression")
st.caption("Saisie mensuelle : Nombre de clients, Vol Facture, Vol Amene → Rendement calcule automatiquement")
st.markdown("---")


# ============================================================
# ETAPE 1 : PERIODE
# ============================================================
st.subheader("1. Selectionner la periode")

with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        annee = st.selectbox("Annee", list(range(2020, 2028)), index=6)
    with col2:
        mois = st.selectbox("Mois", list(range(1, 13)), 
                           format_func=nom_mois,
                           index=datetime.now().month - 1)


# ============================================================
# CHARGER LES ETAGES
# ============================================================
df_etages = get_etages()

if df_etages.empty:
    st.warning("Aucun etage de pression defini")
    st.info("Ajoutez d'abord des etages via la page **Lineaires Reseau** ou l'**Administration**.")
    st.stop()


# ============================================================
# INFO MODE
# ============================================================
if user_can_validate():
    st.success(f"**Mode Administrateur** : {len(df_etages)} etages a saisir - Validation directe")
else:
    st.info(f"**Mode Agent** : {len(df_etages)} etages a saisir - Soumission pour validation")


# ============================================================
# CHARGER LES SAISIES EXISTANTES POUR CETTE PERIODE
# ============================================================
try:
    engine = get_engine()
    df_existant = pd.read_sql(f"""
        SELECT id_etage, nombre_clients, volume_facture_m3, volume_amene_m3, rendement
        FROM staging.rendements_etage
        WHERE annee = {annee} AND mois = {mois}
    """, engine)
    
    valeurs_existantes = {}
    for _, row in df_existant.iterrows():
        valeurs_existantes[int(row['id_etage'])] = {
            'nb_clients': row['nombre_clients'] or 0,
            'vol_facture': float(row['volume_facture_m3']) if row['volume_facture_m3'] else 0.0,
            'vol_amene': float(row['volume_amene_m3']) if row['volume_amene_m3'] else 0.0
        }
    
    nb_deja = len(valeurs_existantes)
    if nb_deja > 0:
        st.caption(f"{nb_deja} etage(s) deja saisi(s) pour {nom_mois(mois)} {annee} (valeurs pre-remplies)")

except Exception as e:
    valeurs_existantes = {}
    st.warning(f"Impossible de charger les saisies existantes: {e}")


# ============================================================
# ETAPE 2 : SAISIE PAR ETAGE
# ============================================================
st.subheader(f"2. Saisir les rendements - {nom_mois(mois)} {annee}")

st.markdown("""
**Structure des donnees (comme dans le fichier Excel original) :**
- **NOM_ETAGE** : Nom de l'etage de pression
- **Nombre de clients** : Nombre de clients dans l'etage
- **Vol Facture (m3)** : Volume d'eau facture aux clients
- **Vol Amene (m3)** : Volume d'eau amene dans l'etage
- **Rendement (%)** : Calcule automatiquement = (Vol Facture / Vol Amene) × 100
""")

st.markdown("---")

with st.form("form_rendements"):
    donnees = []
    
    # Tableau visuel des etages
    for _, etage in df_etages.iterrows():
        id_etage = int(etage['id_etage'])
        val_prev = valeurs_existantes.get(id_etage, {
            'nb_clients': 0, 'vol_facture': 0.0, 'vol_amene': 0.0
        })
        
        with st.container(border=True):
            st.markdown(f"### {etage['nom_etage']}")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                nb_clients = st.number_input(
                    "Nombre de clients",
                    min_value=0,
                    step=1,
                    value=int(val_prev['nb_clients']),
                    key=f"nc_{id_etage}"
                )
            
            with col2:
                vol_facture = st.number_input(
                    "Vol Facture (m3)",
                    min_value=0.0,
                    step=100.0,
                    value=float(val_prev['vol_facture']),
                    key=f"vf_{id_etage}",
                    help="Volume d'eau facture aux clients"
                )
            
            with col3:
                vol_amene = st.number_input(
                    "Vol Amene (m3)",
                    min_value=0.0,
                    step=100.0,
                    value=float(val_prev['vol_amene']),
                    key=f"va_{id_etage}",
                    help="Volume d'eau amene dans l'etage"
                )
            
            with col4:
                # CALCUL AUTOMATIQUE DU RENDEMENT
                if vol_amene > 0:
                    rendement_pct = (vol_facture / vol_amene) * 100
                    rendement_frac = vol_facture / vol_amene
                    
                    # Afficher avec couleur selon performance
                    if rendement_pct >= 75:
                        st.success(f"Rendement: **{rendement_pct:.2f}%**")
                    elif rendement_pct >= 60:
                        st.warning(f"Rendement: **{rendement_pct:.2f}%**")
                    else:
                        st.error(f"Rendement: **{rendement_pct:.2f}%**")
                else:
                    rendement_pct = 0
                    rendement_frac = 0
                    st.info("Rendement: **-**")
                
                # Info consommation moyenne
                if nb_clients > 0 and vol_facture > 0:
                    conso_moy = vol_facture / nb_clients
                    st.caption(f"Conso/client: {conso_moy:.1f} m3")
            
            donnees.append({
                'id_etage': id_etage,
                'nom_etage': etage['nom_etage'],
                'nombre_clients': nb_clients,
                'volume_facture_m3': vol_facture,
                'volume_amene_m3': vol_amene,
                'rendement': rendement_frac
            })
    
    st.markdown("---")
    
    commentaire = st.text_area("Commentaire (optionnel)", height=60)
    
    # Boutons
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        submit = st.form_submit_button(
            "Soumettre",
            use_container_width=True
        )
    
    with col2:
        if user_can_validate():
            submit_val = st.form_submit_button(
                "Valider directement",
                type="primary",
                use_container_width=True
            )
        else:
            submit_val = False


# ============================================================
# TRAITEMENT
# ============================================================
if submit or submit_val:
    statut = "VALIDE" if (submit_val and user_can_validate()) else "EN_ATTENTE"
    
    nb_ok = 0
    nb_skip = 0
    erreurs = []
    
    with st.spinner("Enregistrement..."):
        for d in donnees:
            # Skip si aucune donnee saisie (tout a 0)
            if d['volume_amene_m3'] == 0 and d['volume_facture_m3'] == 0 and d['nombre_clients'] == 0:
                nb_skip += 1
                continue
            
            try:
                data = {
                    'id_etage': d['id_etage'],
                    'annee': annee,
                    'mois': mois,
                    'nombre_clients': d['nombre_clients'],
                    'volume_facture_m3': d['volume_facture_m3'],
                    'volume_amene_m3': d['volume_amene_m3'],
                    'rendement': d['rendement'],
                    'commentaire': commentaire,
                    'saisi_par': user['username'],
                    'statut': statut
                }
                id_s, _ = insert_rendement_etage(data)
                log_action(user['username'], 'INSERT', 'staging.rendements_etage', id_s)
                nb_ok += 1
            except Exception as e:
                erreurs.append(f"{d['nom_etage']}: {str(e)[:80]}")
    
    if erreurs:
        with st.expander(f"{len(erreurs)} erreur(s)"):
            for e in erreurs:
                st.error(e)
    
    if nb_ok > 0:
        if statut == "VALIDE":
            st.success(f"**{nb_ok} rendements valides et enregistres !**")
            st.balloons()
        else:
            st.success(
                f"**{nb_ok} rendements soumis pour validation.**\n\n"
                f"L'administrateur sera notifie."
            )
    
    if nb_skip > 0:
        st.info(f"{nb_skip} etage(s) ignore(s) (aucune donnee saisie)")


# ============================================================
# HISTORIQUE DES SAISIES POUR CETTE PERIODE
# ============================================================
st.markdown("---")
st.subheader("Historique des saisies")

try:
    df_hist = pd.read_sql(f"""
        SELECT 
            e.nom_etage AS "NOM_ETAGE",
            TO_CHAR(TO_DATE(s.mois::TEXT, 'MM'), 'FMMonth') || '-' || RIGHT(s.annee::TEXT, 2) AS "Mois_annee",
            s.nombre_clients AS "Nombre de clients",
            s.volume_facture_m3 AS "Vol Facture",
            s.volume_amene_m3 AS "Vol Amene",
            ROUND(s.rendement::NUMERIC, 4) AS "Rendement",
            s.statut AS "Statut",
            s.saisi_par AS "Utilisateur",
            s.date_saisie AS "Date"
        FROM staging.rendements_etage s
        JOIN gold.dim_etage_pression e ON s.id_etage = e.id_etage
        ORDER BY s.annee DESC, s.mois DESC, e.nom_etage
        LIMIT 100
    """, engine)
    
    if not df_hist.empty:
        st.caption(f"{len(df_hist)} enregistrement(s) - Format identique au fichier Excel original")
        
        st.dataframe(
            df_hist, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Date": st.column_config.DatetimeColumn(format="DD/MM/YY HH:mm"),
                "Rendement": st.column_config.NumberColumn(format="%.4f"),
                "Vol Facture": st.column_config.NumberColumn(format="%.0f"),
                "Vol Amene": st.column_config.NumberColumn(format="%.0f")
            }
        )
        
        # Export CSV compatible Excel
        csv = df_hist.to_csv(index=False, sep=';').encode('utf-8-sig')
        st.download_button(
            "Telecharger (format Excel compatible)",
            csv,
            f"rendements_etages_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv"
        )
    else:
        st.info("Aucun rendement saisi pour le moment")

except Exception as e:
    st.error(f"Erreur historique: {e}")


# ============================================================
# STATISTIQUES GLOBALES
# ============================================================
st.markdown("---")
st.subheader("Statistiques Globales")

try:
    df_stats = pd.read_sql("""
        SELECT 
            e.nom_etage,
            COUNT(s.id_saisie) as nb_mois_saisis,
            AVG(s.rendement * 100) as rendement_moyen,
            SUM(s.volume_facture_m3) as vol_facture_total,
            SUM(s.volume_amene_m3) as vol_amene_total
        FROM gold.dim_etage_pression e
        LEFT JOIN staging.rendements_etage s ON e.id_etage = s.id_etage
        GROUP BY e.nom_etage
        ORDER BY e.nom_etage
    """, engine)
    
    if not df_stats.empty:
        st.dataframe(
            df_stats, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "nom_etage": "Etage",
                "nb_mois_saisis": "Nb Mois Saisis",
                "rendement_moyen": st.column_config.NumberColumn(
                    "Rendement Moyen %", format="%.2f%%"
                ),
                "vol_facture_total": st.column_config.NumberColumn(
                    "Vol Facture Total (m3)", format="%.0f"
                ),
                "vol_amene_total": st.column_config.NumberColumn(
                    "Vol Amene Total (m3)", format="%.0f"
                )
            }
        )

except Exception as e:
    st.caption(f"Stats indisponibles: {e}")