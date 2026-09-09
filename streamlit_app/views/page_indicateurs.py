# views/page_indicateurs.py
"""Saisie et gestion des indicateurs DP."""

import streamlit as st
import pandas as pd
import time
from datetime import datetime

from auth.session_manager import SessionManager
from auth.authentication import AuthManager
from db.queries import (
    get_types_indicateur, insert_indicateurs_batch, get_staging_lots,
    get_lot_details_indicateurs, get_lot_details_reclamations, submit_lot,
    delete_draft_lot, update_donnee_with_correction, get_lot_corrections_history,
    get_centres, get_lots_transferes_pour_agent, marquer_transfert_traite,
    resubmit_lot_after_rejection, 
    get_demandes_pour_user, resoumettre_apres_modif_agent,
)
from config.provinces import get_province_name
from utils.helpers import get_current_period, MOIS_FR, get_mois_name, format_datetime
from utils.styles import (
    render_page_header, render_notice, render_empty, render_section_open, render_section_close,
    render_form_category, render_lot_detail_card, STATUS_LABELS, get_status_badge
)
from utils.history_display import render_historique_complet_lot, render_data_table_with_history
from utils.pagination import paginate_list

STATIC_CATEGORIES = ["Infrastructure"]


def _clear_indicateur_form_keys():
    """Vide les champs du formulaire d'indicateurs."""
    keys_to_delete = []
    for k in list(st.session_state.keys()):
        if k.startswith("val_"):
            keys_to_delete.append(k)
    for k in keys_to_delete:
        try:
            del st.session_state[k]
        except KeyError:
            pass


def render_indicateurs():
    SessionManager.require_role(["agent_dp", "admin_dp", "super_admin"])
    user = SessionManager.get_user()
    id_province = user["id_province"]
    province_name = user["nom_province"] or get_province_name(id_province)
    role = user["role"]
    is_admin = role in ("admin_dp", "super_admin")

    st.markdown(render_page_header("Indicateurs de performance DP", f"Province de {province_name}"), unsafe_allow_html=True)

    if is_admin:
        st.markdown(render_notice(
            "En tant qu'admin DP, vos saisies sont <strong>auto-validées</strong> et transmises directement au régional. "
            "Consultez la page <strong>Validation DP</strong> pour gérer les rejets et demandes de modification.",
            "info"
        ), unsafe_allow_html=True)

    drafts = get_staging_lots(
        id_province=id_province, statut="brouillon",
        type_donnees="indicateurs", user_id=user["id"]
    ) or []

    # ─── Lots rejetés & demandes uniquement pour l'AGENT DP ───
    if role == "agent_dp":
        rej_dp = get_staging_lots(
            id_province=id_province, statut="partiellement_rejete_dp",
            type_donnees="indicateurs"
        ) or []
        rej_dp = [l for l in rej_dp if l["cree_par"] == user["id"]]
        rej_transferes = get_lots_transferes_pour_agent(id_province, user["id"], "indicateurs") or []
        rejected = rej_dp + rej_transferes

        demandes_modif = get_demandes_pour_user(user["id"], "indicateurs") or []
    else:
        rejected = []
        demandes_modif = []

    if rejected:
        st.markdown(render_notice(
            f"Vos lot(s) avec des données rejetées : <strong>{len(rejected)}</strong>. "
            f"Consultez l'onglet « Lots rejetés » pour corriger.",
            "warning"
        ), unsafe_allow_html=True)

    if drafts:
        st.markdown(render_notice(
            f"Vous avez <strong>{len(drafts)}</strong> brouillon(s) non soumis.",
            "info"
        ), unsafe_allow_html=True)

    # ─── Onglets adaptés selon le rôle ───
    if is_admin:
        tab_new, tab_drafts, tab_hist = st.tabs([
            "Nouvelle saisie",
            f"Brouillons ({len(drafts)})",
            "Historique"
        ])

        with tab_new:
            _render_new_entry(user, id_province)
        with tab_drafts:
            render_draft_lots("indicateurs", user, drafts)
        with tab_hist:
            _render_history("indicateurs", id_province)
    else:
        tab_new, tab_drafts, tab_rejected, tab_modif, tab_hist = st.tabs([
            "Nouvelle saisie",
            f"Brouillons ({len(drafts)})",
            f"Lots rejetés ({len(rejected)})",
            f"Modifications demandées ({len(demandes_modif)})",
            "Historique"
        ])

        with tab_new:
            _render_new_entry(user, id_province)
        with tab_drafts:
            render_draft_lots("indicateurs", user, drafts)
        with tab_rejected:
            render_rejected_lots("indicateurs", user, rejected, role)
        with tab_modif:
            render_modifications_agent("indicateurs", user, demandes_modif)
        with tab_hist:
            _render_history("indicateurs", id_province)

            
def _render_new_entry(user, id_province):
    role = user["role"]
    is_admin = role in ("admin_dp", "super_admin")

    st.markdown(render_notice(
        "Sélectionnez la période et le centre, puis saisissez les valeurs. "
        + ("Vos saisies seront <strong>auto-validées</strong> lors de la soumission."
           if is_admin else
           "Enregistrez en brouillon ou soumettez directement pour validation par votre admin DP.")
    ), unsafe_allow_html=True)

    st.markdown(render_section_open("Période et centre", "CALENDAR"), unsafe_allow_html=True)

    cy, cm = get_current_period()
    c1, c2, c3 = st.columns(3)
    with c1:
        annee = st.selectbox("Année", list(range(cy, cy - 3, -1)), key="i_a")
    with c2:
        mois = st.selectbox("Mois", list(range(1, 13)), format_func=lambda x: MOIS_FR[x], index=max(0, cm - 2), key="i_m")
    with c3:
        centres = get_centres(id_province)
        cmap = {c["nom_centre"]: c for c in centres}
        cn = st.selectbox("Centre", list(cmap.keys()), key="i_c")
        centre = cmap[cn]
    st.markdown(render_section_close(), unsafe_allow_html=True)

    types = get_types_indicateur()
    if not types:
        st.warning("Aucun type d'indicateur configuré.")
        return

    cats_m, cats_s = {}, {}
    for t in types:
        cat = t["categorie"] or "Autres"
        if cat in STATIC_CATEGORIES:
            cats_s.setdefault(cat, []).append(t)
        else:
            cats_m.setdefault(cat, []).append(t)

    st.markdown(render_section_open("Indicateurs mensuels", "EDIT"), unsafe_allow_html=True)
    
    with st.form("form_ind", clear_on_submit=True):
        records = []

        for cat_name, indics in cats_m.items():
            st.markdown(render_form_category("FOLDER", cat_name), unsafe_allow_html=True)
            hc1, hc2 = st.columns([6, 3])
            with hc1:
                st.markdown("<div style='font-weight:600;font-size:0.8rem;color:#6B7280;'>INDICATEUR</div>", unsafe_allow_html=True)
            with hc2:
                st.markdown("<div style='font-weight:600;font-size:0.8rem;color:#6B7280;'>VALEUR</div>", unsafe_allow_html=True)

            for ind in indics:
                cl, cv = st.columns([6, 3])
                with cl:
                    st.markdown(f"<div style='padding-top:0.5rem;'><strong>{ind['libelle_indicateur']}</strong> <span style='color:#6B7280;font-size:0.78rem;'>({ind['unite']})</span></div>", unsafe_allow_html=True)
                with cv:
                    is_int = ind["unite"] in ["U", "An", ""]
                    val = st.number_input(f"V {ind['code_indicateur']}", min_value=0 if is_int else 0.0, value=0 if is_int else 0.0, step=1 if is_int else 0.01, format=None if is_int else "%.2f", key=f"val_{ind['code_indicateur']}", label_visibility="collapsed")
                if val > 0:
                    records.append({"id_type_indicateur": ind["id_type_indicateur"], "valeur": float(val)})

        if cats_s:
            st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
            st.markdown("<div style='background:#FEF3C7;border-left:4px solid #F59E0B;padding:0.85rem;border-radius:6px;margin:1rem 0;'><div style='font-weight:700;color:#78350F;'>Indicateurs statiques (Infrastructure)</div><div style='font-size:0.8rem;color:#78350F;'>Saisissez-les uniquement lors d'un changement réel. Laissez à 0 si aucun changement.</div></div>", unsafe_allow_html=True)
            for cat_name, indics in cats_s.items():
                st.markdown(render_form_category("FOLDER", cat_name), unsafe_allow_html=True)
                for ind in indics:
                    cl, cv = st.columns([6, 3])
                    with cl:
                        st.markdown(f"<div style='padding-top:0.5rem;'><strong>{ind['libelle_indicateur']}</strong> ({ind['unite']})</div>", unsafe_allow_html=True)
                    with cv:
                        val = st.number_input(f"V {ind['code_indicateur']}", min_value=0.0, value=0.0, key=f"val_{ind['code_indicateur']}", label_visibility="collapsed")
                    if val > 0:
                        records.append({"id_type_indicateur": ind["id_type_indicateur"], "valeur": float(val)})

        st.markdown("---")
        b1, b2 = st.columns(2)
        with b1:
            draft = st.form_submit_button("Enregistrer brouillon", use_container_width=True)
        with b2:
            btn_lbl = "Soumettre et auto-valider" if is_admin else "Soumettre pour validation"
            submit = st.form_submit_button(btn_lbl, use_container_width=True, type="primary")

        if draft or submit:
            if not records:
                st.error("Saisissez au moins une valeur non nulle.")
            else:
                is_sub = bool(submit)
                id_lot = insert_indicateurs_batch(centre["id_centre"], annee, mois, records, user["id"], is_sub)
                AuthManager.log_action(user["id"], "SOUMISSION_INDICATEURS" if is_sub else "BROUILLON_INDICATEURS", "lot_saisie", id_lot, {"nb": len(records)})

                _clear_indicateur_form_keys()

                if is_sub and is_admin:
                    st.success(
                        f"Lot #{id_lot} saisi et transmis directement au régional "
                        f"(auto-validation DP) — {len(records)} lignes."
                    )
                elif is_sub:
                    st.success(f"Lot #{id_lot} soumis pour validation — {len(records)} lignes.")
                else:
                    st.success(f"Brouillon #{id_lot} enregistré — {len(records)} lignes.")

                time.sleep(1)
                st.rerun()

    st.markdown(render_section_close(), unsafe_allow_html=True)


def render_draft_lots(data_type, user, drafts):
    if not drafts:
        st.markdown(render_empty("EDIT", "Aucun brouillon", "Aucun lot en brouillon."), unsafe_allow_html=True)
        return

    st.markdown(render_notice("Vos brouillons sont sauvegardés mais pas encore envoyés pour validation.", "info"), unsafe_allow_html=True)

    for lot in drafts:
        id_lot = lot["id_lot"]
        details = get_lot_details_indicateurs(id_lot) if data_type == "indicateurs" else get_lot_details_reclamations(id_lot)

        with st.expander(
            f"Brouillon #{id_lot} — {get_mois_name(lot['mois'])} {lot['annee']} — {lot['nom_centre']} — {lot['nb_enregistrements']} enreg.",
            expanded=False
        ):
            st.markdown(f"**Statut :** {get_status_badge(lot['statut'])}", unsafe_allow_html=True)

            st.markdown(render_lot_detail_card({
                "lot_id": lot["id_lot"], "agent": lot["cree_par_nom"], "centre": lot["nom_centre"],
                "mois": get_mois_name(lot['mois']), "annee": lot['annee'], "nb": lot["nb_enregistrements"],
                "date_soum": format_datetime(lot.get("date_creation")),
            }), unsafe_allow_html=True)

            if not details:
                st.info("Aucune donnée.")
                continue

            st.markdown("**Modifier les valeurs :**")
            df = pd.DataFrame(details)
            cfg = {"ID": None}

            if data_type == "indicateurs":
                df_show = df[["id_donnee", "code_indicateur", "libelle_indicateur", "categorie", "unite", "valeur_indicateur"]].copy()
                df_show.columns = ["ID", "Code", "Indicateur", "Catégorie", "Unité", "Valeur"]
                cfg["Valeur"] = st.column_config.NumberColumn("Valeur", min_value=0)
            else:
                df_show = pd.DataFrame()
                df_show["ID"] = df["id_donnee"]
                df_show["Code"] = df["code_type"]
                df_show["Type"] = df["libelle_reclamation"]
                df_show["Valeur"] = df.apply(
                    lambda r: (r.get("commentaire_autre") or "—") if r.get("code_type") == "AUTRES" else r.get("valeur_brute", 0),
                    axis=1
                )
                cfg["Valeur"] = st.column_config.TextColumn("Valeur")

            edited = st.data_editor(
                df_show, use_container_width=True, hide_index=True,
                disabled=[c for c in df_show.columns if c != "Valeur"],
                column_config=cfg,
                key=f"draft_ed_{data_type}_{id_lot}"
            )

            st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
            bc1, bc2, bc3, _ = st.columns([1.5, 1.8, 1.2, 2])

            with bc1:
                if st.button("Enregistrer", key=f"save_dr_{data_type}_{id_lot}", use_container_width=True):
                    for i, row in edited.iterrows():
                        orig = details[i]
                        if data_type == "indicateurs":
                            updates = {"valeur_indicateur": float(row["Valeur"])}
                        else:
                            if orig.get("code_type") == "AUTRES":
                                updates = {"commentaire_autre": str(row["Valeur"])}
                            else:
                                updates = {"valeur_brute": float(row["Valeur"]), "nombre_reclamations": int(float(row["Valeur"]))}
                        update_donnee_with_correction(orig["id_donnee"], updates, user["id"], None)
                    st.success("Modifications enregistrées.")
                    time.sleep(1)
                    st.rerun()

            with bc2:
                st.markdown('<div class="btn-success">', unsafe_allow_html=True)
                if st.button("Soumettre pour validation", key=f"sub_dr_{data_type}_{id_lot}", type="primary", use_container_width=True):
                    for i, row in edited.iterrows():
                        orig = details[i]
                        if data_type == "indicateurs":
                            updates = {"valeur_indicateur": float(row["Valeur"])}
                        else:
                            if orig.get("code_type") == "AUTRES":
                                updates = {"commentaire_autre": str(row["Valeur"])}
                            else:
                                updates = {"valeur_brute": float(row["Valeur"]), "nombre_reclamations": int(float(row["Valeur"]))}
                        update_donnee_with_correction(orig["id_donnee"], updates, user["id"], None)
                    submit_lot(id_lot, user["id"])
                    st.success("Brouillon soumis pour validation.")
                    time.sleep(1)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

            with bc3:
                st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
                confirm_key = f"conf_del_{id_lot}"
                if confirm_key not in st.session_state:
                    st.session_state[confirm_key] = False
                if not st.session_state[confirm_key]:
                    if st.button("Supprimer", key=f"del_dr_{data_type}_{id_lot}", use_container_width=True):
                        st.session_state[confirm_key] = True
                        st.rerun()
                else:
                    if st.button("Confirmer", key=f"conf_{data_type}_{id_lot}", use_container_width=True):
                        delete_draft_lot(id_lot)
                        st.session_state[confirm_key] = False
                        st.success("Brouillon supprimé.")
                        time.sleep(1)
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)


def render_rejected_lots(data_type, user, rejected_lots, role):
    if not rejected_lots:
        st.markdown(render_empty("CHECK_CIRCLE", "Aucun lot rejeté", "Aucune donnée à corriger."), unsafe_allow_html=True)
        return

    st.markdown(render_notice(
        f"Les lots ci-dessous contiennent des lignes rejetées. Vous pouvez corriger les valeurs et resoumettre. "
        f"<strong>Toutes vos modifications seront tracées.</strong>",
        "warning"
    ), unsafe_allow_html=True)

    def _val_disp_rec(r):
        """Retourne la valeur en STRING pour l'affichage/édition."""
        if r.get("code_type") == "AUTRES":
            return str(r.get("commentaire_autre") or "")
        v = r.get("valeur_brute", 0)
        if v is None:
            return "0"
        if isinstance(v, float) and v == int(v):
            return str(int(v))
        return str(v)

    for lot in rejected_lots:
        id_lot = lot["id_lot"]
        details = get_lot_details_indicateurs(id_lot) if data_type == "indicateurs" else get_lot_details_reclamations(id_lot)
        rej_lines = [d for d in details if d["statut"] in ("rejete_dp", "rejete_regional")]

        status_lbl = "Rejeté par Admin DP" if lot["statut"] == "partiellement_rejete_dp" else "Rejeté par Admin Régional"

        with st.expander(
            f"{status_lbl} — Lot #{id_lot} — {get_mois_name(lot['mois'])} {lot['annee']} — "
            f"{lot['nom_centre']} — {len(rej_lines)} ligne(s) rejetée(s)",
            expanded=False
        ):
            # ── TÊTE DU LOT ──
            st.markdown(f"**Statut :** {get_status_badge(lot['statut'])}", unsafe_allow_html=True)
            st.markdown(render_lot_detail_card({
                "lot_id": lot["id_lot"], "agent": lot["cree_par_nom"], "centre": lot["nom_centre"],
                "mois": get_mois_name(lot['mois']), "annee": lot['annee'],
                "nb": lot["nb_enregistrements"],
                "date_soum": format_datetime(lot.get("date_soumission")),
            }), unsafe_allow_html=True)

            if lot.get("commentaire_transfert"):
                st.markdown(
                    f"<div style='background:#FEF3C7;border-left:4px solid #F59E0B;"
                    f"padding:1rem;border-radius:6px;margin:0.75rem 0;'>"
                    f"<div style='font-weight:700;color:#78350F;margin-bottom:0.35rem;'>"
                    f"Message de {lot.get('admin_dp_nom', 'Admin DP')} :"
                    f"</div>"
                    f"<div style='color:#78350F;font-style:italic;'>« {lot['commentaire_transfert']} »</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )

            if rej_lines:
                st.markdown("**Lignes à corriger (chaque ligne a son motif spécifique) :**")

                if data_type == "indicateurs":
                    rows = [{
                        "ID": d["id_donnee"], "Code": d["code_indicateur"],
                        "Indicateur": d["libelle_indicateur"], "Unité": d["unite"],
                        "Motif de rejet": d.get("dernier_commentaire") or "Non spécifié",
                        "Valeur": d["valeur_indicateur"]
                    } for d in rej_lines]
                    df_rej = pd.DataFrame(rows)
                    cfg = {
                        "ID": None,
                        "Motif de rejet": st.column_config.TextColumn("Motif de rejet", width="large"),
                        "Valeur": st.column_config.NumberColumn("Nouvelle Valeur", min_value=0),
                    }
                else:
                    rows = [{
                        "ID": d["id_donnee"], "Code": d["code_type"],
                        "Type": d["libelle_reclamation"],
                        "Motif de rejet": d.get("dernier_commentaire") or "Non spécifié",
                        "Valeur": _val_disp_rec(d)
                    } for d in rej_lines]
                    df_rej = pd.DataFrame(rows)
                    df_rej["Valeur"] = df_rej["Valeur"].astype(str)
                    cfg = {
                        "ID": None,
                        "Motif de rejet": st.column_config.TextColumn("Motif de rejet", width="large"),
                        "Valeur": st.column_config.TextColumn("Nouvelle Valeur"),
                    }

                edited = st.data_editor(
                    df_rej, use_container_width=True, hide_index=True,
                    disabled=[c for c in df_rej.columns if c != "Valeur"],
                    column_config=cfg,
                    key=f"rej_ed_{data_type}_{id_lot}"
                )

                st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
                bc1, _ = st.columns([2, 3])
                with bc1:
                    st.markdown('<div class="btn-success">', unsafe_allow_html=True)
                    if st.button("Corriger et resoumettre",
                                 key=f"resub_{data_type}_{id_lot}",
                                 type="primary", use_container_width=True):
                        try:
                            for i, row in edited.iterrows():
                                orig = rej_lines[i]
                                if data_type == "indicateurs":
                                    updates = {"valeur_indicateur": float(row["Valeur"])}
                                else:
                                    if orig.get("code_type") == "AUTRES":
                                        updates = {"commentaire_autre": str(row["Valeur"]).strip() or None}
                                    else:
                                        raw = str(row["Valeur"]).replace(",", ".").strip()
                                        new_val = float(raw) if raw else 0.0
                                        updates = {"valeur_brute": new_val, "nombre_reclamations": int(new_val)}
                                update_donnee_with_correction(orig["id_donnee"], updates, user["id"], None)

                            if lot.get("commentaire_transfert"):
                                marquer_transfert_traite(id_lot)

                            resubmit_lot_after_rejection(id_lot, user["id"])
                            AuthManager.log_action(user["id"], "CORRECTION_RESOUMISSION", "lot_saisie", id_lot, {"role": role})
                            st.success("Corrections enregistrées et lot resoumis.")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur : {e}")
                    st.markdown('</div>', unsafe_allow_html=True)

            render_historique_complet_lot(id_lot, key_prefix=f"rej_{data_type}")


def _render_history(data_type, id_province):
    st.markdown(render_section_open("Historique des saisies", "ARCHIVE"), unsafe_allow_html=True)

    st.markdown("**Filtres :**")
    f1, f2, f3, f4 = st.columns(4)

    with f1:
        all_statuses = ["Tous", "brouillon", "soumis", "valide_dp", "partiellement_rejete_dp", "valide_regional", "partiellement_rejete_regional"]
        f_st = st.selectbox(
            "Statut", all_statuses,
            format_func=lambda x: "Tous les statuts" if x == "Tous" else STATUS_LABELS.get(x, x),
            key=f"hi_s_{data_type}"
        )

    lots_all = get_staging_lots(
        id_province=id_province,
        statut=f_st if f_st != "Tous" else None,
        type_donnees=data_type
    ) or []

    with f2:
        annees_dispo = sorted(set(l["annee"] for l in lots_all), reverse=True)
        f_annee = st.selectbox("Année", ["Toutes"] + annees_dispo, key=f"hi_a_{data_type}")

    with f3:
        mois_dispo = sorted(set(l["mois"] for l in lots_all))
        f_mois = st.selectbox("Mois", ["Tous"] + mois_dispo, format_func=lambda x: "Tous les mois" if x == "Tous" else MOIS_FR[x], key=f"hi_m_{data_type}")

    with f4:
        centres_dispo = sorted(set(l["nom_centre"] for l in lots_all))
        f_centre = st.selectbox("Centre", ["Tous"] + centres_dispo, key=f"hi_c_{data_type}")

    lots = [
        l for l in lots_all
        if (f_annee == "Toutes" or l["annee"] == f_annee)
        and (f_mois == "Tous" or l["mois"] == f_mois)
        and (f_centre == "Tous" or l["nom_centre"] == f_centre)
    ]

    if not lots:
        st.markdown(render_empty("INBOX", "Aucun lot trouvé", "Ajustez vos filtres."), unsafe_allow_html=True)
        st.markdown(render_section_close(), unsafe_allow_html=True)
        return

    paginated, curr_page, total_pages = paginate_list(lots, f"histoi_{data_type}")

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    rows = [{
        "Lot": f"#{l['id_lot']}", "Centre": l["nom_centre"],
        "Créé par": l.get("cree_par_nom", "—"),
        "Période": f"{get_mois_name(l['mois'])} {l['annee']}",
        "Statut": STATUS_LABELS.get(l["statut"], l["statut"]),
        "Enreg.": l["nb_enregistrements"],
        "Créé le": format_datetime(l["date_creation"])
    } for l in paginated]

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
        height=min(400, 40 + 35 * len(rows))
    )

    st.markdown("---")
    lot_opts = {f"Lot #{l['id_lot']} — {l['nom_centre']} ({get_mois_name(l['mois'])} {l['annee']})": l for l in lots}
    sel = st.selectbox("Voir les détails d'un lot", ["—"] + list(lot_opts.keys()), key=f"det_h_{data_type}")

    if sel != "—":
        lot = lot_opts[sel]
        id_lot = lot["id_lot"]

        # ✅ TÊTE DU LOT
        st.markdown(f"**Statut global :** {get_status_badge(lot['statut'])}", unsafe_allow_html=True)
        st.markdown(render_lot_detail_card({
            "lot_id": lot["id_lot"], "agent": lot["cree_par_nom"], "centre": lot["nom_centre"],
            "mois": get_mois_name(lot['mois']), "annee": lot['annee'],
            "nb": lot["nb_enregistrements"], "date_soum": format_datetime(lot.get("date_soumission")),
        }), unsafe_allow_html=True)

        details = get_lot_details_indicateurs(id_lot) if data_type == "indicateurs" else get_lot_details_reclamations(id_lot)

        if details:
            st.markdown("#### Données du lot")
            render_data_table_with_history(
                details=details,
                id_lot=id_lot,
                data_type=data_type,
                key_prefix=f"histo_{data_type}"
            )

    st.markdown(render_section_close(), unsafe_allow_html=True)


def render_modifications_agent(data_type, user, demandes):
    """Onglet pour l'agent : lots à modifier suite à demande admin_dp."""
    if not demandes:
        st.markdown(render_empty("CHECK_CIRCLE", "Aucune modification demandée",
                                  "Aucun lot ne vous a été délégué pour modification."),
                    unsafe_allow_html=True)
        return

    st.markdown(render_notice(
        "L'Admin DP vous a délégué la modification de ces lots. "
        "Modifiez les valeurs demandées et resoumettez.",
        "warning"
    ), unsafe_allow_html=True)

    def _val_disp(r):
        if r.get("code_type") == "AUTRES":
            return str(r.get("commentaire_autre") or "")
        v = r.get("valeur_brute", 0)
        if v is None:
            return "0"
        if isinstance(v, float) and v == int(v):
            return str(int(v))
        return str(v)

    for lot in demandes:
        id_lot = lot["id_lot"]
        details = get_lot_details_indicateurs(id_lot) if data_type == "indicateurs" else get_lot_details_reclamations(id_lot)
        lignes_modif = [d for d in details if d["statut"] == "modif_agent_dp"]

        with st.expander(
            f"Demande de {lot['demandeur_nom']} — Lot #{id_lot} — {get_mois_name(lot['mois'])} {lot['annee']} — "
            f"{lot['nom_centre']} — {len(lignes_modif)} ligne(s)",
            expanded=False
        ):
            st.markdown(f"**Statut :** {get_status_badge(lot['statut'])}", unsafe_allow_html=True)

            st.markdown(
                f"<div style='background:#FEF3C7;border-left:4px solid #F59E0B;"
                f"padding:1rem;border-radius:6px;margin:0.75rem 0;'>"
                f"<div style='font-weight:700;color:#78350F;'>Message de {lot['demandeur_nom']} (Admin DP) :</div>"
                f"<div style='color:#78350F;font-style:italic;margin-top:0.35rem;'>« {lot['commentaire_demande']} »</div>"
                f"</div>",
                unsafe_allow_html=True
            )

            if not lignes_modif:
                st.info("Aucune ligne à modifier.")
                render_historique_complet_lot(id_lot, key_prefix=f"modag_{data_type}")
                continue

            st.markdown("**Lignes à modifier :**")

            cfg = {"ID": None}
            if data_type == "indicateurs":
                rows = [{"ID": d["id_donnee"], "Code": d["code_indicateur"],
                         "Indicateur": d["libelle_indicateur"], "Unité": d["unite"],
                         "Valeur": d["valeur_indicateur"]} for d in lignes_modif]
                cfg["Valeur"] = st.column_config.NumberColumn("Nouvelle Valeur", min_value=0)
            else:
                rows = [{"ID": d["id_donnee"], "Code": d["code_type"],
                         "Type": d["libelle_reclamation"],
                         "Valeur": _val_disp(d)}
                         for d in lignes_modif]
                cfg["Valeur"] = st.column_config.TextColumn("Nouvelle Valeur")

            df_edit = pd.DataFrame(rows)
            if data_type == "reclamations":
                df_edit["Valeur"] = df_edit["Valeur"].astype(str)

            edited = st.data_editor(
                df_edit, use_container_width=True, hide_index=True,
                disabled=[c for c in df_edit.columns if c != "Valeur"],
                column_config=cfg,
                key=f"modag_ed_{data_type}_{id_lot}"
            )

            st.markdown('<div class="btn-success">', unsafe_allow_html=True)
            if st.button("Enregistrer et resoumettre", key=f"modag_save_{data_type}_{id_lot}", type="primary"):
                for i, row in edited.iterrows():
                    orig = lignes_modif[i]
                    if data_type == "indicateurs":
                        updates = {"valeur_indicateur": float(row["Valeur"])}
                    else:
                        if orig.get("code_type") == "AUTRES":
                            updates = {"commentaire_autre": str(row["Valeur"]).strip() or None}
                        else:
                            raw = str(row["Valeur"]).replace(",", ".").strip()
                            new_val = float(raw) if raw else 0.0
                            updates = {"valeur_brute": new_val, "nombre_reclamations": int(new_val)}
                    update_donnee_with_correction(orig["id_donnee"], updates, user["id"], "Modification agent suite à demande admin DP")

                resoumettre_apres_modif_agent(id_lot, user["id"])
                AuthManager.log_action(user["id"], "MODIF_AGENT_APRES_DEM", "lot_saisie", id_lot)
                st.success("Modifications enregistrées. Le lot repart en validation Admin DP → Régional.")
                time.sleep(1)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

            render_historique_complet_lot(id_lot, key_prefix=f"modag_{data_type}")