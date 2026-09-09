# views/page_validation_regionale.py
"""Validation Régionale - Admin régional valide définitivement ou rejette."""

import streamlit as st
import pandas as pd
import time

from auth.session_manager import SessionManager
from auth.authentication import AuthManager
from db.queries import (
    get_staging_lots, get_lot_details_indicateurs, get_lot_details_reclamations,
    validate_donnees_batch, get_provinces, update_donnee_with_correction,
    set_lot_commentaire_global,
    modifier_et_valider_regional, demander_modification_lot,
    get_admin_dp_de_province,
)
from utils.helpers import format_datetime, get_mois_name, MOIS_FR
from utils.styles import (
    render_page_header, render_notice, render_empty, render_section_open, render_section_close,
    render_metric, render_lot_detail_card, render_prov_card, STATUS_LABELS, get_status_badge
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


def render_validation_regionale():
    SessionManager.require_role(["admin_regional", "super_admin"])
    user = SessionManager.get_user()

    st.markdown(render_page_header("Validation régionale", "Siège Agadir — Données validées par les admins DP"), unsafe_allow_html=True)

    all_i_raw = get_staging_lots(type_donnees="indicateurs") or []
    all_r_raw = get_staging_lots(type_donnees="reclamations") or []

    rejets_i = len([l for l in all_i_raw if l["statut"] in ["partiellement_rejete_regional", "rejete_regional"]])
    rejets_r = len([l for l in all_r_raw if l["statut"] in ["partiellement_rejete_regional", "rejete_regional"]])
    total_rejets_reg = rejets_i + rejets_r

    allowed = ["valide_dp", "en_cours_validation_regional", "valide_regional"]
    all_i = [l for l in all_i_raw if l["statut"] in allowed]
    all_r = [l for l in all_r_raw if l["statut"] in allowed]

    pending_st = ["valide_dp", "en_cours_validation_regional"]
    i_pending = [l for l in all_i if l["statut"] in pending_st]
    r_pending = [l for l in all_r if l["statut"] in pending_st]

    i_valides = [l for l in all_i if l["statut"] == "valide_regional"]
    r_valides = [l for l in all_r if l["statut"] == "valide_regional"]

    c1, c2, c3, c4 = st.columns(4, gap="small")
    with c1: st.markdown(render_metric("Indic. à valider", len(i_pending), "CLOCK"), unsafe_allow_html=True)
    with c2: st.markdown(render_metric("Réc. à valider", len(r_pending), "CLOCK"), unsafe_allow_html=True)
    with c3: st.markdown(render_metric("Validés définitivement", len(i_valides) + len(r_valides), "CHECK_CIRCLE"), unsafe_allow_html=True)
    with c4: st.markdown(render_metric("Rejets Régional", total_rejets_reg, "X"), unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    st.markdown(render_section_open("Vue d'ensemble par province", "MAP_PIN"), unsafe_allow_html=True)
    provs = get_provinces() or []
    cols = st.columns(3, gap="small")
    for idx, p in enumerate(provs):
        pid = p["id_province"]
        prov_i = [l for l in all_i if l["id_province"] == pid]
        prov_r = [l for l in all_r if l["id_province"] == pid]
        pend = len([l for l in prov_i + prov_r if l["statut"] in pending_st])
        val = len([l for l in prov_i + prov_r if l["statut"] == "valide_regional"])
        tot = len(prov_i) + len(prov_r)
        with cols[idx % 3]:
            st.markdown(render_prov_card(p["nom_province"], tot, pend, val, 0), unsafe_allow_html=True)
    st.markdown(render_section_close(), unsafe_allow_html=True)

    tab_queue, tab_valides = st.tabs([
        f"File d'attente ({len(i_pending) + len(r_pending)})",
        f"Validés définitivement ({len(i_valides) + len(r_valides)})"
    ])

    with tab_queue:
        sub_i, sub_r = st.tabs([f"Indicateurs ({len(i_pending)})", f"Réclamations ({len(r_pending)})"])
        with sub_i: _render_reg_ui("indicateurs", user, i_pending, provs)
        with sub_r: _render_reg_ui("reclamations", user, r_pending, provs)

    with tab_valides:
        _render_valides_history(i_valides, r_valides, provs)


def _render_reg_ui(data_type, user, lots, provs):
    if not lots:
        st.markdown(render_empty("CHECK_CIRCLE", "File d'attente vide"), unsafe_allow_html=True)
        return

    st.markdown(render_section_open("Filtres", "FILTER"), unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    with f1:
        opts_p = [("Toutes", "Toutes les provinces")] + [(p["id_province"], p["nom_province"]) for p in provs]
        f_prov = st.selectbox("Province", opts_p, format_func=lambda x: x[1], key=f"fp_{data_type}")
    with f2:
        annees = sorted(set(l["annee"] for l in lots), reverse=True)
        f_annee = st.selectbox("Année", ["Toutes"] + annees, key=f"fa_{data_type}")
    with f3:
        mois_d = sorted(set(l["mois"] for l in lots))
        f_mois = st.selectbox("Mois", ["Tous"] + mois_d, format_func=lambda x: "Tous" if x == "Tous" else MOIS_FR[x], key=f"fm_{data_type}")
    st.markdown(render_section_close(), unsafe_allow_html=True)

    pid = f_prov[0] if f_prov[0] != "Toutes" else None
    filtered = [l for l in lots if (pid is None or l["id_province"] == pid) and (f_annee == "Toutes" or l["annee"] == f_annee) and (f_mois == "Tous" or l["mois"] == f_mois)]

    if not filtered:
        st.markdown(render_empty("FILTER", "Aucun lot"), unsafe_allow_html=True)
        return

    st.markdown(render_section_open("Sélection multiple (validation en masse)", "LAYERS"), unsafe_allow_html=True)

    sel_key = f"sel_reg_{data_type}"
    if sel_key not in st.session_state: st.session_state[sel_key] = set()

    tc1, tc2, _ = st.columns([1.2, 1.2, 4])
    with tc1:
        if st.button("Tout sélectionner", key=f"selall_r_{data_type}", use_container_width=True):
            st.session_state[sel_key] = set(l["id_lot"] for l in filtered)
            st.rerun()
    with tc2:
        if st.button("Tout désélectionner", key=f"unsel_r_{data_type}", use_container_width=True):
            st.session_state[sel_key] = set()
            st.rerun()

    paginated, curr_page, total_pages = paginate_list(filtered, f"reg_{data_type}")

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    rows_data = [{
        "Sél.": lot["id_lot"] in st.session_state[sel_key],
        "Lot #": lot["id_lot"], "Province": lot["nom_province"], "Centre": lot["nom_centre"],
        "Agent": lot["cree_par_nom"], "Période": f"{get_mois_name(lot['mois'])} {lot['annee']}",
        "Statut": STATUS_LABELS.get(lot["statut"], lot["statut"]), "Enreg.": lot["nb_enregistrements"],
    } for lot in paginated]

    edited_lots = st.data_editor(
        pd.DataFrame(rows_data), use_container_width=True, hide_index=True,
        height=min(400, 40 + 35 * len(rows_data)),
        disabled=["Lot #", "Province", "Centre", "Agent", "Période", "Statut", "Enreg."],
        column_config={"Sél.": st.column_config.CheckboxColumn("Sél.", width="small"), "Lot #": st.column_config.NumberColumn("Lot #", width="small")},
        key=f"editor_lots_r_{data_type}_p{curr_page}",
    )

    for i, row in edited_lots.iterrows():
        lot_id = paginated[i]["id_lot"]
        if row["Sél."]: st.session_state[sel_key].add(lot_id)
        else: st.session_state[sel_key].discard(lot_id)

    nb_sel = len(st.session_state[sel_key])

    if nb_sel > 0:
        cmt_mass = st.text_area("Commentaire (obligatoire pour rejet)", key=f"cmt_mass_r_{data_type}", height=80)
        ac1, ac2, _ = st.columns([1.5, 1.5, 3])
        with ac1:
            st.markdown('<div class="btn-success">', unsafe_allow_html=True)
            if st.button(f"Valider les {nb_sel} lot(s)", key=f"vall_r_{data_type}", use_container_width=True):
                for lid in list(st.session_state[sel_key]):
                    details = get_lot_details_indicateurs(lid) if data_type == "indicateurs" else get_lot_details_reclamations(lid)
                    ids_pending = [d["id_donnee"] for d in details if d["statut"] not in ("valide_regional", "rejete_regional")]
                    if ids_pending: validate_donnees_batch(ids_pending, "valide", "regional", user["id"], cmt_mass if cmt_mass.strip() else None)
                    if cmt_mass.strip(): set_lot_commentaire_global(lid, cmt_mass, "regional", user["id"])
                    AuthManager.log_action(user["id"], "VALIDATION_MASS_REG", "lot_saisie", lid)
                st.session_state[sel_key] = set()
                st.success(f"{nb_sel} lot(s) validé(s).")
                time.sleep(1)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with ac2:
            st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
            if st.button(f"Rejeter les {nb_sel} lot(s)", key=f"rall_r_{data_type}", use_container_width=True):
                if not cmt_mass.strip(): st.error("Commentaire obligatoire.")
                else:
                    for lid in list(st.session_state[sel_key]):
                        details = get_lot_details_indicateurs(lid) if data_type == "indicateurs" else get_lot_details_reclamations(lid)
                        ids_pending = [d["id_donnee"] for d in details if d["statut"] not in ("valide_regional", "rejete_regional")]
                        if ids_pending: validate_donnees_batch(ids_pending, "rejete", "regional", user["id"], cmt_mass)
                        set_lot_commentaire_global(lid, cmt_mass, "regional", user["id"])
                        AuthManager.log_action(user["id"], "REJET_MASS_REG", "lot_saisie", lid, {"motif": cmt_mass})
                    st.session_state[sel_key] = set()
                    st.warning(f"{nb_sel} lot(s) rejeté(s).")
                    time.sleep(1)
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(render_section_close(), unsafe_allow_html=True)

    # ═══ INSPECTION DÉTAILLÉE ═══
    st.markdown(render_section_open("Inspection ligne par ligne", "EYE"), unsafe_allow_html=True)
    opts = {f"[{l['nom_province']}] Lot #{l['id_lot']} — {l['nom_centre']} — {get_mois_name(l['mois'])} {l['annee']}": l for l in filtered}
    sel = st.selectbox("Choisir un lot", ["— Sélectionner —"] + list(opts.keys()), key=f"sel_r_{data_type}")

    if sel == "— Sélectionner —":
        st.markdown(render_section_close(), unsafe_allow_html=True)
        return

    lot = opts[sel]
    id_lot = lot["id_lot"]
    details = get_lot_details_indicateurs(id_lot) if data_type == "indicateurs" else get_lot_details_reclamations(id_lot)

    # ✅ TÊTE DU LOT
    st.markdown(f"**Statut du lot :** {get_status_badge(lot['statut'])}", unsafe_allow_html=True)
    st.markdown(render_lot_detail_card({
        "lot_id": lot["id_lot"], "agent": lot["cree_par_nom"], "centre": lot["nom_centre"],
        "mois": get_mois_name(lot['mois']), "annee": lot['annee'], "nb": lot["nb_enregistrements"],
        "date_soum": format_datetime(lot.get("date_soumission")),
    }, extra_info={"Province": lot["nom_province"]}), unsafe_allow_html=True)

    st.markdown("**Décidez pour chaque ligne (vous pouvez modifier la valeur) :**")
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
        if s == "Validé Régional": return "— Figé (validé) —"
        if "Rejeté Régional" in s: return "— Figé (rejeté) —"
        return "Valider définitivement"

    df_show["Action"] = df_show["Statut Actuel"].apply(_initial_action)
    cfg["Action"] = st.column_config.SelectboxColumn("Décision", options=["Valider définitivement", "Rejeter au DP"], required=True)

    edited = st.data_editor(df_show, use_container_width=True, hide_index=True, height=min(500, 40 + 35 * len(df_show)), disabled=["ID", "Code", "Indicateur", "Type", "Catégorie", "Unité", "Statut Actuel"], column_config=cfg, key=f"ed_valr_{id_lot}")

    to_reject = edited[edited["Action"] == "Rejeter au DP"]
    to_validate = edited[edited["Action"] == "Valider définitivement"]
    has_rej = len(to_reject) > 0

    val_changes = {}
    for i, row in edited.iterrows():
        orig = details[i]
        if orig["statut"] in ("valide_regional", "rejete_regional"): continue
        if data_type == "indicateurs":
            old_val = float(orig.get("valeur_indicateur") or 0)
            new_val = float(row["Valeur"])
            if abs(old_val - new_val) > 0.001: val_changes[orig["id_donnee"]] = {"valeur_indicateur": new_val}
        else:
            if orig.get("code_type") == "AUTRES":
                old_cmt = (orig.get("commentaire_autre") or "").strip()
                new_cmt = str(row["Valeur"]).strip()
                if old_cmt != new_cmt: val_changes[orig["id_donnee"]] = {"commentaire_autre": new_cmt or None}
            else:
                old_val = float(orig.get("valeur_brute") or 0)
                raw = str(row["Valeur"]).replace(",", ".").strip()
                new_val = float(raw) if raw else 0.0
                if abs(old_val - new_val) > 0.001: val_changes[orig["id_donnee"]] = {"valeur_brute": new_val, "nombre_reclamations": int(new_val)}

    with st.form(f"f_act_r_{id_lot}"):
        motifs_par_ligne = {}
        if has_rej:
            st.markdown(render_notice(f"<strong>{len(to_reject)} ligne(s)</strong> seront renvoyées au DP. Précisez le motif :", "warning"), unsafe_allow_html=True)
            for idx, row in to_reject.iterrows():
                id_ligne = row["ID"]
                lbl = row.get("Indicateur", row.get("Type", "—"))
                motifs_par_ligne[id_ligne] = st.text_input(f"Motif pour « {lbl} » *", key=f"motif_r_{id_lot}_{id_ligne}")

        cmt_global = st.text_area("Commentaire général sur ce lot (optionnel)", key=f"cmt_glob_r_{id_lot}", height=60)
        btn = st.form_submit_button("Appliquer les décisions", type="primary", use_container_width=True)

        if btn:
            missing_motifs = [mid for mid, m in motifs_par_ligne.items() if not m or not m.strip()]
            if has_rej and missing_motifs: st.error(f"Motif obligatoire pour {len(missing_motifs)} ligne(s).")
            else:
                figes = {d["id_donnee"] for d in details if d["statut"] in ("valide_regional", "rejete_regional")}
                ids_v = [i for i in to_validate["ID"].tolist() if i not in figes]
                ids_r = [i for i in to_reject["ID"].tolist() if i not in figes]

                if not ids_v and not ids_r and not val_changes: st.warning("Aucune nouvelle décision.")
                else:
                    for id_donnee, updates in val_changes.items(): update_donnee_with_correction(id_donnee, updates, user["id"], "Modification admin régional")
                    if ids_v: validate_donnees_batch(ids_v, "valide", "regional", user["id"], None)
                    for id_r in ids_r: validate_donnees_batch([id_r], "rejete", "regional", user["id"], motifs_par_ligne.get(id_r, "Rejet sans motif"))
                    if cmt_global.strip(): set_lot_commentaire_global(id_lot, cmt_global.strip(), "regional", user["id"])

                    st.success("Décisions appliquées.")
                    time.sleep(1)
                    st.rerun()

    render_historique_complet_lot(id_lot, key_prefix=f"val_reg_{data_type}")
    st.markdown(render_section_close(), unsafe_allow_html=True)


def _render_valides_history(i_valides, r_valides, provs):
    st.markdown(render_notice("Données validées définitivement, prêtes pour le pipeline ETL.", "success"), unsafe_allow_html=True)
    tab_i, tab_r = st.tabs([f"Indicateurs ({len(i_valides)})", f"Réclamations ({len(r_valides)})"])
    for lots, tab, dt in [(i_valides, tab_i, "indicateurs"), (r_valides, tab_r, "reclamations")]:
        with tab:
            if not lots:
                st.markdown(render_empty("CHECK_CIRCLE", "Aucune donnée validée"), unsafe_allow_html=True)
                continue

            f1, f2, f3, f4 = st.columns(4)
            with f1:
                opts_p = ["Toutes"] + [(p["id_province"], p["nom_province"]) for p in provs]
                f_prov = st.selectbox("Province", opts_p, format_func=lambda x: "Toutes les provinces" if x == "Toutes" else x[1], key=f"vh_prov_{dt}")
            with f2:
                annees_dispo = sorted(set(l["annee"] for l in lots), reverse=True)
                f_annee = st.selectbox("Année", ["Toutes"] + annees_dispo, key=f"vh_annee_{dt}")
            with f3:
                mois_dispo = sorted(set(l["mois"] for l in lots))
                f_mois = st.selectbox("Mois", ["Tous"] + mois_dispo, format_func=lambda x: "Tous les mois" if x == "Tous" else MOIS_FR[x], key=f"vh_mois_{dt}")
            with f4:
                if f_prov != "Toutes": centres_dispo = sorted(set(l["nom_centre"] for l in lots if l["id_province"] == f_prov[0]))
                else: centres_dispo = sorted(set(l["nom_centre"] for l in lots))
                f_centre = st.selectbox("Centre", ["Tous"] + centres_dispo, key=f"vh_centre_{dt}")

            filtered = [l for l in lots if (f_prov == "Toutes" or l["id_province"] == f_prov[0]) and (f_annee == "Toutes" or l["annee"] == f_annee) and (f_mois == "Tous" or l["mois"] == f_mois) and (f_centre == "Tous" or l["nom_centre"] == f_centre)]

            if not filtered:
                st.markdown(render_empty("FILTER", "Aucun lot avec ces filtres"), unsafe_allow_html=True)
                continue

            paginated, curr_page, total_pages = paginate_list(filtered, f"vh_{dt}")

            rows = [{"Lot": f"#{l['id_lot']}", "Province": l["nom_province"], "Centre": l["nom_centre"], "Période": f"{get_mois_name(l['mois'])} {l['annee']}", "Statut": STATUS_LABELS.get(l["statut"], l["statut"]), "Enreg.": l["nb_enregistrements"]} for l in paginated]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=min(400, 40 + 35 * len(rows)))

            st.markdown("---")
            st.markdown(render_section_open("Voir les détails d'un lot validé", "EYE"), unsafe_allow_html=True)
            lot_opts = {f"[{l['nom_province']}] Lot #{l['id_lot']} — {l['nom_centre']} — {get_mois_name(l['mois'])} {l['annee']}": l for l in filtered}
            sel = st.selectbox("Choisir un lot à inspecter", ["— Sélectionner —"] + list(lot_opts.keys()), key=f"vh_det_{dt}")

            if sel != "— Sélectionner —":
                lot = lot_opts[sel]
                id_lot = lot["id_lot"]

                # ✅ TÊTE DU LOT
                st.markdown(f"**Statut du lot :** {get_status_badge(lot['statut'])}", unsafe_allow_html=True)
                st.markdown(render_lot_detail_card({
                    "lot_id": lot["id_lot"], "agent": lot["cree_par_nom"], "centre": lot["nom_centre"],
                    "mois": get_mois_name(lot['mois']), "annee": lot['annee'],
                    "nb": lot["nb_enregistrements"], "date_soum": format_datetime(lot.get("date_soumission")),
                }, extra_info={"Province": lot["nom_province"]}), unsafe_allow_html=True)

                details = get_lot_details_indicateurs(id_lot) if dt == "indicateurs" else get_lot_details_reclamations(id_lot)

                if details:
                    st.markdown("#### Données du lot")
                    edited = render_data_table_with_history(
                        details=details,
                        id_lot=id_lot,
                        data_type=dt,
                        key_prefix=f"vh_edit_{dt}",
                        editable_col="Valeur"
                    )

                    # Détecter les modifications
                    val_changes = {}
                    if edited is not None:
                        for i, row in edited.iterrows():
                            orig = details[i]
                            if dt == "indicateurs":
                                old_val = float(orig.get("valeur_indicateur") or 0)
                                try:
                                    new_val = float(row["Valeur"])
                                except (ValueError, TypeError):
                                    continue
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
                                    try:
                                        new_val = float(raw) if raw else 0.0
                                    except (ValueError, TypeError):
                                        continue
                                    if abs(old_val - new_val) > 0.001:
                                        val_changes[orig["id_donnee"]] = {"valeur_brute": new_val, "nombre_reclamations": int(new_val)}

                    # ═══ ACTIONS ═══
                    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
                    st.markdown(render_section_open("Actions (optionnel)", "EDIT"), unsafe_allow_html=True)
                    st.markdown(render_notice(
                        "Par défaut : <strong>consultation uniquement</strong> (rien n'est sélectionné). "
                        "Choisissez <strong>une seule</strong> action ci-dessous.",
                        "info"
                    ), unsafe_allow_html=True)

                    mode = st.radio(
                        "Choisir une action",
                        options=["Corriger moi-même", "Déléguer à l'Admin DP"],
                        index=None,
                        horizontal=True,
                        key=f"vh_action_mode_{dt}_{id_lot}",
                        label_visibility="collapsed",
                    )

                    if mode == "Corriger moi-même":
                        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
                        st.markdown("##### Corriger moi-même")
                        st.caption("Modifiez les valeurs dans le tableau puis re-validez définitivement.")
                        if val_changes:
                            st.info(f"{len(val_changes)} modification(s) détectée(s).")
                        else:
                            st.caption("Modifiez d'abord une ou plusieurs valeurs ci-dessus.")

                        if st.button(
                            "Enregistrer et re-valider définitivement",
                            key=f"vh_save_{dt}_{id_lot}",
                            type="primary",
                            use_container_width=True,
                            disabled=(len(val_changes) == 0),
                        ):
                            uid = SessionManager.get_user()["id"]
                            for id_donnee, updates in val_changes.items():
                                modifier_et_valider_regional(id_donnee, updates, uid)
                            AuthManager.log_action(
                                uid, "MODIF_POST_VALIDATION_REG",
                                "lot_saisie", id_lot,
                                {"nb_changes": len(val_changes)},
                            )
                            st.success(f"{len(val_changes)} modification(s) enregistrée(s) et re-validée(s).")
                            time.sleep(1)
                            st.rerun()

                    elif mode == "Déléguer à l'Admin DP":
                        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
                        st.markdown("##### Déléguer à l'Admin DP")
                        st.caption("Envoie le lot à l'Admin DP pour correction.")
                        admin_dp = get_admin_dp_de_province(lot["id_province"])
                        if not admin_dp:
                            st.error(f"Aucun Admin DP actif pour {lot.get('nom_province', 'cette province')}.")
                        else:
                            st.info(f"Destinataire : **{admin_dp['nom_complet']}**")
                            cmt_delegate = st.text_area(
                                "Commentaire de délégation (obligatoire)",
                                placeholder="Ex: Vérifier le rendement...",
                                key=f"vh_delegcmt_{dt}_{id_lot}",
                                height=80,
                            )
                            if st.button(
                                "Envoyer la demande à l'Admin DP",
                                key=f"vh_deleg_{dt}_{id_lot}",
                                use_container_width=True,
                            ):
                                if not cmt_delegate.strip():
                                    st.error("Commentaire obligatoire.")
                                else:
                                    demander_modification_lot(
                                        id_lot=id_lot,
                                        id_demandeur=SessionManager.get_user()["id"],
                                        role_demandeur="admin_regional",
                                        id_destinataire=admin_dp["id_utilisateur"],
                                        role_destinataire="admin_dp",
                                        commentaire=cmt_delegate.strip(),
                                    )
                                    AuthManager.log_action(
                                        SessionManager.get_user()["id"],
                                        "DELEG_MODIF_ADMIN_DP",
                                        "lot_saisie",
                                        id_lot,
                                        {"commentaire": cmt_delegate.strip()},
                                    )
                                    st.success(f"Demande envoyée à {admin_dp['nom_complet']}.")
                                    time.sleep(1)
                                    st.rerun()

                    st.markdown(render_section_close(), unsafe_allow_html=True)

            st.markdown(render_section_close(), unsafe_allow_html=True)