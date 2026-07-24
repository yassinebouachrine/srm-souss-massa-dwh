# views/page_dashboard.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from auth.session_manager import SessionManager
from db.queries import (
    get_dashboard_stats_filtered,
    get_province_full_stats,
    get_activity_timeline,
    get_dp_activity_summary,
    get_available_years_dashboard,
    get_staging_lots,
)
from config.provinces import PROVINCES
from utils.helpers import format_datetime, get_mois_name, MOIS_FR
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

    st.markdown(render_page_header("Tableau de bord",
                                    f"Vue d'ensemble — {user['nom_complet']}"),
                unsafe_allow_html=True)

    # Détermine le mode de vue selon le rôle
    role_view = "admin_regional" if role == "admin_regional" else None

    # Bandeau info pour admin régional
    if role == "admin_regional":
        st.markdown(
            "<div style='background:#F0F9FF;border-left:3px solid #0EA5E9;"
            "padding:0.75rem 1rem;border-radius:6px;font-size:0.85rem;color:#075985;"
            "margin-bottom:1rem;'>"
            "<strong>Vue Admin Régional :</strong> Vous voyez uniquement les données "
            "déjà <strong>validées par les admins DP</strong> (à valider, validées définitivement, rejetées régional)."
            "</div>",
            unsafe_allow_html=True
        )

    # ═══════════════════════════════════════════════════
    # FILTRES GLOBAUX
    # ═══════════════════════════════════════════════════
    annees_dispo = get_available_years_dashboard()
    if not annees_dispo:
        annees_dispo = [datetime.now().year]

    st.markdown(render_section_open("Filtres", "FILTER",
                                     "Filtres appliqués sur tout le tableau de bord"),
                unsafe_allow_html=True)

    f1, f2, f3 = st.columns(3)

    with f1:
        f_annee = st.selectbox(
            "Année",
            ["Toutes"] + annees_dispo,
            key="dash_f_annee",
        )

    with f2:
        f_mois = st.selectbox(
            "Mois",
            ["Tous"] + list(range(1, 13)),
            format_func=lambda x: "Tous les mois" if x == "Tous" else MOIS_FR[x],
            key="dash_f_mois",
        )

    with f3:
        # Filtre province (uniquement pour admin_regional et super_admin)
        if role in ["admin_regional", "super_admin"]:
            prov_options = [(None, "Toutes les provinces")] + \
                           [(pid, p["nom"]) for pid, p in PROVINCES.items()]
            f_prov = st.selectbox(
                "Province",
                prov_options,
                format_func=lambda x: x[1] if isinstance(x, tuple) else x,
                key="dash_f_prov",
            )
            selected_province = f_prov[0] if isinstance(f_prov, tuple) else None
        else:
            # Agent/Admin DP : verrouillé sur leur province
            st.text_input("Province",
                          value=PROVINCES[id_province]["nom"] if id_province else "—",
                          disabled=True)
            selected_province = id_province

    st.markdown(render_section_close(), unsafe_allow_html=True)

    # Appliquer les filtres
    annee_filter = f_annee if f_annee != "Toutes" else None
    mois_filter = f_mois if f_mois != "Tous" else None

    # ═══════════════════════════════════════════════════
    # RÉCUPÉRER LES STATS GLOBALES (avec filtres)
    # ═══════════════════════════════════════════════════
    stats = get_dashboard_stats_filtered(
        id_province=selected_province,
        annee=annee_filter,
        mois=mois_filter,
        role_view=role_view,
    )

    indic = stats.get("indicateurs", {}) or {}
    reclam = stats.get("reclamations", {}) or {}
    indic_total = sum(indic.values()) if indic else 0
    reclam_total = sum(reclam.values()) if reclam else 0

    indic_valides = indic.get("valide_regional", 0)
    reclam_valides = reclam.get("valide_regional", 0)
    indic_rejetes = indic.get("rejete_dp", 0) + indic.get("rejete_regional", 0)
    reclam_rejetes = reclam.get("rejete_dp", 0) + reclam.get("rejete_regional", 0)
    pending_i = indic.get("soumis", 0) + indic.get("valide_dp", 0)
    pending_r = reclam.get("soumis", 0) + reclam.get("valide_dp", 0)

    # ═══════════════════════════════════════════════════
    # MÉTRIQUES
    # ═══════════════════════════════════════════════════
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

    # ═══════════════════════════════════════════════════
    # WORKFLOW
    # ═══════════════════════════════════════════════════
    with st.expander("Comment fonctionne le workflow ?"):
        st.markdown("""
| Étape | Responsable | Action |
|-------|-------------|--------|
| 1. Saisie | Agent DP | Saisie des données |
| 2. Validation DP | Admin DP | Vérification locale |
| 3. Validation régionale | Admin Régional | Validation finale |
| 4. Stockage DWH | Système | Transfert au DWH |
| Rejet | Admin | Retour à l'agent pour correction |
        """)

    # ═══════════════════════════════════════════════════
    # GRAPHIQUE PAR PROVINCE (Admin uniquement)
    # ═══════════════════════════════════════════════════
    if role in ["admin_regional", "super_admin"]:
        _render_provinces_chart(annee_filter, mois_filter, role_view)

    # ═══════════════════════════════════════════════════
    # GRAPHIQUES DE RÉPARTITION
    # ═══════════════════════════════════════════════════
    col_l, col_r = st.columns(2, gap="medium")

    with col_l:
        st.markdown(render_section_open("Indicateurs — Répartition par statut",
                                         "CHART_BAR"),
                    unsafe_allow_html=True)
        if indic_total > 0:
            _render_donut(indic, indic_total)
        else:
            st.markdown(render_empty("INBOX", "Aucun indicateur"),
                        unsafe_allow_html=True)
        st.markdown(render_section_close(), unsafe_allow_html=True)

    with col_r:
        st.markdown(render_section_open("Réclamations — Répartition par statut",
                                         "CLIPBOARD"),
                    unsafe_allow_html=True)
        if reclam_total > 0:
            _render_donut(reclam, reclam_total)
        else:
            st.markdown(render_empty("INBOX", "Aucune réclamation"),
                        unsafe_allow_html=True)
        st.markdown(render_section_close(), unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════
    # COURBE TEMPORELLE (Admin uniquement)
    # ═══════════════════════════════════════════════════
    if role in ["admin_regional", "super_admin"]:
        _render_timeline_chart(annee_filter, mois_filter, selected_province, role_view)

    # ═══════════════════════════════════════════════════
    # VUE GLOBALE D'ACTIVITÉ (Admin uniquement)
    # ═══════════════════════════════════════════════════
    if role in ["admin_regional", "super_admin"]:
        _render_activity_summary(annee_filter, mois_filter, selected_province, role_view)


# ════════════════════════════════════════════════════════════════
# COMPOSANTS GRAPHIQUES
# ════════════════════════════════════════════════════════════════

def _render_donut(data, total):
    """Donut chart des statuts."""
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
        textinfo="percent+label",
        textposition="outside",
        textfont=dict(size=11, family="Inter"),
        hovertemplate="<b>%{label}</b><br>%{value} enreg. (%{percent})<extra></extra>",
        sort=False,
    )])
    fig.update_layout(
        height=320, margin=dict(l=20, r=20, t=20, b=60),
        annotations=[dict(text=f"<b>{total}</b>", x=0.5, y=0.5,
                          font=dict(size=22, color="#111827"), showarrow=False)],
        showlegend=False, paper_bgcolor="#FFF", plot_bgcolor="#FFF",
    )
    st.plotly_chart(fig, use_container_width=True, config=get_chart_config())


def _render_provinces_chart(annee_filter, mois_filter, role_view):
    """Graphique horizontal empilé par province avec TOUS les statuts."""
    subtitle = ("Répartition par statut — Données validées par les admins DP"
                if role_view == "admin_regional"
                else "Répartition complète par statut")

    st.markdown(render_section_open("Vue par province — Souss-Massa", "MAP_PIN",
                                     subtitle),
                unsafe_allow_html=True)

    # ✅ Récupérer les vraies stats complètes
    data = get_province_full_stats(annee=annee_filter, mois=mois_filter,
                                    role_view=role_view)

    if not data or all(row["total"] == 0 for row in data):
        st.markdown(render_empty("INBOX", "Aucune donnée",
                                  "Aucune donnée saisie sur cette période"),
                    unsafe_allow_html=True)
        st.markdown(render_section_close(), unsafe_allow_html=True)
        return

    df = pd.DataFrame(data)

    # Définir les statuts à afficher selon le rôle
    if role_view == "admin_regional":
        statuts_to_show = [
            ("valide_dp", "À valider par régional", "#F59E0B"),
            ("valide_regional", "Validés définitivement", "#10B981"),
            ("rejete_regional", "Rejetés régional", "#EF4444"),
        ]
    else:
        statuts_to_show = [
            ("brouillon", "Brouillon", "#94A3B8"),
            ("soumis", "Soumis", "#3B82F6"),
            ("valide_dp", "Validé DP", "#F59E0B"),
            ("rejete_dp", "Rejeté DP", "#F87171"),
            ("valide_regional", "Validé Régional", "#10B981"),
            ("rejete_regional", "Rejeté Régional", "#EF4444"),
        ]

    fig = go.Figure()

    for col_name, display_name, color in statuts_to_show:
        if col_name in df.columns:
            values = df[col_name].tolist()
            # N'afficher que si au moins une valeur > 0
            if sum(values) > 0:
                fig.add_trace(go.Bar(
                    name=display_name,
                    y=df["nom_province"],
                    x=values,
                    orientation="h",
                    marker=dict(color=color),
                    text=[str(v) if v > 0 else "" for v in values],
                    textposition="inside",
                    textfont=dict(color="white", size=11),
                    hovertemplate=f"<b>%{{y}}</b><br>{display_name}: %{{x}}<extra></extra>",
                ))

    fig.update_layout(
        barmode="stack",
        height=350,
        xaxis_title="",
        yaxis_title="",
        margin=dict(l=20, r=20, t=20, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25,
                    xanchor="center", x=0.5),
    )
    fig = apply_chart_theme(fig)
    st.plotly_chart(fig, use_container_width=True, config=get_chart_config())

    st.markdown(render_section_close(), unsafe_allow_html=True)


def _render_timeline_chart(annee_filter, mois_filter, id_province, role_view):
    """Courbe temporelle de l'activité par province."""
    st.markdown(render_section_open("Évolution mensuelle par province",
                                     "TRENDING_UP",
                                     "Suivi de l'activité de saisie dans le temps"),
                unsafe_allow_html=True)

    data = get_activity_timeline(annee=annee_filter, mois=mois_filter,
                                  id_province=id_province, role_view=role_view)

    if not data:
        st.markdown(render_empty("INBOX", "Aucune donnée",
                                  "Aucune saisie enregistrée sur la période sélectionnée"),
                    unsafe_allow_html=True)
        st.markdown(render_section_close(), unsafe_allow_html=True)
        return

    df = pd.DataFrame(data)
    df["periode"] = df.apply(
        lambda r: f"{get_mois_name(r['mois'])[:3]} {r['annee']}", axis=1
    )
    df["periode_sort"] = df["annee"] * 100 + df["mois"]
    df = df.sort_values("periode_sort")

    province_colors = {
        "Tata": "#3B82F6",
        "Tiznit": "#10B981",
        "Chtouka Ait Baha": "#F59E0B",
        "Taroudant": "#EF4444",
        "Inezgane Ait Melloul": "#8B5CF6",
        "Agadir": "#EC4899",
    }

    fig = go.Figure()

    for province in df["nom_province"].unique():
        prov_df = df[df["nom_province"] == province].sort_values("periode_sort")

        fig.add_trace(go.Scatter(
            x=prov_df["periode"],
            y=prov_df["nb_total"],
            mode="lines+markers",
            name=province,
            line=dict(color=province_colors.get(province, "#6B7280"), width=2),
            marker=dict(size=8),
            hovertemplate=f"<b>{province}</b><br>%{{x}}<br>%{{y}} saisies<extra></extra>",
        ))

    fig.update_layout(
        height=400,
        xaxis_title="",
        yaxis_title="Nombre de saisies",
        hovermode="x unified",
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.3,
            xanchor="center", x=0.5
        ),
        margin=dict(l=20, r=20, t=20, b=80),
    )
    fig = apply_chart_theme(fig)
    st.plotly_chart(fig, use_container_width=True, config=get_chart_config())

    st.markdown(render_section_close(), unsafe_allow_html=True)


def _render_activity_summary(annee_filter, mois_filter, id_province, role_view):
    """Vue globale d'activité par DP avec détection des inactives."""
    subtitle = ("Participation des DP (données validées par admins DP)"
                if role_view == "admin_regional"
                else "Suivi de la participation de chaque province")

    st.markdown(render_section_open("État d'activité par DP", "ACTIVITY",
                                     subtitle),
                unsafe_allow_html=True)

    data = get_dp_activity_summary(annee=annee_filter, mois=mois_filter,
                                    id_province=id_province, role_view=role_view)

    if not data:
        st.markdown(render_empty("INBOX", "Aucune donnée"),
                    unsafe_allow_html=True)
        st.markdown(render_section_close(), unsafe_allow_html=True)
        return

    now = datetime.now()
    rows = []
    dp_inactives = []

    for dp in data:
        nb_total = dp.get("nb_total", 0)
        derniere_saisie = dp.get("derniere_saisie")

        if nb_total == 0:
            statut = "🔴 Aucune saisie"
            dp_inactives.append(dp["nom_province"])
        else:
            if derniere_saisie:
                jours_depuis = (now - derniere_saisie).days
                if jours_depuis > 60:
                    statut = f"🟠 Inactif depuis {jours_depuis}j"
                elif jours_depuis > 30:
                    statut = f"🟡 {jours_depuis}j sans saisie"
                else:
                    statut = f"🟢 Actif"
            else:
                statut = "🔴 Aucune saisie"

        rows.append({
            "Province": dp["nom_province"],
            "Indicateurs": dp.get("nb_indicateurs", 0),
            "Réclamations": dp.get("nb_reclamations", 0),
            "Total saisies": nb_total,
            "Validés": dp.get("nb_valides", 0),
            "En attente": dp.get("nb_soumis", 0),
            "Dernière saisie": format_datetime(derniere_saisie) if derniere_saisie else "Jamais",
            "Statut": statut,
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Alerte si DP inactives (seulement si aucun filtre restrictif)
    if dp_inactives and not id_province:
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        periode_str = ""
        if annee_filter or mois_filter:
            parts = []
            if mois_filter:
                parts.append(MOIS_FR[mois_filter])
            if annee_filter:
                parts.append(str(annee_filter))
            periode_str = f" pour {' '.join(parts)}"

        st.markdown(
            f"<div style='background:#FEF2F2;border-left:3px solid #DC2626;"
            f"padding:0.75rem 1rem;border-radius:6px;font-size:0.85rem;color:#991B1B;'>"
            f"<strong>Alerte :</strong> {len(dp_inactives)} DP sans aucune saisie"
            f"{periode_str} : <strong>{', '.join(dp_inactives)}</strong>"
            f"</div>",
            unsafe_allow_html=True
        )

    # Graphique en barres
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name="Indicateurs",
        x=df["Province"],
        y=df["Indicateurs"],
        marker=dict(color="#3B82F6"),
        text=df["Indicateurs"],
        textposition="outside",
        textfont=dict(size=11),
    ))
    fig.add_trace(go.Bar(
        name="Réclamations",
        x=df["Province"],
        y=df["Réclamations"],
        marker=dict(color="#10B981"),
        text=df["Réclamations"],
        textposition="outside",
        textfont=dict(size=11),
    ))

    fig.update_layout(
        barmode="group",
        height=350,
        xaxis_title="",
        yaxis_title="Nombre de saisies",
        legend=dict(orientation="h", yanchor="bottom", y=-0.25,
                    xanchor="center", x=0.5),
        margin=dict(l=20, r=20, t=20, b=60),
    )
    fig = apply_chart_theme(fig)
    st.plotly_chart(fig, use_container_width=True, config=get_chart_config())

    st.markdown(render_section_close(), unsafe_allow_html=True)