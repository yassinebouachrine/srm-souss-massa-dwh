# views/page_dashboard.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from auth.session_manager import SessionManager
from db.queries import get_dashboard_stats, get_staging_lots
from config.provinces import PROVINCES
from utils.helpers import format_datetime, get_mois_name
from utils.styles import (
    render_page_header, render_metric,
    render_section_open, render_section_close,
    render_empty, apply_chart_theme, get_chart_config,
    CHART_COLORS, STATUS_LABELS
)


def _pct(part, total):
    return round((part / total) * 100, 1) if total > 0 else 0


def render_dashboard():
    SessionManager.require_auth()
    user = SessionManager.get_user()
    role = user["role"]
    id_province = user["id_province"]

    st.markdown(render_page_header("Tableau de bord", f"Vue d'ensemble — {user['nom_complet']}"),
                unsafe_allow_html=True)

    # Filtrage selon le rôle
    if role == "admin_regional":
        # Admin régional ne voit QUE les données validées par admin_dp (à partir de valide_dp)
        province_filter = None
        show_only_validated_dp = True
    elif role in ["agent_dp", "admin_dp"]:
        province_filter = id_province
        show_only_validated_dp = False
    else:
        province_filter = None
        show_only_validated_dp = False

    stats = get_dashboard_stats(province_filter)
    indic = stats.get("indicateurs", {}) or {}
    reclam = stats.get("reclamations", {}) or {}

    # Pour admin régional : filtrer pour ne montrer que valide_dp, valide_regional, rejete_regional
    if show_only_validated_dp:
        allowed = ["valide_dp", "valide_regional", "rejete_regional"]
        indic = {k: v for k, v in indic.items() if k in allowed}
        reclam = {k: v for k, v in reclam.items() if k in allowed}

    indic_total = sum(indic.values()) if indic else 0
    reclam_total = sum(reclam.values()) if reclam else 0

    indic_valides = indic.get("valide_regional", 0)
    reclam_valides = reclam.get("valide_regional", 0)
    indic_rejetes = indic.get("rejete_dp", 0) + indic.get("rejete_regional", 0)
    reclam_rejetes = reclam.get("rejete_dp", 0) + reclam.get("rejete_regional", 0)
    pending_i = indic.get("soumis", 0) + indic.get("valide_dp", 0)
    pending_r = reclam.get("soumis", 0) + reclam.get("valide_dp", 0)

    # ═══════ MÉTRIQUES ═══════
    c1, c2, c3, c4 = st.columns(4, gap="small")

    with c1:
        pct = _pct(indic_valides, indic_total)
        st.markdown(render_metric(
            "Indicateurs", indic_total, "CHART_BAR",
            sub=f"{indic_valides} validés définitivement",
            trend=(f"{pct}% dans le DWH", "up" if pct >= 50 else "neutral")
        ), unsafe_allow_html=True)

    with c2:
        pct = _pct(reclam_valides, reclam_total)
        st.markdown(render_metric(
            "Réclamations", reclam_total, "CLIPBOARD",
            sub=f"{reclam_valides} validées définitivement",
            trend=(f"{pct}% dans le DWH", "up" if pct >= 50 else "neutral")
        ), unsafe_allow_html=True)

    with c3:
        total_pending = pending_i + pending_r
        pct_pend = _pct(total_pending, indic_total + reclam_total)
        st.markdown(render_metric(
            "En attente", total_pending, "CLOCK",
            sub=f"Ind: {pending_i} · Réc: {pending_r}",
            trend=(f"{pct_pend}% du total", "neutral")
        ), unsafe_allow_html=True)

    with c4:
        total_rej = indic_rejetes + reclam_rejetes
        pct_rej = _pct(total_rej, indic_total + reclam_total)
        st.markdown(render_metric(
            "Rejetés", total_rej, "X",
            sub=f"Ind: {indic_rejetes} · Réc: {reclam_rejetes}",
            trend=(f"{pct_rej}% du total", "down" if total_rej > 0 else "neutral")
        ), unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ═══════ WORKFLOW ═══════
    with st.expander("Comment fonctionne le workflow de validation ?"):
        st.markdown("""
| Étape | Responsable | Action |
|-------|-------------|--------|
| 1. Saisie | Agent DP | Saisie des données de sa province |
| 2. Validation DP | Admin DP | Vérification locale |
| 3. Validation régionale | Admin Régional | Validation finale à Agadir |
| 4. Stockage DWH | Système | Transfert automatique vers Power BI |
| Rejet | Admin DP/Régional | Retour à l'agent pour correction |
        """)

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # ═══════ GRAPHIQUES PRINCIPAUX ═══════
    if role in ["admin_regional", "super_admin"]:
        # Vue régionale : graphique par province + graphique donut global
        _render_provinces_chart()
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    col_l, col_r = st.columns(2, gap="medium")

    with col_l:
        st.markdown(render_section_open("Indicateurs — Répartition", "CHART_BAR"),
                    unsafe_allow_html=True)
        if indic_total > 0:
            _render_donut_only(indic, indic_total)
        else:
            st.markdown(render_empty("INBOX", "Aucune donnée"), unsafe_allow_html=True)
        st.markdown(render_section_close(), unsafe_allow_html=True)

    with col_r:
        st.markdown(render_section_open("Réclamations — Répartition", "CLIPBOARD"),
                    unsafe_allow_html=True)
        if reclam_total > 0:
            _render_donut_only(reclam, reclam_total)
        else:
            st.markdown(render_empty("INBOX", "Aucune donnée"), unsafe_allow_html=True)
        st.markdown(render_section_close(), unsafe_allow_html=True)


def _render_donut_only(data, total):
    """Donut chart uniquement (pas de tableau redondant)."""
    rows = [{"Statut": STATUS_LABELS.get(k, k), "Nombre": v,
             "color": CHART_COLORS.get(k, "#94A3B8")}
            for k, v in data.items() if v > 0]

    if not rows:
        st.info("Aucune donnée.")
        return

    df = pd.DataFrame(rows)

    fig = go.Figure(data=[go.Pie(
        labels=df["Statut"].tolist(),
        values=df["Nombre"].tolist(),
        hole=0.6,
        marker=dict(colors=df["color"].tolist(), line=dict(color="#FFF", width=2)),
        textinfo="percent",
        textposition="inside",
        textfont=dict(size=13, family="Inter", color="white"),
        hovertemplate="<b>%{label}</b><br>%{value} enreg. (%{percent})<extra></extra>",
        sort=False,
    )])

    fig.update_layout(
        height=320,
        margin=dict(l=20, r=20, t=20, b=60),
        annotations=[dict(
            text=f"<b style='font-size:28px;'>{total}</b><br>"
                 f"<span style='font-size:11px;color:#6B7280;'>total</span>",
            x=0.5, y=0.5,
            font=dict(color="#111827"),
            showarrow=False
        )],
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top", y=-0.05,
            xanchor="center", x=0.5,
            font=dict(size=11, color="#374151"),
            itemsizing="constant",
        ),
        paper_bgcolor="#FFF",
        plot_bgcolor="#FFF",
    )
    st.plotly_chart(fig, use_container_width=True, config=get_chart_config())


def _render_provinces_chart():
    """Graphique horizontal empilé par province — vue admin régional."""
    st.markdown(render_section_open("Vue par province — Souss-Massa", "MAP_PIN",
                                     "Données validées par les admins DP"),
                unsafe_allow_html=True)

    rows = []
    for pid, pinfo in PROVINCES.items():
        ps = get_dashboard_stats(pid)
        pi = ps.get("indicateurs", {}) or {}
        pr = ps.get("reclamations", {}) or {}

        # Seulement les données visibles pour admin régional
        rows.append({
            "Province": pinfo["nom"],
            "À valider par régional": pi.get("valide_dp", 0) + pr.get("valide_dp", 0),
            "Validés définitivement": pi.get("valide_regional", 0) + pr.get("valide_regional", 0),
            "Rejetés régional": pi.get("rejete_regional", 0) + pr.get("rejete_regional", 0),
        })

    df = pd.DataFrame(rows)

    if df[["À valider par régional", "Validés définitivement", "Rejetés régional"]].sum().sum() == 0:
        st.markdown(render_empty("INBOX", "Aucune donnée",
                                  "Aucune donnée n'a encore été validée par les admins DP"),
                    unsafe_allow_html=True)
        st.markdown(render_section_close(), unsafe_allow_html=True)
        return

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="À valider par régional",
        y=df["Province"], x=df["À valider par régional"],
        orientation="h", marker=dict(color="#F59E0B"),
        text=df["À valider par régional"], textposition="inside",
        textfont=dict(color="white", size=11),
    ))
    fig.add_trace(go.Bar(
        name="Validés définitivement",
        y=df["Province"], x=df["Validés définitivement"],
        orientation="h", marker=dict(color="#10B981"),
        text=df["Validés définitivement"], textposition="inside",
        textfont=dict(color="white", size=11),
    ))
    fig.add_trace(go.Bar(
        name="Rejetés régional",
        y=df["Province"], x=df["Rejetés régional"],
        orientation="h", marker=dict(color="#EF4444"),
        text=df["Rejetés régional"], textposition="inside",
        textfont=dict(color="white", size=11),
    ))

    fig.update_layout(
        barmode="stack", height=350,
        # xaxis_title="Nombre d'enregistrements",
        yaxis_title="",
        margin=dict(l=20, r=20, t=20, b=20),
    )
    fig = apply_chart_theme(fig)
    st.plotly_chart(fig, use_container_width=True, config=get_chart_config())

    st.markdown(render_section_close(), unsafe_allow_html=True)