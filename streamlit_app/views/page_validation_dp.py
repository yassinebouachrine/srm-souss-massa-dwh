# views/page_validation_dp.py
"""
Validation DP - Admin DP voit UNIQUEMENT :
- Lots soumis (statut = soumis) : à valider
- Lots rejetés au DP (statut = rejete_dp) : peut corriger si besoin
- Lots validés (statut = valide_dp) : historique traité
"""
import streamlit as st
import pandas as pd
from auth.session_manager import SessionManager
from auth.authentication import AuthManager
from db.queries import (
    get_staging_lots, get_staging_indicateurs, get_staging_reclamations,
    update_staging_status, get_rejected_lots, get_lot_corrections
)
from config.provinces import get_province_name, get_centres_for_province
from utils.helpers import format_datetime, get_mois_name, MOIS_FR
from utils.styles import (
    render_page_header, render_notice, render_empty,
    render_section_open, render_section_close, render_metric,
    render_lot_detail_card, render_action_bar, STATUS_LABELS
)


def render_validation_dp():
    SessionManager.require_role(["admin_dp", "super_admin"])
    user = SessionManager.get_user()
    id_province = user["id_province"]
    province_name = get_province_name(id_province)

    st.markdown(
        render_page_header("Validation DP", f"Province de {province_name}"),
        unsafe_allow_html=True,
    )

    all_indic = get_staging_lots(id_province=id_province, data_type="indicateurs") or []
    all_reclam = get_staging_lots(id_province=id_province, data_type="reclamations") or []

    indic_pending = [l for l in all_indic if l["statut"] == "soumis"]
    reclam_pending = [l for l in all_reclam if l["statut"] == "soumis"]
    indic_done = [l for l in all_indic if l["statut"] in ["valide_dp", "valide_regional"]]
    reclam_done = [l for l in all_reclam if l["statut"] in ["valide_dp", "valide_regional"]]
    indic_rej = [l for l in all_indic if l["statut"] in ["rejete_dp", "rejete_regional"]]
    reclam_rej = [l for l in all_reclam if l["statut"] in ["rejete_dp", "rejete_regional"]]

    # Métriques
    c1, c2, c3, c4 = st.columns(4, gap="small")
    with c1:
        st.markdown(render_metric("À valider (Ind.)", len(indic_pending), "CLOCK",
                                   sub="En attente"), unsafe_allow_html=True)
    with c2:
        st.markdown(render_metric("À valider (Réc.)", len(reclam_pending), "CLOCK",
                                   sub="En attente"), unsafe_allow_html=True)
    with c3:
        st.markdown(render_metric("Traités", len(indic_done) + len(reclam_done), "CHECK_CIRCLE",
                                   sub="Validés et transmis"), unsafe_allow_html=True)
    with c4:
        st.markdown(render_metric("Rejetés", len(indic_rej) + len(reclam_rej), "X",
                                   sub="À corriger"), unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    tab_queue, tab_rejected, tab_history = st.tabs([
        f"File d'attente ({len(indic_pending) + len(reclam_pending)})",
        f"Lots rejetés ({len(indic_rej) + len(reclam_rej)})",
        f"Historique traité ({len(indic_done) + len(reclam_done)})"
    ])

    with tab_queue:
        st.markdown(render_notice(
            "Sélectionnez plusieurs lots pour valider ou rejeter en masse.",
        ), unsafe_allow_html=True)

        sub_i, sub_r = st.tabs([
            f"Indicateurs ({len(indic_pending)})",
            f"Réclamations ({len(reclam_pending)})"
        ])

        with sub_i:
            _render_batch_ui("indicateurs", id_province, user, indic_pending)
        with sub_r:
            _render_batch_ui("reclamations", id_province, user, reclam_pending)

    with tab_rejected:
        st.markdown(render_notice(
            "En tant qu'admin DP, vous pouvez corriger les lots rejetés à la place des agents si nécessaire.",
            "info"
        ), unsafe_allow_html=True)

        sub_ri, sub_rr = st.tabs([
            f"Indicateurs rejetés ({len(indic_rej)})",
            f"Réclamations rejetées ({len(reclam_rej)})"
        ])

        with sub_ri:
            from views.page_indicateurs import render_rejected_lots
            render_rejected_lots("indicateurs", id_province, user,
                                 get_rejected_lots(id_province, "indicateurs") or [])
        with sub_rr:
            from views.page_indicateurs import render_rejected_lots
            render_rejected_lots("reclamations", id_province, user,
                                 get_rejected_lots(id_province, "reclamations") or [])

    with tab_history:
        _render_history_table(indic_done, reclam_done)


def _render_batch_ui(data_type, id_province, user, lots):
    if not lots:
        st.markdown(render_empty("CHECK_CIRCLE", "File d'attente vide",
                                  "Aucun lot en attente"), unsafe_allow_html=True)
        return

    lots_enr = _enrich_lots(lots, data_type)

    # Filtres
    st.markdown(render_section_open("Filtres", "FILTER"), unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    with f1:
        annees = sorted(set(l["annee"] for l in lots_enr), reverse=True)
        f_annee = st.selectbox("Année", ["Toutes"] + annees, key=f"fa_{data_type}")
    with f2:
        mois_dispo = sorted(set(l["mois_num"] for l in lots_enr))
        f_mois = st.selectbox("Mois", ["Tous"] + mois_dispo,
                               format_func=lambda x: "Tous" if x == "Tous" else MOIS_FR[x],
                               key=f"fm_{data_type}")
    with f3:
        centres = get_centres_for_province(id_province)
        f_centre = st.selectbox("Centre",
                                 ["Tous"] + [c["nom"] for c in centres],
                                 key=f"fc_{data_type}")
    st.markdown(render_section_close(), unsafe_allow_html=True)

    filtered = [l for l in lots_enr
                if (f_annee == "Toutes" or l["annee"] == f_annee)
                and (f_mois == "Tous" or l["mois_num"] == f_mois)
                and (f_centre == "Tous" or l["centre"] == f_centre)]

    st.markdown(f"<div style='color:#6B7280;font-size:0.85rem;margin:0.5rem 0;'>"
                f"<strong style='color:#111827;'>{len(filtered)}</strong> lot(s) affiché(s)</div>",
                unsafe_allow_html=True)

    if not filtered:
        st.markdown(render_empty("FILTER", "Aucun lot"), unsafe_allow_html=True)
        return

    # Sélection
    st.markdown(render_section_open("Lots à valider", "LAYERS"), unsafe_allow_html=True)

    sel_key = f"sel_{data_type}"
    if sel_key not in st.session_state:
        st.session_state[sel_key] = set()

    tc1, tc2 = st.columns([1, 5])
    with tc1:
        if st.button("Tout sélectionner", key=f"selall_{data_type}", use_container_width=True):
            st.session_state[sel_key] = set(l["lot_id"] for l in filtered)
            st.rerun()
    with tc2:
        if st.button("Tout désélectionner", key=f"unsel_{data_type}"):
            st.session_state[sel_key] = set()
            st.rerun()

    rows = []
    for lot in filtered:
        rows.append({
            "✓": lot["lot_id"] in st.session_state[sel_key],
            "Agent": lot["agent"],
            "Centre": lot["centre"],
            "Période": f"{get_mois_name(lot['mois_num'])[:3]} {lot['annee']}",
            "Enreg.": lot["nb"],
            "Soumis le": lot["date_soum"],
        })

    df_display = pd.DataFrame(rows)
    edited = st.data_editor(
        df_display, use_container_width=True, hide_index=True,
        disabled=["Agent", "Centre", "Période", "Enreg.", "Soumis le"],
        column_config={"✓": st.column_config.CheckboxColumn("Sél.", width="small")},
        key=f"editor_{data_type}",
    )

    for i, row in edited.iterrows():
        lot_id = filtered[i]["lot_id"]
        if row["✓"]:
            st.session_state[sel_key].add(lot_id)
        else:
            st.session_state[sel_key].discard(lot_id)

    selected_ids = list(st.session_state[sel_key])
    nb_sel = len(selected_ids)
    st.markdown(render_section_close(), unsafe_allow_html=True)

    # Actions
    st.markdown(render_action_bar(nb_sel), unsafe_allow_html=True)

    if nb_sel > 0:
        comment_mass = st.text_area("Commentaire (obligatoire pour un rejet)",
                                     key=f"cmt_{data_type}", height=80)

        ac1, ac2, _ = st.columns([1.2, 1.2, 3])
        with ac1:
            st.markdown('<div class="btn-success">', unsafe_allow_html=True)
            if st.button(f"Valider les {nb_sel} lot(s)",
                         key=f"vall_{data_type}", use_container_width=True):
                for lid in selected_ids:
                    update_staging_status(data_type, lid, "valide_dp",
                                          user["id"], comment_mass, "dp")
                    AuthManager.log_action(user["id"],
                                            f"VALIDATION_DP_{data_type.upper()}",
                                            f"staging_{data_type}_dp",
                                            details={"lot_id": lid})
                st.session_state[sel_key] = set()
                st.success(f"{nb_sel} lot(s) validé(s) et transmis au régional.")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with ac2:
            st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
            if st.button(f"Rejeter les {nb_sel} lot(s)",
                         key=f"rall_{data_type}", use_container_width=True):
                if not comment_mass:
                    st.error("Commentaire obligatoire pour un rejet.")
                else:
                    for lid in selected_ids:
                        update_staging_status(data_type, lid, "rejete_dp",
                                              user["id"], comment_mass, "dp")
                        AuthManager.log_action(user["id"],
                                                f"REJET_DP_{data_type.upper()}",
                                                f"staging_{data_type}_dp",
                                                details={"lot_id": lid, "motif": comment_mass})
                    st.session_state[sel_key] = set()
                    st.warning(f"{nb_sel} lot(s) rejeté(s), retournés à l'agent.")
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════
    # INSPECTION D'UN LOT (avec historique des corrections)
    # ═══════════════════════════════════════════════════════════
    st.markdown(render_section_open("Inspection d'un lot", "EYE"), unsafe_allow_html=True)
    opts = {f"{l['agent']} — {get_mois_name(l['mois_num'])} {l['annee']} — {l['centre']} "
            f"({l['nb']} enreg.)": l for l in filtered}
    sel = st.selectbox("Choisir un lot", ["— Sélectionner —"] + list(opts.keys()),
                        key=f"insp_{data_type}")

    if sel != "— Sélectionner —":
        lot = opts[sel]
        st.markdown(render_lot_detail_card({
            "lot_id": lot["lot_id"], "agent": lot["agent"], "centre": lot["centre"],
            "mois": get_mois_name(lot["mois_num"]), "annee": lot["annee"],
            "nb": lot["nb"], "date_soum": lot["date_soum"],
        }), unsafe_allow_html=True)

        df = pd.DataFrame(lot["details"])

        # Affichage des données
        if data_type == "indicateurs":
            cols_source = ["code_indicateur", "libelle_indicateur", "categorie",
                           "unite", "valeur_indicateur"]
            available = [c for c in cols_source if c in df.columns]
            df_show = df[available].copy()
            df_show = df_show.rename(columns={
                "code_indicateur": "Code",
                "libelle_indicateur": "Indicateur",
                "categorie": "Catégorie",
                "unite": "Unité",
                "valeur_indicateur": "Valeur",
            })
        else:
            cols_source = ["code_type", "libelle_reclamation",
                           "categorie_reclamation", "valeur_brute"]
            available = [c for c in cols_source if c in df.columns]
            df_show = df[available].copy()
            df_show = df_show.rename(columns={
                "code_type": "Code",
                "libelle_reclamation": "Type",
                "categorie_reclamation": "Catégorie",
                "valeur_brute": "Valeur",
            })

        st.dataframe(df_show, use_container_width=True, hide_index=True)

        # ═══════════════════════════════════════════════════════════
        # ✅ NOUVEAU : Historique des corrections du lot
        # ═══════════════════════════════════════════════════════════
        corrections = get_lot_corrections(lot["lot_id"])
        if corrections:
            st.markdown("---")
            st.markdown("#### Historique des corrections")
            st.markdown(render_notice(
                f"Ce lot a été corrigé <strong>{len(corrections)}</strong> fois "
                f"avant d'être resoumis. Consultez le détail ci-dessous avant validation.",
                "info"
            ), unsafe_allow_html=True)

            corr_rows = []
            for c in corrections:
                corr_rows.append({
                    "Date": format_datetime(c["date_correction"]),
                    "Corrigé par": c.get("corrige_par_nom", "—"),
                    "Rôle": c.get("role_correcteur", "—"),
                    "Élément": c.get("libelle_element", c.get("code_element", "—")),
                    "Champ": c["champ_modifie"],
                    "Ancienne valeur": c["ancienne_valeur"],
                    "Nouvelle valeur": c["nouvelle_valeur"],
                    "Motif rejet initial": c.get("motif_rejet", "—"),
                })
            st.dataframe(pd.DataFrame(corr_rows),
                         use_container_width=True, hide_index=True)

            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            col_s1, _, _ = st.columns([1, 1, 2])
            with col_s1:
                st.metric("Total corrections", len(corrections))
        else:
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            st.markdown(
                "<div style='color:#6B7280;font-size:0.82rem;font-style:italic;'>"
                "Aucune correction préalable — première soumission de ce lot."
                "</div>",
                unsafe_allow_html=True
            )

    st.markdown(render_section_close(), unsafe_allow_html=True)


def _render_history_table(indic_done, reclam_done):
    st.markdown(render_notice("Historique des lots que vous avez validés."),
                unsafe_allow_html=True)

    tab_i, tab_r = st.tabs(["Indicateurs", "Réclamations"])

    with tab_i:
        if indic_done:
            df = pd.DataFrame(indic_done)
            df["Créé le"] = df["date_creation"].apply(format_datetime)
            df["Mois"] = df["mois"].apply(get_mois_name)
            df["Statut"] = df["statut"].map(STATUS_LABELS).fillna(df["statut"])
            st.dataframe(df[["annee", "Mois", "Statut", "nb_enregistrements", "Créé le"]],
                         use_container_width=True, hide_index=True)
        else:
            st.markdown(render_empty("ARCHIVE", "Aucun historique"),
                        unsafe_allow_html=True)

    with tab_r:
        if reclam_done:
            df = pd.DataFrame(reclam_done)
            df["Créé le"] = df["date_creation"].apply(format_datetime)
            df["Mois"] = df["mois"].apply(get_mois_name)
            df["Statut"] = df["statut"].map(STATUS_LABELS).fillna(df["statut"])
            st.dataframe(df[["annee", "Mois", "Statut", "nb_enregistrements", "Créé le"]],
                         use_container_width=True, hide_index=True)
        else:
            st.markdown(render_empty("ARCHIVE", "Aucun historique"),
                        unsafe_allow_html=True)


def _enrich_lots(lots, data_type):
    enriched = []
    for lot in lots:
        if data_type == "indicateurs":
            details = get_staging_indicateurs(lot_id=lot["lot_id"])
        else:
            details = get_staging_reclamations(lot_id=lot["lot_id"])
        if details:
            first = details[0]
            enriched.append({
                "lot_id": lot["lot_id"],
                "agent": first.get("soumis_par_nom", "—"),
                "centre": first.get("nom_centre", "—"),
                "annee": lot["annee"],
                "mois_num": lot["mois"],
                "nb": lot["nb_enregistrements"],
                "date_soum": format_datetime(first.get("date_soumission")),
                "details": details,
            })
    return enriched