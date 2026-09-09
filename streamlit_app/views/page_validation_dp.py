# views/page_validation_dp.py
"""Validation DP - Admin DP valide/rejette les lots soumis par les agents uniquement."""

import streamlit as st
import pandas as pd
import time

from auth.session_manager import SessionManager
from auth.authentication import AuthManager
from db.queries import (
    get_staging_lots, get_lot_details_indicateurs, get_lot_details_reclamations,
    validate_donnees_batch, update_donnee_with_correction,
    get_lots_rejets_regional_pour_admin_dp, transfert_lot_a_agent, submit_lot,
    resubmit_lot_after_rejection,
    get_demandes_pour_user, get_admin_dp_de_province,
    demander_modification_lot, resoumettre_apres_modif_admin_dp,
    marquer_demandes_traitees,
)
from config.provinces import get_province_name, get_centres_for_province
from utils.helpers import format_datetime, get_mois_name, MOIS_FR
from utils.styles import (
    render_page_header, render_notice, render_empty, render_section_open, render_section_close,
    render_metric, render_lot_detail_card, STATUS_LABELS, get_status_badge
)
from utils.history_display import render_historique_complet_lot, render_data_table_with_history
from utils.pagination import paginate_list


def _val_display_reclamation(r):
    """Retourne la valeur en STRING pour l'affichage/édition dans data_editor."""
    if r.get("code_type") == "AUTRES":
        return str(r.get("commentaire_autre") or "")
    v = r.get("valeur_brute", 0)
    if v is None:
        return "0"
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v)


def render_validation_dp():
    SessionManager.require_role(["admin_dp", "super_admin"])
    user = SessionManager.get_user()
    id_province = user["id_province"]
    province_name = user["nom_province"] or get_province_name(id_province)

    st.markdown(render_page_header("Validation DP", f"Province de {province_name}"), unsafe_allow_html=True)

    all_i = get_staging_lots(id_province=id_province, type_donnees="indicateurs") or []
    all_r = get_staging_lots(id_province=id_province, type_donnees="reclamations") or []

    statuts_pend = ["soumis", "en_cours_validation_dp"]
    i_pend = [l for l in all_i if l["statut"] in statuts_pend and l["cree_par"] != user["id"]]
    r_pend = [l for l in all_r if l["statut"] in statuts_pend and l["cree_par"] != user["id"]]

    i_rej_reg = get_lots_rejets_regional_pour_admin_dp(id_province, "indicateurs") or []
    r_rej_reg = get_lots_rejets_regional_pour_admin_dp(id_province, "reclamations") or []

    i_demandes = get_demandes_pour_user(user["id"], "indicateurs") or []
    r_demandes = get_demandes_pour_user(user["id"], "reclamations") or []

    i_done = [l for l in all_i if l["statut"] in ["valide_dp", "valide_regional", "en_cours_validation_regional"]]
    r_done = [l for l in all_r if l["statut"] in ["valide_dp", "valide_regional", "en_cours_validation_regional"]]

    c1, c2, c3, c4, c5 = st.columns(5, gap="small")
    with c1: st.markdown(render_metric("À valider (Ind.)", len(i_pend), "CLOCK"), unsafe_allow_html=True)
    with c2: st.markdown(render_metric("À valider (Réc.)", len(r_pend), "CLOCK"), unsafe_allow_html=True)
    with c3: st.markdown(render_metric("Rejets régional", len(i_rej_reg) + len(r_rej_reg), "ALERT"), unsafe_allow_html=True)
    with c4: st.markdown(render_metric("Modif. demandées", len(i_demandes) + len(r_demandes), "EDIT"), unsafe_allow_html=True)
    with c5: st.markdown(render_metric("Traités", len(i_done) + len(r_done), "CHECK_CIRCLE"), unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    tab_queue, tab_rej_reg, tab_demandes, tab_history = st.tabs([
        f"File d'attente ({len(i_pend) + len(r_pend)})",
        f"Rejets régional ({len(i_rej_reg) + len(r_rej_reg)})",
        f"Modifications demandées ({len(i_demandes) + len(r_demandes)})",
        f"Historique traité ({len(i_done) + len(r_done)})"
    ])

    with tab_queue:
        st.markdown(render_notice(
            "Lots soumis par les <strong>agents DP</strong> de votre province. "
            "Vos propres saisies sont auto-validées et transmises directement au régional."
        ), unsafe_allow_html=True)
        sub_i, sub_r = st.tabs([f"Indicateurs ({len(i_pend)})", f"Réclamations ({len(r_pend)})"])
        with sub_i:
            _render_val_ui("indicateurs", id_province, user, i_pend)
        with sub_r:
            _render_val_ui("reclamations", id_province, user, r_pend)

    with tab_rej_reg:
        _render_rejets_regional_ui(user, i_rej_reg, r_rej_reg)

    with tab_demandes:
        _render_demandes_modification_ui(user, i_demandes, r_demandes)

    with tab_history:
        _render_history_table(i_done, r_done)


def _render_val_ui(data_type, id_province, user, lots):
    if not lots:
        st.markdown(render_empty("CHECK_CIRCLE", "File d'attente vide"), unsafe_allow_html=True)
        return

    st.markdown(render_section_open("Filtres", "FILTER"), unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    with f1:
        annees = sorted(set(l["annee"] for l in lots), reverse=True)
        f_annee = st.selectbox("Année", ["Toutes"] + annees, key=f"fa_{data_type}")
    with f2:
        mois_d = sorted(set(l["mois"] for l in lots))
        f_mois = st.selectbox("Mois", ["Tous"] + mois_d, format_func=lambda x: "Tous" if x == "Tous" else MOIS_FR[x], key=f"fm_{data_type}")
    with f3:
        centres = get_centres_for_province(id_province)
        f_centre = st.selectbox("Centre", ["Tous"] + [c["nom"] for c in centres], key=f"fc_{data_type}")
    st.markdown(render_section_close(), unsafe_allow_html=True)

    filtered = [l for l in lots if
                (f_annee == "Toutes" or l["annee"] == f_annee)
                and (f_mois == "Tous" or l["mois"] == f_mois)
                and (f_centre == "Tous" or l["nom_centre"] == f_centre)]

    if not filtered:
        st.markdown(render_empty("FILTER", "Aucun lot"), unsafe_allow_html=True)
        return

    st.markdown(render_section_open("Sélection multiple (validation/rejet en masse)", "LAYERS"), unsafe_allow_html=True)

    sel_key = f"sel_dp_{data_type}"
    if sel_key not in st.session_state:
        st.session_state[sel_key] = set()

    tc1, tc2, _ = st.columns([1.2, 1.2, 4])
    with tc1:
        if st.button("Tout sélectionner", key=f"selall_{data_type}", use_container_width=True):
            st.session_state[sel_key] = set(l["id_lot"] for l in filtered)
            st.rerun()
    with tc2:
        if st.button("Tout désélectionner", key=f"unsel_{data_type}", use_container_width=True):
            st.session_state[sel_key] = set()
            st.rerun()

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    paginated, curr_page, total_pages = paginate_list(filtered, f"dp_{data_type}")

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    rows_data = [{
        "Sél.": lot["id_lot"] in st.session_state[sel_key],
        "Lot #": lot["id_lot"],
        "Centre": lot["nom_centre"],
        "Agent": lot["cree_par_nom"],
        "Période": f"{get_mois_name(lot['mois'])} {lot['annee']}",
        "Statut": STATUS_LABELS.get(lot["statut"], lot["statut"]),
        "Enreg.": lot["nb_enregistrements"],
        "Soumis le": format_datetime(lot.get("date_soumission")),
    } for lot in paginated]

    df_lots = pd.DataFrame(rows_data)
    edited_lots = st.data_editor(
        df_lots,
        use_container_width=True,
        hide_index=True,
        height=min(400, 40 + 35 * len(rows_data)),
        disabled=["Lot #", "Centre", "Agent", "Période", "Statut", "Enreg.", "Soumis le"],
        column_config={
            "Sél.": st.column_config.CheckboxColumn("Sél.", width="small"),
            "Lot #": st.column_config.NumberColumn("Lot #", width="small"),
        },
        key=f"editor_lots_{data_type}_p{curr_page}",
    )

    for i, row in edited_lots.iterrows():
        lot_id = paginated[i]["id_lot"]
        if row["Sél."]:
            st.session_state[sel_key].add(lot_id)
        else:
            st.session_state[sel_key].discard(lot_id)

    nb_sel = len(st.session_state[sel_key])

    if nb_sel > 0:
        st.markdown(render_notice(f"<strong>{nb_sel} lot(s) sélectionné(s)</strong>.", "success"), unsafe_allow_html=True)
        cmt_mass = st.text_area("Motif (obligatoire pour rejet)", key=f"cmt_mass_{data_type}", height=80)

        ac1, ac2, _ = st.columns([1.5, 1.5, 3])
        with ac1:
            st.markdown('<div class="btn-success">', unsafe_allow_html=True)
            if st.button(f"Valider les {nb_sel} lot(s)", key=f"vall_{data_type}", use_container_width=True):
                for lid in list(st.session_state[sel_key]):
                    details = get_lot_details_indicateurs(lid) if data_type == "indicateurs" else get_lot_details_reclamations(lid)
                    ids_pending = [d["id_donnee"] for d in details if d["statut"] not in ("valide_dp", "valide_regional", "rejete_dp", "rejete_regional")]
                    if ids_pending:
                        validate_donnees_batch(ids_pending, "valide", "dp", user["id"], None)
                    AuthManager.log_action(user["id"], f"VALIDATION_MASS_DP", "lot_saisie", lid)
                st.session_state[sel_key] = set()
                st.success(f"{nb_sel} lot(s) validé(s) et transmis au régional.")
                time.sleep(1)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with ac2:
            st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
            if st.button(f"Rejeter les {nb_sel} lot(s)", key=f"rall_{data_type}", use_container_width=True):
                if not cmt_mass.strip():
                    st.error("Motif obligatoire pour un rejet.")
                else:
                    for lid in list(st.session_state[sel_key]):
                        details = get_lot_details_indicateurs(lid) if data_type == "indicateurs" else get_lot_details_reclamations(lid)
                        ids_pending = [d["id_donnee"] for d in details if d["statut"] not in ("valide_dp", "valide_regional", "rejete_dp", "rejete_regional")]
                        if ids_pending:
                            validate_donnees_batch(ids_pending, "rejete", "dp", user["id"], cmt_mass)
                        AuthManager.log_action(user["id"], f"REJET_MASS_DP", "lot_saisie", lid, {"motif": cmt_mass})
                    st.session_state[sel_key] = set()
                    st.warning(f"{nb_sel} lot(s) rejeté(s), renvoyés aux agents.")
                    time.sleep(1)
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(render_section_close(), unsafe_allow_html=True)

    # ═══ INSPECTION LIGNE PAR LIGNE ═══
    st.markdown(render_section_open("Inspection ligne par ligne d'un lot", "EYE"), unsafe_allow_html=True)

    opts = {f"Lot #{l['id_lot']} — {l['nom_centre']} — {get_mois_name(l['mois'])} {l['annee']}": l for l in filtered}
    sel = st.selectbox("Choisir un lot à inspecter", ["— Sélectionner —"] + list(opts.keys()), key=f"insp_{data_type}")

    if sel == "— Sélectionner —":
        st.markdown(render_section_close(), unsafe_allow_html=True)
        return

    lot = opts[sel]
    id_lot = lot["id_lot"]
    details = get_lot_details_indicateurs(id_lot) if data_type == "indicateurs" else get_lot_details_reclamations(id_lot)

    st.markdown(f"**Statut du lot :** {get_status_badge(lot['statut'])}", unsafe_allow_html=True)

    st.markdown(render_lot_detail_card({
        "lot_id": lot["id_lot"], "agent": lot["cree_par_nom"], "centre": lot["nom_centre"],
        "mois": get_mois_name(lot['mois']), "annee": lot['annee'], "nb": lot["nb_enregistrements"],
        "date_soum": format_datetime(lot.get("date_soumission")),
    }), unsafe_allow_html=True)

    st.markdown("**Décidez pour chaque ligne (vous pouvez modifier la valeur avant de valider) :**")
    df = pd.DataFrame(details)

    cfg = {"ID": None}

    if data_type == "indicateurs":
        df_show = df[["id_donnee", "code_indicateur", "libelle_indicateur", "categorie", "unite", "valeur_indicateur", "statut"]].copy()
        df_show.columns = ["ID", "Code", "Indicateur", "Catégorie", "Unité", "Valeur", "Statut Actuel"]
        cfg["Valeur"] = st.column_config.NumberColumn("Valeur", min_value=0)
    else:
        df_show = pd.DataFrame()
        df_show["ID"] = df["id_donnee"]
        df_show["Code"] = df["code_type"]
        df_show["Type"] = df["libelle_reclamation"]
        df_show["Valeur"] = df.apply(_val_display_reclamation, axis=1).astype(str)
        df_show["Statut Actuel"] = df["statut"]
        cfg["Valeur"] = st.column_config.TextColumn("Valeur")

    df_show["Statut Actuel"] = df_show["Statut Actuel"].map(lambda x: STATUS_LABELS.get(x, x))

    def _initial_action(s):
        if "Validé" in s: return "— Figé (validé) —"
        if "Rejeté" in s: return "— Figé (rejeté) —"
        return "Valider"

    df_show["Action"] = df_show["Statut Actuel"].apply(_initial_action)
    cfg["Action"] = st.column_config.SelectboxColumn("Décision", options=["Valider", "Rejeter"], required=True)

    edited = st.data_editor(df_show, use_container_width=True, hide_index=True,
        height=min(500, 40 + 35 * len(df_show)),
        disabled=["ID", "Code", "Indicateur", "Type", "Catégorie", "Unité", "Statut Actuel"],
        column_config=cfg,
        key=f"ed_val_{id_lot}"
    )

    to_reject = edited[edited["Action"] == "Rejeter"]
    to_validate = edited[edited["Action"] == "Valider"]
    has_rej = len(to_reject) > 0

    val_changes = {}
    for i, row in edited.iterrows():
        orig = details[i]
        if orig["statut"] in ("valide_dp", "valide_regional", "rejete_dp", "rejete_regional"):
            continue

        if data_type == "indicateurs":
            old_val = float(orig.get("valeur_indicateur") or 0)
            new_val = float(row["Valeur"])
            if abs(old_val - new_val) > 0.001:
                val_changes[orig["id_donnee"]] = {"valeur_indicateur": new_val}
        else:
            if orig.get("code_type") == "AUTRES":
                old_cmt = (orig.get("commentaire_autre") or "").strip()
                new_cmt = str(row["Valeur"]).strip()
                if old_cmt != new_cmt:
                    val_changes[orig["id_donnee"]] = {"commentaire_autre": new_cmt or None}
            else:
                old_val = float(orig.get("valeur_brute") or 0)
                raw = str(row["Valeur"]).replace(",", ".").strip()
                new_val = float(raw) if raw else 0.0
                if abs(old_val - new_val) > 0.001:
                    val_changes[orig["id_donnee"]] = {"valeur_brute": new_val, "nombre_reclamations": int(new_val)}

    if val_changes:
        st.markdown(render_notice(f"<strong>{len(val_changes)} valeur(s) modifiée(s)</strong> par l'admin.", "info"), unsafe_allow_html=True)

    with st.form(f"f_act_{id_lot}"):
        motifs_par_ligne = {}

        if has_rej:
            st.markdown(render_notice(
                f"<strong>{len(to_reject)} ligne(s)</strong> vont être rejetées. Précisez le motif :", "warning"
            ), unsafe_allow_html=True)
            for idx, row in to_reject.iterrows():
                id_ligne = row["ID"]
                lbl = row.get("Indicateur", row.get("Type", "—"))
                motifs_par_ligne[id_ligne] = st.text_input(f"Motif pour « {lbl} » *", key=f"motif_{id_lot}_{id_ligne}")

        btn = st.form_submit_button("Appliquer les décisions", type="primary", use_container_width=True)

        if btn:
            missing_motifs = [mid for mid, m in motifs_par_ligne.items() if not m or not m.strip()]
            if has_rej and missing_motifs:
                st.error(f"Motif obligatoire pour {len(missing_motifs)} ligne(s).")
            else:
                figes = {d["id_donnee"] for d in details if d["statut"] in ("valide_dp", "valide_regional", "rejete_dp", "rejete_regional")}
                ids_v = [i for i in to_validate["ID"].tolist() if i not in figes]
                ids_r = [i for i in to_reject["ID"].tolist() if i not in figes]

                if not ids_v and not ids_r and not val_changes:
                    st.warning("Aucune nouvelle décision à appliquer.")
                else:
                    for id_donnee, updates in val_changes.items():
                        update_donnee_with_correction(id_donnee, updates, user["id"], None)

                    if ids_v: validate_donnees_batch(ids_v, "valide", "dp", user["id"], None)
                    for id_r in ids_r:
                        validate_donnees_batch([id_r], "rejete", "dp", user["id"], motifs_par_ligne.get(id_r, "Rejet sans motif"))

                    AuthManager.log_action(user["id"], f"VALIDATION_DP_{data_type.upper()}", "lot_saisie", id_lot, {"v": len(ids_v), "r": len(ids_r), "m": len(val_changes)})
                    st.success("Décisions appliquées avec succès.")
                    time.sleep(1)
                    st.rerun()

    render_historique_complet_lot(id_lot, key_prefix=f"val_dp_{data_type}")
    st.markdown(render_section_close(), unsafe_allow_html=True)


def _render_rejets_regional_ui(user, i_rej_reg, r_rej_reg):
    if not i_rej_reg and not r_rej_reg:
        st.markdown(render_empty("CHECK_CIRCLE", "Aucun rejet régional", "Aucun lot rejeté par l'admin régional en attente de traitement."), unsafe_allow_html=True)
        return

    st.markdown(render_notice("L'admin régional a rejeté ces lots. Corrigez-les vous-même ou transférez-les à l'agent.", "warning"), unsafe_allow_html=True)

    sub_i, sub_r = st.tabs([f"Indicateurs ({len(i_rej_reg)})", f"Réclamations ({len(r_rej_reg)})"])

    for lots, tab, dt in [(i_rej_reg, sub_i, "indicateurs"), (r_rej_reg, sub_r, "reclamations")]:
        with tab:
            if not lots:
                st.markdown(render_empty("CHECK_CIRCLE", "Aucun rejet régional"), unsafe_allow_html=True)
                continue

            for lot in lots:
                id_lot = lot["id_lot"]
                details = get_lot_details_indicateurs(id_lot) if dt == "indicateurs" else get_lot_details_reclamations(id_lot)
                rej_lines = [d for d in details if d["statut"] == "rejete_regional"]

                is_my_lot = (lot["cree_par"] == user["id"])
                origine_lbl = "votre saisie" if is_my_lot else f"saisie par {lot['cree_par_nom']}"

                with st.expander(f"Rejeté par Admin Régional — Lot #{id_lot} — {lot['nom_centre']} — {get_mois_name(lot['mois'])} {lot['annee']} — {len(rej_lines)} ligne(s) — [{origine_lbl}]", expanded=False):
                    st.markdown(f"**Statut :** {get_status_badge(lot['statut'])}", unsafe_allow_html=True)

                    if is_my_lot:
                        st.markdown("<div style='background:#F0F9FF;padding:0.75rem;margin:0.5rem 0;'>Ce lot a été saisi par <strong>vous-même</strong>. Vous devez le corriger.</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div style='background:#F0FDF4;padding:0.75rem;margin:0.5rem 0;'>Saisi par <strong>{lot['cree_par_nom']}</strong>. Corrigez ou transférez.</div>", unsafe_allow_html=True)

                    if not rej_lines:
                        st.info("Aucune ligne à traiter.")
                        continue

                    st.markdown("**Lignes rejetées par le régional :**")

                    df_rej = pd.DataFrame()
                    cfg = {"ID": None, "Motif régional": st.column_config.TextColumn("Motif régional", width="large")}

                    if dt == "indicateurs":
                        rows = [{"ID": d["id_donnee"], "Code": d["code_indicateur"], "Indicateur": d["libelle_indicateur"], "Motif régional": d.get("dernier_commentaire") or "Non spécifié", "Valeur": d["valeur_indicateur"]} for d in rej_lines]
                        cfg["Valeur"] = st.column_config.NumberColumn("Nouvelle Valeur", min_value=0)
                    else:
                        rows = [{"ID": d["id_donnee"], "Code": d["code_type"], "Réclamation": d["libelle_reclamation"], "Motif régional": d.get("dernier_commentaire") or "Non spécifié", "Valeur": _val_display_reclamation(d)} for d in rej_lines]
                        cfg["Valeur"] = st.column_config.TextColumn("Nouvelle Valeur")

                    df_rej = pd.DataFrame(rows)
                    if dt == "reclamations":
                        df_rej["Valeur"] = df_rej["Valeur"].astype(str)

                    edited = st.data_editor(
                        df_rej, use_container_width=True, hide_index=True,
                        disabled=[c for c in df_rej.columns if c != "Valeur"],
                        column_config=cfg,
                        key=f"rejreg_ed_{dt}_{id_lot}"
                    )

                    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
                    cmt_action = st.text_area("Commentaire" + (" (obligatoire pour transfert)" if not is_my_lot else " (optionnel)"), key=f"cmt_rej_reg_{dt}_{id_lot}", height=70)

                    bc1, bc2, _ = st.columns([2, 2, 2]) if not is_my_lot else (st.columns([2, 4])[0], None, None)

                    with bc1:
                        st.markdown('<div class="btn-success">', unsafe_allow_html=True)
                        if st.button("Corriger moi-même", key=f"corr_rej_reg_{dt}_{id_lot}", type="primary", use_container_width=True):
                            for i, row in edited.iterrows():
                                orig = rej_lines[i]
                                if dt == "indicateurs":
                                    updates = {"valeur_indicateur": float(row["Valeur"])}
                                else:
                                    if orig.get("code_type") == "AUTRES":
                                        updates = {"commentaire_autre": str(row["Valeur"]).strip() or None}
                                    else:
                                        raw = str(row["Valeur"]).replace(",", ".").strip()
                                        new_val = float(raw) if raw else 0.0
                                        updates = {"valeur_brute": new_val, "nombre_reclamations": int(new_val)}
                                update_donnee_with_correction(orig["id_donnee"], updates, user["id"], None)

                            resubmit_lot_after_rejection(id_lot, user["id"])
                            st.success("Corrections enregistrées et lot resoumis.")
                            time.sleep(1)
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

                    if not is_my_lot and bc2:
                        with bc2:
                            if st.button("Transférer à l'agent", key=f"trans_rej_reg_{dt}_{id_lot}", use_container_width=True):
                                if not cmt_action.strip():
                                    st.error("Commentaire obligatoire pour transférer à l'agent.")
                                else:
                                    transfert_lot_a_agent(id_lot, user["id"], cmt_action)
                                    st.success(f"Lot transféré à l'agent {lot['cree_par_nom']}.")
                                    time.sleep(1)
                                    st.rerun()

                    render_historique_complet_lot(id_lot, key_prefix=f"rejreg_{dt}")


def _render_demandes_modification_ui(user, i_demandes, r_demandes):
    """Onglet dédié aux demandes de modification venant de l'Admin Régional."""
    if not i_demandes and not r_demandes:
        st.markdown(render_empty("EDIT", "Aucune demande de modification",
                                  "Aucun lot en attente de modification post-validation régional."),
                    unsafe_allow_html=True)
        return

    st.markdown(render_notice(
        "L'Admin Régional a demandé la modification de ces lots (déjà validés définitivement). "
        "Vous pouvez soit <strong>corriger vous-même</strong>, soit <strong>déléguer à l'agent</strong> qui a saisi.",
        "warning"
    ), unsafe_allow_html=True)

    sub_i, sub_r = st.tabs([f"Indicateurs ({len(i_demandes)})", f"Réclamations ({len(r_demandes)})"])

    for lots, tab, dt in [(i_demandes, sub_i, "indicateurs"), (r_demandes, sub_r, "reclamations")]:
        with tab:
            if not lots:
                st.markdown(render_empty("CHECK_CIRCLE", "Aucune demande"), unsafe_allow_html=True)
                continue

            for lot in lots:
                id_lot = lot["id_lot"]
                details = get_lot_details_indicateurs(id_lot) if dt == "indicateurs" else get_lot_details_reclamations(id_lot)
                lignes_modif = [d for d in details if d["statut"] == "modif_admin_dp"]

                with st.expander(
                    f"Demande de {lot['demandeur_nom']} — Lot #{id_lot} — {lot['nom_centre']} — "
                    f"{get_mois_name(lot['mois'])} {lot['annee']} — {len(lignes_modif)} ligne(s)",
                    expanded=False
                ):
                    st.markdown(f"**Statut :** {get_status_badge(lot['statut'])}", unsafe_allow_html=True)

                    st.markdown(
                        f"<div style='background:#FEF3C7;border-left:4px solid #F59E0B;"
                        f"padding:1rem;border-radius:6px;margin:0.75rem 0;'>"
                        f"<div style='font-weight:700;color:#78350F;'>Message de {lot['demandeur_nom']} :</div>"
                        f"<div style='color:#78350F;font-style:italic;margin-top:0.35rem;'>« {lot['commentaire_demande']} »</div>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                    if not lignes_modif:
                        st.info("Aucune ligne à modifier.")
                        render_historique_complet_lot(id_lot, key_prefix=f"dem_{dt}")
                        continue

                    st.markdown("**Lignes à modifier :**")

                    cfg = {"ID": None}
                    if dt == "indicateurs":
                        rows = [{"ID": d["id_donnee"], "Code": d["code_indicateur"],
                                 "Indicateur": d["libelle_indicateur"], "Unité": d["unite"],
                                 "Valeur": d["valeur_indicateur"]} for d in lignes_modif]
                        cfg["Valeur"] = st.column_config.NumberColumn("Nouvelle Valeur", min_value=0)
                    else:
                        rows = [{"ID": d["id_donnee"], "Code": d["code_type"],
                                 "Type": d["libelle_reclamation"],
                                 "Valeur": _val_display_reclamation(d)}
                                 for d in lignes_modif]
                        cfg["Valeur"] = st.column_config.TextColumn("Nouvelle Valeur")

                    df_edit = pd.DataFrame(rows)
                    if dt == "reclamations":
                        df_edit["Valeur"] = df_edit["Valeur"].astype(str)

                    edited = st.data_editor(
                        df_edit, use_container_width=True, hide_index=True,
                        disabled=[c for c in df_edit.columns if c != "Valeur"],
                        column_config=cfg,
                        key=f"demdp_ed_{dt}_{id_lot}"
                    )

                    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
                    st.markdown("**Que voulez-vous faire ?**")

                    cmt_action = st.text_area(
                        "Commentaire (obligatoire pour transfert à l'agent)",
                        key=f"cmt_dem_{dt}_{id_lot}", height=70
                    )

                    bc1, bc2, _ = st.columns([2, 2, 2])

                    with bc1:
                        st.markdown('<div class="btn-success">', unsafe_allow_html=True)
                        if st.button("Corriger moi-même", key=f"corr_dem_{dt}_{id_lot}", type="primary", use_container_width=True):
                            for i, row in edited.iterrows():
                                orig = lignes_modif[i]
                                if dt == "indicateurs":
                                    updates = {"valeur_indicateur": float(row["Valeur"])}
                                else:
                                    if orig.get("code_type") == "AUTRES":
                                        updates = {"commentaire_autre": str(row["Valeur"]).strip() or None}
                                    else:
                                        raw = str(row["Valeur"]).replace(",", ".").strip()
                                        new_val = float(raw) if raw else 0.0
                                        updates = {"valeur_brute": new_val, "nombre_reclamations": int(new_val)}
                                update_donnee_with_correction(orig["id_donnee"], updates, user["id"], "Correction Admin DP suite à demande régionale")

                            resoumettre_apres_modif_admin_dp(id_lot, user["id"])
                            AuthManager.log_action(user["id"], "MODIF_APRES_DEM_REG", "lot_saisie", id_lot)
                            st.success("Modifications enregistrées et transmises pour re-validation régionale.")
                            time.sleep(1)
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

                    with bc2:
                        if st.button("Déléguer à l'Agent", key=f"trans_dem_{dt}_{id_lot}", use_container_width=True):
                            if not cmt_action.strip():
                                st.error("Commentaire obligatoire pour déléguer à l'agent.")
                            else:
                                demander_modification_lot(
                                    id_lot=id_lot,
                                    id_demandeur=user["id"],
                                    role_demandeur="admin_dp",
                                    id_destinataire=lot["cree_par"],
                                    role_destinataire="agent_dp",
                                    commentaire=cmt_action.strip(),
                                    only_ids=[l["id_donnee"] for l in lignes_modif]
                                )
                                marquer_demandes_traitees(id_lot, user["id"])
                                AuthManager.log_action(user["id"], "TRANSFERT_MODIF_AGENT", "lot_saisie", id_lot,
                                                       {"commentaire": cmt_action.strip()})
                                st.success(f"Demande transférée à l'agent {lot['cree_par_nom']}.")
                                time.sleep(1)
                                st.rerun()

                    render_historique_complet_lot(id_lot, key_prefix=f"dem_{dt}")


def _render_history_table(i_done, r_done):
    st.markdown(render_notice("Historique des lots que vous avez traités ou qui sont passés par votre validation."), unsafe_allow_html=True)
    tab_i, tab_r = st.tabs(["Indicateurs", "Réclamations"])
    for lots, tab, dt in [(i_done, tab_i, "indicateurs"), (r_done, tab_r, "reclamations")]:
        with tab:
            if not lots:
                st.markdown(render_empty("ARCHIVE", "Aucun historique"), unsafe_allow_html=True)
                continue

            paginated, curr_page, total_pages = paginate_list(lots, f"histdp_{dt}")

            rows = [{
                "Lot": f"#{l['id_lot']}", "Centre": l["nom_centre"],
                "Créé par": l.get("cree_par_nom", "—"),
                "Année": l["annee"], "Mois": get_mois_name(l["mois"]),
                "Statut": STATUS_LABELS.get(l["statut"], l["statut"]),
                "Enreg.": l["nb_enregistrements"],
                "Créé le": format_datetime(l["date_creation"])
            } for l in paginated]

            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=min(400, 40 + 35 * len(rows)))

            st.markdown("---")
            st.markdown(render_section_open("Voir les détails d'un lot traité", "EYE"), unsafe_allow_html=True)

            lot_opts = {f"Lot #{l['id_lot']} — {l['nom_centre']} — {get_mois_name(l['mois'])} {l['annee']}": l for l in lots}
            sel = st.selectbox("Choisir un lot à inspecter", ["— Sélectionner —"] + list(lot_opts.keys()), key=f"hist_dp_det_{dt}")

            if sel != "— Sélectionner —":
                lot = lot_opts[sel]
                id_lot = lot["id_lot"]

                # ✅ TÊTE DU LOT
                st.markdown(f"**Statut du lot :** {get_status_badge(lot['statut'])}", unsafe_allow_html=True)
                st.markdown(render_lot_detail_card({
                    "lot_id": lot["id_lot"], "agent": lot["cree_par_nom"], "centre": lot["nom_centre"],
                    "mois": get_mois_name(lot['mois']), "annee": lot['annee'],
                    "nb": lot["nb_enregistrements"], "date_soum": format_datetime(lot.get("date_soumission")),
                }), unsafe_allow_html=True)

                details = get_lot_details_indicateurs(id_lot) if dt == "indicateurs" else get_lot_details_reclamations(id_lot)

                if details:
                    st.markdown("#### Données du lot")
                    render_data_table_with_history(
                        details=details,
                        id_lot=id_lot,
                        data_type=dt,
                        key_prefix=f"hist_dp_{dt}"
                    )

            st.markdown(render_section_close(), unsafe_allow_html=True)