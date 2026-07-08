# views/page_dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from auth.session_manager import SessionManager
from db.queries import get_dashboard_stats, get_staging_lots
from config.provinces import PROVINCES
from utils.helpers import format_datetime, get_mois_name
from utils.styles import (
    render_page_header, render_metric,
    render_section_open, render_section_close,
    render_empty, get_status_badge,
    apply_chart_theme, get_chart_config,
    CHART_COLORS, STATUS_LABELS
)


def _pct(part, total):
    """Calcule un pourcentage."""
    if total == 0:
        return 0
    return round((part / total) * 100, 1)


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
    indic_total = sum(indic.values()) if indic else 0
    reclam_total = sum(reclam.values()) if reclam else 0

    # Calcul des taux
    indic_valides = indic.get("valide_regional", 0)
    reclam_valides = reclam.get("valide_regional", 0)
    taux_indic = _pct(indic_valides, indic_total) if indic_total else 0
    taux_reclam = _pct(reclam_valides, reclam_total) if reclam_total else 0

    # ── Métriques principales avec pourcentages ──
    c1, c2, c3, c4 = st.columns(4, gap="small")

    with c1:
        st.markdown(render_metric(
            "Total Indicateurs", indic_total, "CHART_BAR",
            sub=f"{indic_valides} validés au DWH",
            trend=(f"{taux_indic}% validés", "up" if taux_indic >= 50 else "neutral")
        ), unsafe_allow_html=True)

    with c2:
        st.markdown(render_metric(
            "Total Réclamations", reclam_total, "CLIPBOARD",
            sub=f"{reclam_valides} validées au DWH",
            trend=(f"{taux_reclam}% validées", "up" if taux_reclam >= 50 else "neutral")
        ), unsafe_allow_html=True)

    with c3:
        pending = indic.get("soumis", 0) + indic.get("valide_dp", 0)
        pct_pend = _pct(pending, indic_total)
        st.markdown(render_metric(
            "En attente", pending, "CLOCK",
            sub=f"Indicateurs — {pct_pend}%",
            trend=(f"{indic.get('soumis', 0)} nouveaux", "neutral")
        ), unsafe_allow_html=True)

    with c4:
        pending_r = reclam.get("soumis", 0) + reclam.get("valide_dp", 0)
        pct_pend_r = _pct(pending_r, reclam_total)
        st.markdown(render_metric(
            "En attente", pending_r, "CLOCK",
            sub=f"Réclamations — {pct_pend_r}%",
            trend=(f"{reclam.get('soumis', 0)} nouvelles", "neutral")
        ), unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── Workflow ──
    with st.expander("Comment fonctionne le workflow de validation ?"):
        st.markdown("""
| Étape | Responsable | Action |
|-------|-------------|--------|
| 1. Saisie | Agent DP | Saisie des données de sa province |
| 2. Validation DP | Admin DP | Vérification et validation locale |
| 3. Validation régionale | Admin Régional | Validation finale |
| 4. Stockage | Système | Transfert automatique vers le Data Warehouse |
        """)

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # ══════════════════════════════════════════
    # GRAPHIQUES DE RÉPARTITION
    # ══════════════════════════════════════════
    col_l, col_r = st.columns(2, gap="medium")

    # ── Indicateurs : Graphique en donut ──
    with col_l:
        st.markdown(render_section_open("Indicateurs — Répartition par statut", "CHART_BAR"),
                    unsafe_allow_html=True)
        if indic and sum(indic.values()) > 0:
            df = pd.DataFrame([
                {"Statut": STATUS_LABELS.get(k, k),
                 "Nombre": v,
                 "Pourcentage": f"{_pct(v, indic_total)}%",
                 "color_key": k}
                for k, v in indic.items() if v > 0
            ])

            fig = go.Figure(data=[go.Pie(
                labels=df["Statut"],
                values=df["Nombre"],
                hole=0.55,
                marker=dict(
                    colors=[CHART_COLORS.get(k, "#94A3B8") for k in df["color_key"]],
                    line=dict(color="#FFFFFF", width=2),
                ),
                textinfo="percent",
                textfont=dict(size=12, color="white", family="Inter"),
                hovertemplate="<b>%{label}</b><br>%{value} enregistrements<br>%{percent}<extra></extra>",
            )])
            fig.update_layout(
                height=280,
                annotations=[dict(
                    text=f"<b>{indic_total}</b><br><span style='font-size:11px;color:#6B7280;'>total</span>",
                    x=0.5, y=0.5, font=dict(size=20, color="#111827"), showarrow=False
                )],
            )
            fig = apply_chart_theme(fig)
            st.plotly_chart(fig, use_container_width=True, config=get_chart_config())

            # Tableau récapitulatif compact
            st.dataframe(df[["Statut", "Nombre", "Pourcentage"]],
                         use_container_width=True, hide_index=True)
        else:
            st.markdown(render_empty("INBOX", "Aucun indicateur", "Aucune donnée saisie"),
                        unsafe_allow_html=True)
        st.markdown(render_section_close(), unsafe_allow_html=True)

    # ── Réclamations : Graphique en donut ──
    with col_r:
        st.markdown(render_section_open("Réclamations — Répartition par statut", "CLIPBOARD"),
                    unsafe_allow_html=True)
        if reclam and sum(reclam.values()) > 0:
            df = pd.DataFrame([
                {"Statut": STATUS_LABELS.get(k, k),
                 "Nombre": v,
                 "Pourcentage": f"{_pct(v, reclam_total)}%",
                 "color_key": k}
                for k, v in reclam.items() if v > 0
            ])

            fig = go.Figure(data=[go.Pie(
                labels=df["Statut"],
                values=df["Nombre"],
                hole=0.55,
                marker=dict(
                    colors=[CHART_COLORS.get(k, "#94A3B8") for k in df["color_key"]],
                    line=dict(color="#FFFFFF", width=2),
                ),
                textinfo="percent",
                textfont=dict(size=12, color="white", family="Inter"),
                hovertemplate="<b>%{label}</b><br>%{value} enregistrements<br>%{percent}<extra></extra>",
            )])
            fig.update_layout(
                height=280,
                annotations=[dict(
                    text=f"<b>{reclam_total}</b><br><span style='font-size:11px;color:#6B7280;'>total</span>",
                    x=0.5, y=0.5, font=dict(size=20, color="#111827"), showarrow=False
                )],
            )
            fig = apply_chart_theme(fig)
            st.plotly_chart(fig, use_container_width=True, config=get_chart_config())

            st.dataframe(df[["Statut", "Nombre", "Pourcentage"]],
                         use_container_width=True, hide_index=True)
        else:
            st.markdown(render_empty("INBOX", "Aucune réclamation", "Aucune donnée saisie"),
                        unsafe_allow_html=True)
        st.markdown(render_section_close(), unsafe_allow_html=True)

    # ══════════════════════════════════════════
    # GRAPHIQUE BARRES : Vue par province (Admin uniquement)
    # ══════════════════════════════════════════
    if role in ["admin_regional", "super_admin"]:
        st.markdown(render_section_open("Vue par province", "MAP_PIN",
                                         "Comparaison des données par province"),
                    unsafe_allow_html=True)

        rows = []
        chart_data = []
        for pid, pinfo in PROVINCES.items():
            ps = get_dashboard_stats(pid)
            pi = ps.get("indicateurs", {})
            pr = ps.get("reclamations", {})

            total_i = sum(pi.values())
            total_r = sum(pr.values())

            rows.append({
                "Province": pinfo["nom"],
                "Indic. Total": total_i,
                "Indic. En attente": pi.get("soumis", 0) + pi.get("valide_dp", 0),
                "Indic. Validés": pi.get("valide_regional", 0),
                "Réc. Total": total_r,
                "Réc. En attente": pr.get("soumis", 0) + pr.get("valide_dp", 0),
                "Réc. Validées": pr.get("valide_regional", 0),
                "% Validation Indic.": f"{_pct(pi.get('valide_regional', 0), total_i)}%",
                "% Validation Réc.": f"{_pct(pr.get('valide_regional', 0), total_r)}%",
            })

            chart_data.append({"Province": pinfo["nom"], "Type": "Indicateurs",
                               "Nombre": total_i})
            chart_data.append({"Province": pinfo["nom"], "Type": "Réclamations",
                               "Nombre": total_r})

        # Graphique barres groupées
        df_chart = pd.DataFrame(chart_data)
        fig = px.bar(
            df_chart, x="Province", y="Nombre", color="Type",
            barmode="group",
            color_discrete_map={"Indicateurs": "#3B82F6", "Réclamations": "#10B981"},
            text="Nombre",
        )
        fig.update_traces(textposition="outside", textfont=dict(size=11))
        fig.update_layout(height=350, xaxis_title="", yaxis_title="Nombre d'enregistrements")
        fig = apply_chart_theme(fig)
        st.plotly_chart(fig, use_container_width=True, config=get_chart_config())

        # Tableau détaillé
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.markdown(render_section_close(), unsafe_allow_html=True)

    # ══════════════════════════════════════════
    # LOTS RÉCENTS
    # ══════════════════════════════════════════
    st.markdown(render_section_open("Lots récents", "ARCHIVE"), unsafe_allow_html=True)
    tab_i, tab_r = st.tabs(["Indicateurs", "Réclamations"])

    with tab_i:
        lots = get_staging_lots(province_filter, data_type="indicateurs")
        if lots:
            df = pd.DataFrame(lots[:10])
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
            df = pd.DataFrame(lots_r[:10])
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