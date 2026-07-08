# pages/page_dashboard.py
import streamlit as st
import pandas as pd
from auth.session_manager import SessionManager
from db.queries import get_dashboard_stats, get_staging_lots
from config.provinces import PROVINCES
from utils.helpers import format_datetime, get_mois_name
from utils.styles import (
    render_page_header, render_metric,
    render_section_open, render_section_close,
    render_empty, get_status_badge
)


def render_dashboard():
    SessionManager.require_auth()
    user = SessionManager.get_user()
    role = user["role"]
    id_province = user["id_province"]

    st.markdown(
        render_page_header("Tableau de bord",
                           f"Vue d'ensemble — {user['nom_complet']}"),
        unsafe_allow_html=True,
    )

    # ── Stats ──
    province_filter = id_province if role in ["agent_dp", "admin_dp"] else None
    stats = get_dashboard_stats(province_filter)

    indic = stats.get("indicateurs", {})
    reclam = stats.get("reclamations", {})
    indic_total = sum(indic.values())
    reclam_total = sum(reclam.values())
    pending_indic = indic.get("soumis", 0) + indic.get("valide_dp", 0)
    pending_reclam = reclam.get("soumis", 0) + reclam.get("valide_dp", 0)

    c1, c2, c3, c4 = st.columns(4, gap="small")
    with c1:
        st.markdown(render_metric("Indicateurs", indic_total, "CHART_BAR", "Total saisis"),
                    unsafe_allow_html=True)
    with c2:
        st.markdown(render_metric("Réclamations", reclam_total, "CLIPBOARD", "Total saisies"),
                    unsafe_allow_html=True)
    with c3:
        st.markdown(render_metric("En attente", pending_indic, "CLOCK", "Indicateurs"),
                    unsafe_allow_html=True)
    with c4:
        st.markdown(render_metric("En attente", pending_reclam, "CLOCK", "Réclamations"),
                    unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── Workflow ──
    with st.expander("Comment fonctionne le workflow de validation ?"):
        st.markdown("""
        <div class="wf">
            <div class="wf-step"><div class="wf-circle done">1</div><div class="wf-label">Saisie</div></div>
            <div class="wf-line done"></div>
            <div class="wf-step"><div class="wf-circle active">2</div><div class="wf-label active">Validation DP</div></div>
            <div class="wf-line"></div>
            <div class="wf-step"><div class="wf-circle pending">3</div><div class="wf-label">Validation régionale</div></div>
            <div class="wf-line"></div>
            <div class="wf-step"><div class="wf-circle pending">4</div><div class="wf-label">Data Warehouse</div></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
| Étape | Responsable | Action |
|-------|-------------|--------|
| 1. Saisie | Agent DP | Saisie des données de sa province |
| 2. Validation DP | Admin DP | Vérification et validation locale |
| 3. Validation régionale | Admin Régional | Validation finale |
| 4. Stockage | Système | Transfert automatique vers le DWH |
        """)

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # ── Répartitions ──
    col_l, col_r = st.columns(2, gap="medium")

    with col_l:
        st.markdown(render_section_open("Indicateurs — Répartition par statut", "CHART_BAR"),
                    unsafe_allow_html=True)
        if indic:
            df = pd.DataFrame([{"Statut": k, "Nombre": v} for k, v in indic.items()])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.markdown(render_empty("INBOX", "Aucun indicateur", "Aucune donnée saisie"),
                        unsafe_allow_html=True)
        st.markdown(render_section_close(), unsafe_allow_html=True)

    with col_r:
        st.markdown(render_section_open("Réclamations — Répartition par statut", "CLIPBOARD"),
                    unsafe_allow_html=True)
        if reclam:
            df = pd.DataFrame([{"Statut": k, "Nombre": v} for k, v in reclam.items()])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.markdown(render_empty("INBOX", "Aucune réclamation", "Aucune donnée saisie"),
                        unsafe_allow_html=True)
        st.markdown(render_section_close(), unsafe_allow_html=True)

    # ── Lots récents ──
    st.markdown(render_section_open("Lots récents", "ARCHIVE"), unsafe_allow_html=True)
    tab_i, tab_r = st.tabs(["Indicateurs", "Réclamations"])

    with tab_i:
        lots = get_staging_lots(province_filter, data_type="indicateurs")
        if lots:
            df = pd.DataFrame(lots)
            df["date_creation"] = df["date_creation"].apply(format_datetime)
            df["mois"] = df["mois"].apply(get_mois_name)
            st.dataframe(
                df[["lot_id", "nom_province", "annee", "mois", "statut",
                    "nb_enregistrements", "date_creation"]],
                use_container_width=True, hide_index=True,
                column_config={
                    "lot_id": "Lot", "nom_province": "Province",
                    "annee": "Année", "mois": "Mois", "statut": "Statut",
                    "nb_enregistrements": "Enreg.", "date_creation": "Créé le",
                },
            )
        else:
            st.markdown(render_empty("ARCHIVE", "Aucun lot"), unsafe_allow_html=True)

    with tab_r:
        lots_r = get_staging_lots(province_filter, data_type="reclamations")
        if lots_r:
            df = pd.DataFrame(lots_r)
            df["date_creation"] = df["date_creation"].apply(format_datetime)
            df["mois"] = df["mois"].apply(get_mois_name)
            st.dataframe(
                df[["lot_id", "nom_province", "annee", "mois", "statut",
                    "nb_enregistrements", "date_creation"]],
                use_container_width=True, hide_index=True,
            )
        else:
            st.markdown(render_empty("ARCHIVE", "Aucun lot"), unsafe_allow_html=True)

    st.markdown(render_section_close(), unsafe_allow_html=True)

    # ── Vue par province (Admin) ──
    if role in ["admin_regional", "super_admin"]:
        st.markdown(render_section_open("Vue d'ensemble par province", "MAP_PIN"),
                    unsafe_allow_html=True)
        rows = []
        for pid, pinfo in PROVINCES.items():
            ps = get_dashboard_stats(pid)
            pi, pr = ps.get("indicateurs", {}), ps.get("reclamations", {})
            rows.append({
                "Province": pinfo["nom"],
                "Ind. Brouillon": pi.get("brouillon", 0),
                "Ind. Soumis": pi.get("soumis", 0),
                "Ind. Validé DP": pi.get("valide_dp", 0),
                "Ind. Validé Rég.": pi.get("valide_regional", 0),
                "Réc. Soumis": pr.get("soumis", 0),
                "Réc. Validé DP": pr.get("valide_dp", 0),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.markdown(render_section_close(), unsafe_allow_html=True)