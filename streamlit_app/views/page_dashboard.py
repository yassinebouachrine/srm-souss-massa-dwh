# views/page_dashboard.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from auth.session_manager import SessionManager
from db.queries import (
    get_dashboard_stats_filtered, get_province_full_stats, get_activity_timeline,
    get_dp_activity_summary, get_available_years_dashboard, get_dp_completion_and_activity,   
    get_reference_totals, get_provinces
)
from utils.helpers import format_datetime, get_mois_name, MOIS_FR
from utils.styles import (
    render_page_header, render_metric, render_section_open, render_section_close,
    render_empty, apply_chart_theme, get_chart_config, CHART_COLORS, STATUS_LABELS
)

def _pct(part, total):
    return round((part / total) * 100, 1) if total > 0 else 0

def render_dashboard():
    SessionManager.require_auth()
    user = SessionManager.get_user()
    role = user["role"]
    id_province = user["id_province"]

    st.markdown(render_page_header("Tableau de bord", f"Vue d'ensemble — {user['nom_complet']}"), unsafe_allow_html=True)
    role_view = "admin_regional" if role == "admin_regional" else None

    if role == "admin_regional":
        st.markdown(
            "<div style='background:#F0F9FF;border-left:3px solid #0EA5E9;padding:0.75rem 1rem;border-radius:6px;font-size:0.85rem;color:#075985;margin-bottom:1rem;'>"
            "<strong>Vue Admin Régional :</strong> Vous voyez uniquement les données déjà <strong>validées par les admins DP</strong>."
            "</div>", unsafe_allow_html=True
        )

    annees_dispo = get_available_years_dashboard() or [datetime.now().year]

    st.markdown(render_section_open("Filtres", "FILTER", "Filtres appliqués sur tout le tableau de bord"), unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    with f1:
        f_annee = st.selectbox("Année", ["Toutes"] + annees_dispo, key="dash_f_annee")
    with f2:
        f_mois = st.selectbox("Mois", ["Tous"] + list(range(1, 13)), format_func=lambda x: "Tous les mois" if x == "Tous" else MOIS_FR[x], key="dash_f_mois")
    with f3:
        if role in ["admin_regional", "super_admin"]:
            prov_options = [(None, "Toutes les provinces")] + [(p["id_province"], p["nom_province"]) for p in (get_provinces() or [])]
            f_prov = st.selectbox("Province", prov_options, format_func=lambda x: x[1] if isinstance(x, tuple) else x, key="dash_f_prov")
            selected_province = f_prov[0] if isinstance(f_prov, tuple) else None
        else:
            st.text_input("Province", value=user["nom_province"] or "—", disabled=True)
            selected_province = id_province
    st.markdown(render_section_close(), unsafe_allow_html=True)

    annee_filter = f_annee if f_annee != "Toutes" else None
    mois_filter = f_mois if f_mois != "Tous" else None

    stats = get_dashboard_stats_filtered(selected_province, annee_filter, mois_filter, role_view)
    indic = stats.get("indicateurs", {}) or {}
    reclam = stats.get("reclamations", {}) or {}

    # ✅ CORRECTION : Cacher les brouillons pour les admins (DP et Régional)
    if role in ["admin_dp", "admin_regional", "super_admin"]:
        indic.pop("brouillon", None)
        reclam.pop("brouillon", None)

    indic_total = sum(indic.values()) if indic else 0
    reclam_total = sum(reclam.values()) if reclam else 0

    indic_valides = indic.get("valide_regional", 0)
    reclam_valides = reclam.get("valide_regional", 0)
    indic_rejetes = indic.get("rejete_dp", 0) + indic.get("rejete_regional", 0)
    reclam_rejetes = reclam.get("rejete_dp", 0) + reclam.get("rejete_regional", 0)
    pending_i = indic.get("soumis", 0) + indic.get("valide_dp", 0)
    pending_r = reclam.get("soumis", 0) + reclam.get("valide_dp", 0)

    c1, c2, c3, c4 = st.columns(4, gap="small")
    with c1:
        st.markdown(render_metric("Indicateurs", indic_total, "CHART_BAR", sub=f"{indic_valides} validés définitivement", trend=(f"{_pct(indic_valides, indic_total)}% dans le DWH", "up")), unsafe_allow_html=True)
    with c2:
        st.markdown(render_metric("Réclamations", reclam_total, "CLIPBOARD", sub=f"{reclam_valides} validées définitivement", trend=(f"{_pct(reclam_valides, reclam_total)}% dans le DWH", "up")), unsafe_allow_html=True)
    with c3:
        st.markdown(render_metric("En attente", pending_i + pending_r, "CLOCK", sub=f"Ind: {pending_i} · Réc: {pending_r}", trend=(f"{_pct(pending_i + pending_r, indic_total + reclam_total)}% du total", "neutral")), unsafe_allow_html=True)
    with c4:
        total_rej = indic_rejetes + reclam_rejetes
        st.markdown(render_metric("Rejetés", total_rej, "X", sub=f"Ind: {indic_rejetes} · Réc: {reclam_rejetes}", trend=(f"{_pct(total_rej, indic_total + reclam_total)}% du total", "down" if total_rej > 0 else "neutral")), unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

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

    if role in ["admin_regional", "super_admin"]:
        _render_provinces_chart(annee_filter, mois_filter, role_view)

    col_l, col_r = st.columns(2, gap="medium")
    with col_l:
        st.markdown(render_section_open("Indicateurs — Répartition par statut", "CHART_BAR"), unsafe_allow_html=True)
        if indic_total > 0: _render_donut(indic, indic_total, key="donut_indicateurs")
        else: st.markdown(render_empty("INBOX", "Aucun indicateur"), unsafe_allow_html=True)
        st.markdown(render_section_close(), unsafe_allow_html=True)

    with col_r:
        st.markdown(render_section_open("Réclamations — Répartition par statut", "CLIPBOARD"), unsafe_allow_html=True)
        if reclam_total > 0: _render_donut(reclam, reclam_total, key="donut_reclamations")
        else: st.markdown(render_empty("INBOX", "Aucune réclamation"), unsafe_allow_html=True)
        st.markdown(render_section_close(), unsafe_allow_html=True)

    if role in ["admin_regional", "super_admin"]:
        _render_timeline_chart(annee_filter, mois_filter, selected_province, role_view)
        _render_activity_summary(annee_filter, mois_filter, selected_province, role_view)


def _render_donut(data, total, key):
    rows = [{"Statut": STATUS_LABELS.get(k, k), "Nombre": v, "color": CHART_COLORS.get(k, "#94A3B8")} for k, v in data.items() if v > 0]
    df = pd.DataFrame(rows)
    fig = go.Figure(data=[go.Pie(labels=df["Statut"], values=df["Nombre"], hole=0.6, marker=dict(colors=df["color"], line=dict(color="#FFFFFF", width=2)), textinfo="percent", textposition="inside", insidetextorientation="horizontal", textfont=dict(size=12, color="white", family="Inter"))])
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=20, b=20), annotations=[dict(text=f"<b>{total}</b><br><span style='font-size:11px;color:#6B7280;'>Total</span>", x=0.5, y=0.5, font=dict(size=24, color="#111827"), showarrow=False, align="center")], showlegend=True, legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5, font=dict(size=11, color="#374151"), bgcolor="rgba(0,0,0,0)"))
    st.plotly_chart(fig, use_container_width=True, config=get_chart_config(), key=key)
    
def _render_provinces_chart(annee_filter, mois_filter, role_view):
    st.markdown(render_section_open("Vue par province — Souss-Massa", "MAP_PIN", "Répartition par statut"), unsafe_allow_html=True)
    data = get_province_full_stats(annee=annee_filter, mois=mois_filter, role_view=role_view)
    if not data or all(row["total"] == 0 for row in data):
        st.markdown(render_empty("INBOX", "Aucune donnée"), unsafe_allow_html=True)
        st.markdown(render_section_close(), unsafe_allow_html=True)
        return
    df = pd.DataFrame(data)
    statuts = [("valide_dp", "À valider par régional", "#F59E0B"), ("valide_regional", "Validés définitivement", "#10B981"), ("rejete_regional", "Rejetés régional", "#EF4444")] if role_view == "admin_regional" else [("brouillon", "Brouillon", "#94A3B8"), ("soumis", "Soumis", "#3B82F6"), ("valide_dp", "Validé DP", "#F59E0B"), ("rejete_dp", "Rejeté DP", "#F87171"), ("valide_regional", "Validé Régional", "#10B981"), ("rejete_regional", "Rejeté Régional", "#EF4444")]
    fig = go.Figure()
    for col_name, display_name, color in statuts:
        if col_name in df.columns and df[col_name].sum() > 0:
            fig.add_trace(go.Bar(name=display_name, y=df["nom_province"], x=df[col_name], orientation="h", marker=dict(color=color)))
    fig.update_layout(barmode="stack", height=350, margin=dict(l=20, r=20, t=20, b=20), legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5))
    st.plotly_chart(apply_chart_theme(fig), use_container_width=True, config=get_chart_config())
    st.markdown(render_section_close(), unsafe_allow_html=True)

def _render_timeline_chart(annee_filter, mois_filter, id_province, role_view):
    st.markdown(render_section_open("Évolution mensuelle par province", "TRENDING_UP", "Suivi de l'activité"), unsafe_allow_html=True)
    data = get_activity_timeline(annee=annee_filter, mois=mois_filter, id_province=id_province, role_view=role_view, statut='valide_regional')
    if not data:
        st.markdown(render_empty("INBOX", "Aucune donnée"), unsafe_allow_html=True)
        st.markdown(render_section_close(), unsafe_allow_html=True)
        return
    df = pd.DataFrame(data)
    df["periode"] = df.apply(lambda r: f"{get_mois_name(r['mois'])[:3]} {r['annee']}", axis=1)
    df["periode_sort"] = df["annee"] * 100 + df["mois"]
    df = df.sort_values("periode_sort")
    fig = go.Figure()
    for prov in df["nom_province"].unique():
        prov_df = df[df["nom_province"] == prov].sort_values("periode_sort")
        fig.add_trace(go.Scatter(x=prov_df["periode"], y=prov_df["nb_total"], mode="lines+markers", name=prov))
    fig.update_layout(height=400, hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5), margin=dict(l=20, r=20, t=20, b=80))
    st.plotly_chart(apply_chart_theme(fig), use_container_width=True, config=get_chart_config())
    st.markdown(render_section_close(), unsafe_allow_html=True)

def _render_activity_summary(annee_filter, mois_filter, id_province, role_view):
    from db.queries import get_dp_final_validated_summary
    
    st.markdown(render_section_open("État d'activité par DP", "ACTIVITY", "Participation des DP"), unsafe_allow_html=True)
    
    data = get_dp_activity_summary(
        annee=annee_filter, mois=mois_filter,
        id_province=id_province, role_view=role_view
    ) or []

    comp_rows = get_dp_completion_and_activity(id_province, role_view) or []
    # Clés en int pour éviter les ratés id 6 vs "6"
    comp_data = {int(d["id_province"]): d for d in comp_rows if d.get("id_province") is not None}

    ref = get_reference_totals() or {"total_types_indic": 0, "total_types_reclam": 0}
    
    if not data:
        st.markdown(render_empty("INBOX", "Aucune donnée"), unsafe_allow_html=True)
        st.markdown(render_section_close(), unsafe_allow_html=True)
        return

    now = datetime.now()
    rows, inactifs = [], []
    for dp in data:
        nb, ds = dp.get("nb_total", 0), dp.get("derniere_saisie")
        comp = comp_data.get(int(dp["id_province"]), {})
        c_i = int(comp.get("types_indic_saisis") or 0)
        c_r = int(comp.get("types_reclam_saisis") or 0)
        
        if nb == 0:
            statut = "🔴 Aucune saisie"
            inactifs.append(dp["nom_province"])
        elif ds and ds.year == now.year and ds.month == now.month:
            statut = "🟢 Actif ce mois-ci"
        else:
            mois_ecart = (now.year - ds.year) * 12 + (now.month - ds.month) if ds else 99
            statut = "🟢 Actif ce mois-ci" if mois_ecart <= 0 else (f"🟡 Inactif (mois dernier)" if mois_ecart == 1 else f"🟠 Inactif depuis {mois_ecart} mois")
            if mois_ecart > 1: inactifs.append(dp["nom_province"])
            
        rows.append({
            "Province": dp["nom_province"],
            "Validés définitifs": dp.get("nb_valides", 0),
            "En attente": dp.get("nb_soumis", 0),
            "Complétude Indic": f"{c_i}/{ref['total_types_indic']}",
            "Complétude Réclam": f"{c_r}/{ref['total_types_reclam']}",
            "Dernière saisie": format_datetime(ds) if ds else "Jamais",
            "Statut": statut,
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    if inactifs and not id_province:
        st.markdown(f"<div style='background:#FEF2F2;border-left:3px solid #DC2626;padding:0.75rem 1rem;border-radius:6px;font-size:0.85rem;color:#991B1B;margin-top:1rem;'><strong>⚠️ Alerte :</strong> {len(inactifs)} DP inactives : <strong>{', '.join(inactifs)}</strong></div>", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════
    # ✅ GRAPHIQUE : DONNÉES VALIDÉES DÉFINITIVEMENT uniquement
    # ═══════════════════════════════════════════════════
    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
    st.markdown(render_section_open("Répartition des données validées définitivement par DP", "TRENDING_UP", 
                                     "Uniquement les données validées régional (prêtes pour le DWH)"), 
                unsafe_allow_html=True)

    final_data = get_dp_final_validated_summary(annee=annee_filter, mois=mois_filter)
    
    if not final_data or all(d["nb_indicateurs"] == 0 and d["nb_reclamations"] == 0 for d in final_data):
        st.markdown(render_empty("INBOX", "Aucune donnée validée définitivement", 
                                  "Les DP n'ont pas encore de données validées au niveau régional pour cette période."), 
                    unsafe_allow_html=True)
    else:
        df_final = pd.DataFrame(final_data)
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Indicateurs", x=df_final["nom_province"], y=df_final["nb_indicateurs"], 
                              marker=dict(color="#3B82F6"), text=df_final["nb_indicateurs"], textposition="outside"))
        fig.add_trace(go.Bar(name="Réclamations", x=df_final["nom_province"], y=df_final["nb_reclamations"], 
                              marker=dict(color="#10B981"), text=df_final["nb_reclamations"], textposition="outside"))
        fig.update_layout(
            barmode="group", height=380,
            xaxis_title="", yaxis_title="Nombre de données validées",
            legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
            margin=dict(l=20, r=20, t=50, b=60),
        )
        st.plotly_chart(apply_chart_theme(fig), use_container_width=True, config=get_chart_config())

    st.markdown(render_section_close(), unsafe_allow_html=True)
    st.markdown(render_section_close(), unsafe_allow_html=True)  # Ferme la section principale