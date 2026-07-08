# views/page_validation_dp.py
"""
Page de validation DP OPTIMISEE pour traiter beaucoup de lots facilement.

Fonctionnalites :
- Vue synthétique en tableau de tous les lots en attente
- Filtres avancés (date, centre, agent)
- Sélection multiple pour validation/rejet en masse
- Vue détaillée d'un lot à la demande
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from auth.session_manager import SessionManager
from auth.authentication import AuthManager
from db.queries import (
    get_staging_lots, get_staging_indicateurs, get_staging_reclamations,
    update_staging_status
)
from config.provinces import get_province_name, get_centres_for_province
from utils.helpers import format_datetime, get_mois_name, MOIS_FR
from utils.styles import (
    render_page_header, render_notice, render_empty,
    render_section_open, render_section_close, get_status_badge,
    Icon, render_metric
)


def render_validation_dp():
    SessionManager.require_role(["admin_dp", "super_admin"])
    user = SessionManager.get_user()
    id_province = user["id_province"]
    province_name = get_province_name(id_province)

    st.markdown(
        render_page_header("Validation DP",
                           f"Province de {province_name} — Vérification des soumissions"),
        unsafe_allow_html=True,
    )

    # ── Stats rapides ──
    indic_pending = get_staging_lots(id_province=id_province, statut="soumis",
                                      data_type="indicateurs") or []
    reclam_pending = get_staging_lots(id_province=id_province, statut="soumis",
                                       data_type="reclamations") or []
    indic_recent = get_staging_lots(id_province=id_province, statut="valide_dp",
                                     data_type="indicateurs") or []
    reclam_recent = get_staging_lots(id_province=id_province, statut="valide_dp",
                                      data_type="reclamations") or []

    c1, c2, c3, c4 = st.columns(4, gap="small")
    with c1:
        st.markdown(render_metric("Indicateurs à valider", len(indic_pending), "CLOCK",
                                   sub="En attente de votre revue"),
                    unsafe_allow_html=True)
    with c2:
        st.markdown(render_metric("Réclamations à valider", len(reclam_pending), "CLOCK",
                                   sub="En attente de votre revue"),
                    unsafe_allow_html=True)
    with c3:
        st.markdown(render_metric("Indic. validés (récent)", len(indic_recent), "CHECK_CIRCLE",
                                   sub="Transmis au régional"),
                    unsafe_allow_html=True)
    with c4:
        st.markdown(render_metric("Réc. validées (récent)", len(reclam_recent), "CHECK_CIRCLE",
                                   sub="Transmis au régional"),
                    unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    st.markdown(render_notice(
        "Utilisez la vue synthétique pour valider plusieurs lots à la fois. "
        "Cliquez sur « Détails » pour inspecter un lot spécifique.", "info"
    ), unsafe_allow_html=True)

    tab_i, tab_r = st.tabs([
        f"Indicateurs ({len(indic_pending)})",
        f"Réclamations ({len(reclam_pending)})"
    ])

    with tab_i:
        _render_batch_validation("indicateurs", id_province, user)

    with tab_r:
        _render_batch_validation("reclamations", id_province, user)


def _render_batch_validation(data_type: str, id_province: int, user: dict):
    """Vue optimisée pour valider plusieurs lots en masse."""
    lots = get_staging_lots(id_province=id_province, statut="soumis", data_type=data_type)

    if not lots:
        st.markdown(render_empty("CHECK_CIRCLE", "Aucun élément à valider",
                                  "Toutes les données ont été traitées"),
                    unsafe_allow_html=True)
        return

    # ══════════════════════════════════════════
    # FILTRES
    # ══════════════════════════════════════════
    st.markdown(render_section_open("Filtres", "FILTER"), unsafe_allow_html=True)

    f1, f2, f3, f4 = st.columns(4)

    with f1:
        annees = sorted(set(l["annee"] for l in lots), reverse=True)
        f_annee = st.selectbox("Année", ["Toutes"] + annees, key=f"f_a_{data_type}")

    with f2:
        mois_dispo = sorted(set(l["mois"] for l in lots))
        f_mois = st.selectbox("Mois", ["Tous"] + mois_dispo,
                               format_func=lambda x: "Tous" if x == "Tous" else MOIS_FR[x],
                               key=f"f_m_{data_type}")

    with f3:
        agents = sorted(set(_get_agent_name(l["lot_id"], data_type) for l in lots))
        agents = [a for a in agents if a]
        f_agent = st.selectbox("Agent", ["Tous"] + agents, key=f"f_ag_{data_type}")

    with f4:
        centres = get_centres_for_province(id_province)
        centre_names = [c["nom"] for c in centres]
        f_centre = st.selectbox("Centre", ["Tous"] + centre_names, key=f"f_c_{data_type}")

    st.markdown(render_section_close(), unsafe_allow_html=True)

    # Appliquer les filtres
    filtered_lots = lots
    if f_annee != "Toutes":
        filtered_lots = [l for l in filtered_lots if l["annee"] == f_annee]
    if f_mois != "Tous":
        filtered_lots = [l for l in filtered_lots if l["mois"] == f_mois]

    # Enrichir les lots avec les détails
    lots_enriched = []
    for lot in filtered_lots:
        if data_type == "indicateurs":
            details = get_staging_indicateurs(lot_id=lot["lot_id"])
        else:
            details = get_staging_reclamations(lot_id=lot["lot_id"])

        if details:
            first = details[0]
            agent = first.get("soumis_par_nom", "—")
            centre = first.get("nom_centre", "—")

            if f_agent != "Tous" and agent != f_agent:
                continue
            if f_centre != "Tous" and centre != f_centre:
                continue

            lots_enriched.append({
                "lot_id": lot["lot_id"],
                "agent": agent,
                "centre": centre,
                "mois": get_mois_name(lot["mois"]),
                "annee": lot["annee"],
                "nb": lot["nb_enregistrements"],
                "date_soum": format_datetime(first.get("date_soumission")),
                "raw": lot,
                "details": details,
            })

    st.markdown(f"<div style='color:#6B7280;font-size:0.85rem;margin-bottom:0.5rem;'>"
                f"<strong>{len(lots_enriched)}</strong> lot(s) trouvé(s)</div>",
                unsafe_allow_html=True)

    if not lots_enriched:
        st.markdown(render_empty("FILTER", "Aucun lot", "Modifiez les filtres pour voir plus de résultats"),
                    unsafe_allow_html=True)
        return

    # ══════════════════════════════════════════
    # VUE TABLEAU SYNTHETIQUE + CHECKBOX
    # ══════════════════════════════════════════
    st.markdown(render_section_open(
        "Sélection multiple", "LAYERS",
        "Cochez plusieurs lots pour les valider ou rejeter en une seule action"
    ), unsafe_allow_html=True)

    # État de sélection
    sel_key = f"sel_{data_type}"
    if sel_key not in st.session_state:
        st.session_state[sel_key] = {}

    # En-tête sélection tout
    hc1, hc2, hc3, hc4, hc5, hc6, hc7 = st.columns([0.4, 1.5, 1.5, 1, 0.6, 1.2, 0.8])
    with hc1:
        select_all = st.checkbox("", key=f"sa_{data_type}",
                                  help="Tout sélectionner")
    with hc2: st.markdown("**Lot**")
    with hc3: st.markdown("**Agent**")
    with hc4: st.markdown("**Centre**")
    with hc5: st.markdown("**Période**")
    with hc6: st.markdown("**Soumis le**")
    with hc7: st.markdown("**Enreg.**")

    st.markdown("<hr style='margin:0.3rem 0;'>", unsafe_allow_html=True)

    if select_all:
        for lot in lots_enriched:
            st.session_state[sel_key][lot["lot_id"]] = True

    # Liste des lots
    for lot in lots_enriched:
        rc1, rc2, rc3, rc4, rc5, rc6, rc7 = st.columns([0.4, 1.5, 1.5, 1, 0.6, 1.2, 0.8])

        with rc1:
            checked = st.checkbox("", key=f"chk_{data_type}_{lot['lot_id']}",
                                   value=st.session_state[sel_key].get(lot["lot_id"], False))
            st.session_state[sel_key][lot["lot_id"]] = checked

        with rc2:
            st.markdown(f"<code style='font-size:0.7rem;'>{lot['lot_id'][:20]}...</code>",
                        unsafe_allow_html=True)
        with rc3:
            st.markdown(f"<span style='font-size:0.82rem;'>{lot['agent']}</span>",
                        unsafe_allow_html=True)
        with rc4:
            st.markdown(f"<span style='font-size:0.82rem;'>{lot['centre']}</span>",
                        unsafe_allow_html=True)
        with rc5:
            st.markdown(f"<span style='font-size:0.82rem;'>{lot['mois'][:3]} {lot['annee']}</span>",
                        unsafe_allow_html=True)
        with rc6:
            st.markdown(f"<span style='font-size:0.75rem;color:#6B7280;'>{lot['date_soum']}</span>",
                        unsafe_allow_html=True)
        with rc7:
            st.markdown(f"<strong style='font-size:0.85rem;'>{lot['nb']}</strong>",
                        unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ══════════════════════════════════════════
    # ACTIONS DE MASSE
    # ══════════════════════════════════════════
    selected_ids = [lid for lid, sel in st.session_state[sel_key].items() if sel]
    nb_selected = len(selected_ids)

    comment_mass = st.text_area(
        f"Commentaire pour les {nb_selected} lot(s) sélectionné(s)",
        placeholder="Obligatoire en cas de rejet",
        key=f"cm_{data_type}",
        height=70,
    )

    ac1, ac2, ac3 = st.columns([1, 1, 3])
    with ac1:
        st.markdown('<div class="btn-success">', unsafe_allow_html=True)
        if st.button(f"Valider ({nb_selected})", key=f"vall_{data_type}",
                     use_container_width=True, disabled=(nb_selected == 0)):
            for lid in selected_ids:
                update_staging_status(data_type, lid, "valide_dp",
                                      user["id"], comment_mass, "dp")
                AuthManager.log_action(user["id"],
                                        f"VALIDATION_DP_{data_type.upper()}_MASS",
                                        f"staging_{data_type}_dp",
                                        details={"lot_id": lid})
            st.session_state[sel_key] = {}
            st.success(f"{nb_selected} lot(s) validé(s).")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with ac2:
        st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
        if st.button(f"Rejeter ({nb_selected})", key=f"rall_{data_type}",
                     use_container_width=True, disabled=(nb_selected == 0)):
            if not comment_mass:
                st.error("Commentaire obligatoire pour un rejet.")
            else:
                for lid in selected_ids:
                    update_staging_status(data_type, lid, "rejete_dp",
                                          user["id"], comment_mass, "dp")
                    AuthManager.log_action(user["id"],
                                            f"REJET_DP_{data_type.upper()}_MASS",
                                            f"staging_{data_type}_dp",
                                            details={"lot_id": lid, "motif": comment_mass})
                st.session_state[sel_key] = {}
                st.warning(f"{nb_selected} lot(s) rejeté(s).")
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(render_section_close(), unsafe_allow_html=True)

    # ══════════════════════════════════════════
    # DETAILS D'UN LOT
    # ══════════════════════════════════════════
    st.markdown(render_section_open("Détails d'un lot", "EYE",
                                     "Sélectionnez un lot pour voir les données saisies"),
                unsafe_allow_html=True)

    lot_options = {f"{l['lot_id'][:25]}... — {l['agent']} ({l['nb']} enreg.)": l
                   for l in lots_enriched}
    selected_lot_key = st.selectbox("Choisir un lot", ["—"] + list(lot_options.keys()),
                                     key=f"det_{data_type}")

    if selected_lot_key != "—":
        lot = lot_options[selected_lot_key]

        st.markdown(f"""
        <div style='background:#F9FAFB;padding:0.75rem 1rem;border-radius:6px;margin-bottom:1rem;'>
            <div style='font-size:0.85rem;color:#374151;'>
                <strong>Lot :</strong> <code>{lot['lot_id']}</code><br>
                <strong>Agent :</strong> {lot['agent']} · <strong>Centre :</strong> {lot['centre']} ·
                <strong>Période :</strong> {lot['mois']} {lot['annee']}<br>
                <strong>Soumis le :</strong> {lot['date_soum']}
            </div>
        </div>
        """, unsafe_allow_html=True)

        details = lot["details"]
        df = pd.DataFrame(details)
        if data_type == "indicateurs":
            cols = ["code_indicateur", "libelle_indicateur", "unite",
                    "valeur_mensuelle", "valeur_recapitulatif"]
        else:
            cols = ["code_type", "libelle_reclamation", "nombre_reclamations",
                    "temps_moyen_coupure_h", "delai_moyen_traitement_j", "valeur_brute"]

        st.dataframe(df[[c for c in cols if c in df.columns]],
                     use_container_width=True, hide_index=True)

        # Actions individuelles
        comment_ind = st.text_area("Commentaire (individuel)",
                                    key=f"ci_{data_type}_{lot['lot_id']}",
                                    height=70)

        bc1, bc2, _ = st.columns([1, 1, 3])
        with bc1:
            st.markdown('<div class="btn-success">', unsafe_allow_html=True)
            if st.button("Valider ce lot", key=f"v1_{data_type}_{lot['lot_id']}",
                         use_container_width=True):
                update_staging_status(data_type, lot["lot_id"], "valide_dp",
                                      user["id"], comment_ind, "dp")
                st.success("Lot validé.")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with bc2:
            st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
            if st.button("Rejeter ce lot", key=f"r1_{data_type}_{lot['lot_id']}",
                         use_container_width=True):
                if not comment_ind:
                    st.error("Commentaire obligatoire.")
                else:
                    update_staging_status(data_type, lot["lot_id"], "rejete_dp",
                                          user["id"], comment_ind, "dp")
                    st.warning("Lot rejeté.")
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(render_section_close(), unsafe_allow_html=True)


def _get_agent_name(lot_id: str, data_type: str) -> str:
    """Récupère le nom de l'agent qui a soumis le lot."""
    try:
        if data_type == "indicateurs":
            details = get_staging_indicateurs(lot_id=lot_id)
        else:
            details = get_staging_reclamations(lot_id=lot_id)
        return details[0].get("soumis_par_nom", "—") if details else "—"
    except:
        return "—"