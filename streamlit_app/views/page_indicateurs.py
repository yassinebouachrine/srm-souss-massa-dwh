# views/page_indicateurs.py
import streamlit as st
import pandas as pd
from datetime import datetime
from auth.session_manager import SessionManager
from auth.authentication import AuthManager
from db.queries import (
    get_types_indicateur, insert_staging_indicateurs,
    get_staging_indicateurs, get_staging_reclamations,
    submit_lot, get_staging_lots,
    get_rejected_lots, reset_lot_for_correction, update_staging_record,
    get_draft_lots, delete_lot
)
from config.provinces import get_province_name, get_centres_for_province
from utils.helpers import generate_lot_id, get_current_period, MOIS_FR, get_mois_name, format_datetime
from utils.styles import (
    render_page_header, render_notice, render_empty,
    render_section_open, render_section_close,
    render_form_category, get_status_badge,
    render_lot_detail_card, STATUS_LABELS
)


def render_indicateurs():
    SessionManager.require_role(["agent_dp", "admin_dp", "super_admin"])
    user = SessionManager.get_user()
    id_province = user["id_province"]
    code_province = user["code_province"]
    province_name = get_province_name(id_province)
    role = user["role"]

    st.markdown(
        render_page_header("Indicateurs de performance DP", f"Province de {province_name}"),
        unsafe_allow_html=True,
    )

    # Récupérer les brouillons et rejetés
    drafts = get_draft_lots(id_province, "indicateurs") or []
    rejected = get_rejected_lots(id_province, "indicateurs") or []

    # Alertes
    if rejected:
        who = "Vos" if role == "agent_dp" else "Les"
        st.markdown(render_notice(
            f"{who} lot(s) rejeté(s) : <strong>{len(rejected)}</strong>. "
            f"Consultez l'onglet « Lots rejetés » pour corriger et resoumettre.",
            "warning"
        ), unsafe_allow_html=True)

    if drafts:
        st.markdown(render_notice(
            f"Vous avez <strong>{len(drafts)}</strong> brouillon(s) non soumis. "
            f"N'oubliez pas de les compléter et les soumettre.",
            "info"
        ), unsafe_allow_html=True)

    tab_new, tab_drafts, tab_rejected, tab_hist = st.tabs([
        "Nouvelle saisie",
        f"Brouillons ({len(drafts)})",
        f"Lots rejetés ({len(rejected)})",
        "Historique"
    ])

    with tab_new:
        _render_new_entry(user, id_province, code_province, province_name)

    with tab_drafts:
        render_draft_lots("indicateurs", id_province, user, drafts)

    with tab_rejected:
        render_rejected_lots("indicateurs", id_province, user, rejected)

    with tab_hist:
        _render_history("indicateurs", id_province)


def _render_new_entry(user, id_province, code_province, province_name):
    """Formulaire de saisie."""
    st.markdown(render_notice(
        "Sélectionnez la période et le centre, puis remplissez les valeurs. "
        "Vous pouvez enregistrer en brouillon pour continuer plus tard."
    ), unsafe_allow_html=True)

    st.markdown(render_section_open("Période et centre", "CALENDAR"), unsafe_allow_html=True)

    cy, cm = get_current_period()
    c1, c2, c3 = st.columns(3)
    with c1:
        annee = st.selectbox("Année", list(range(cy, cy - 3, -1)), key="i_a")
    with c2:
        mois = st.selectbox("Mois", list(range(1, 13)), format_func=lambda x: MOIS_FR[x],
                            index=max(0, cm - 2), key="i_m")
    with c3:
        centres = get_centres_for_province(id_province)
        cmap = {c["nom"]: c for c in centres}
        cn = st.selectbox("Centre", list(cmap.keys()), key="i_c")
        centre = cmap[cn]

    st.markdown(render_section_close(), unsafe_allow_html=True)

    types = get_types_indicateur()
    if not types:
        st.warning("Aucun type d'indicateur configuré.")
        return

    cats = {}
    for t in types:
        cats.setdefault(t["categorie"] or "Autres", []).append(t)

    st.markdown(render_section_open("Saisie des valeurs", "EDIT"), unsafe_allow_html=True)

    with st.form("form_ind", clear_on_submit=False):
        vals = {}
        for cat_name, indics in cats.items():
            st.markdown(render_form_category("FOLDER", cat_name), unsafe_allow_html=True)
            for ind in indics:
                col_label, col_vm, col_vr = st.columns([5, 2, 2])
                with col_label:
                    st.markdown(
                        f"**{ind['libelle_indicateur']}** "
                        f"<span style='color:#6B7280;font-size:0.78rem;'>({ind['unite']})</span>",
                        unsafe_allow_html=True
                    )
                with col_vm:
                    vm = st.number_input("Mensuelle", min_value=0.0, value=0.0, step=0.01,
                                          key=f"vm_{ind['code_indicateur']}")
                with col_vr:
                    vr = st.number_input("Récapitulative", min_value=0.0, value=0.0, step=0.01,
                                          key=f"vr_{ind['code_indicateur']}")
                vals[ind["code_indicateur"]] = {
                    "vm": vm, "vr": vr, "lib": ind["libelle_indicateur"],
                    "unite": ind["unite"], "cat": cat_name,
                }

        st.markdown("---")
        b1, b2 = st.columns(2)
        with b1:
            draft = st.form_submit_button("Enregistrer brouillon", use_container_width=True)
        with b2:
            submit = st.form_submit_button("Soumettre pour validation",
                                            use_container_width=True, type="primary")

        if draft or submit:
            has = any(v["vm"] > 0 or v["vr"] > 0 for v in vals.values())
            if not has:
                st.error("Saisissez au moins une valeur non nulle.")
            else:
                lot_id = generate_lot_id(code_province, "INDIC")
                status = "brouillon" if draft else "soumis"
                records = []
                for code, v in vals.items():
                    if v["vm"] > 0 or v["vr"] > 0:
                        records.append((
                            id_province, province_name, centre["id"], centre["nom"],
                            annee, mois, MOIS_FR[mois], code, v["lib"], v["unite"], v["cat"],
                            v["vm"], v["vr"], status, user["id"],
                            datetime.now() if submit else None, lot_id,
                        ))
                try:
                    insert_staging_indicateurs(records)
                    AuthManager.log_action(
                        user["id"],
                        "SAISIE_INDICATEURS" if draft else "SOUMISSION_INDICATEURS",
                        "staging_indicateurs_dp",
                        details={"lot_id": lot_id, "nb": len(records)},
                    )
                    if draft:
                        st.success(f"Brouillon enregistré — {len(records)} indicateurs. "
                                   f"Vous pouvez le modifier dans l'onglet « Brouillons ».")
                    else:
                        st.success(f"Soumis pour validation — {len(records)} indicateurs.")
                except Exception as e:
                    st.error(f"Erreur : {e}")

    st.markdown(render_section_close(), unsafe_allow_html=True)


def render_draft_lots(data_type, id_province, user, drafts):
    """
    Affiche les lots en brouillon avec possibilité de modifier, soumettre ou supprimer.
    Accessible aux agents ET admins DP.
    """
    if not drafts:
        st.markdown(render_empty("EDIT", "Aucun brouillon",
                                  "Aucun lot en brouillon. Vos saisies non soumises apparaîtront ici."),
                    unsafe_allow_html=True)
        return

    st.markdown(render_notice(
        "Vos brouillons sont sauvegardés mais pas encore envoyés pour validation. "
        "Vous pouvez modifier les valeurs, ajouter des données, puis soumettre ou supprimer le lot.",
        "info"
    ), unsafe_allow_html=True)

    for lot in drafts:
        # Récupérer les détails
        if data_type == "indicateurs":
            details = get_staging_indicateurs(lot_id=lot["lot_id"])
        else:
            details = get_staging_reclamations(lot_id=lot["lot_id"])

        if not details:
            continue

        first = details[0]

        with st.expander(
            f"📝 Brouillon — {get_mois_name(lot['mois'])} {lot['annee']} — "
            f"{first.get('nom_centre', '—')} — {lot['nb_enregistrements']} enreg.",
            expanded=False,
        ):
            # Infos du lot
            st.markdown(render_lot_detail_card({
                "lot_id": lot["lot_id"],
                "agent": first.get("soumis_par_nom", "—"),
                "centre": first.get("nom_centre", "—"),
                "mois": get_mois_name(lot["mois"]),
                "annee": lot["annee"],
                "nb": lot["nb_enregistrements"],
                "date_soum": format_datetime(lot.get("date_modification")),
            }), unsafe_allow_html=True)

            # Éditeur
            st.markdown("**Modifier les valeurs :**")

            df = pd.DataFrame(details)

            if data_type == "indicateurs":
                editable_df = df[["id_staging", "code_indicateur", "libelle_indicateur",
                                   "valeur_mensuelle", "valeur_recapitulatif"]].copy()
                editable_df.columns = ["ID", "Code", "Indicateur", "Val. mensuelle", "Val. récap."]

                edited = st.data_editor(
                    editable_df,
                    use_container_width=True,
                    hide_index=True,
                    disabled=["ID", "Code", "Indicateur"],
                    column_config={
                        "ID": None,
                        "Val. mensuelle": st.column_config.NumberColumn("Val. mensuelle", format="%.2f", min_value=0),
                        "Val. récap.": st.column_config.NumberColumn("Val. récap.", format="%.2f", min_value=0),
                    },
                    key=f"draft_ind_{lot['lot_id']}",
                )
            else:
                editable_df = df[["id_staging", "code_type", "libelle_reclamation",
                                   "nombre_reclamations", "temps_moyen_coupure_h",
                                   "delai_moyen_traitement_j", "valeur_brute"]].copy()
                editable_df.columns = ["ID", "Code", "Type", "Nombre", "TMC (h)", "DMT (j)", "Val. brute"]

                edited = st.data_editor(
                    editable_df,
                    use_container_width=True,
                    hide_index=True,
                    disabled=["ID", "Code", "Type"],
                    column_config={
                        "ID": None,
                        "Nombre": st.column_config.NumberColumn("Nombre", min_value=0),
                        "TMC (h)": st.column_config.NumberColumn("TMC (h)", format="%.1f", min_value=0),
                        "DMT (j)": st.column_config.NumberColumn("DMT (j)", format="%.1f", min_value=0),
                        "Val. brute": st.column_config.NumberColumn("Val. brute", format="%.2f", min_value=0),
                    },
                    key=f"draft_rec_{lot['lot_id']}",
                )

            st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

            # 3 boutons d'action
            bc1, bc2, bc3, _ = st.columns([1.5, 1.8, 1.2, 2])

            with bc1:
                if st.button("💾 Enregistrer",
                             key=f"save_draft_{data_type}_{lot['lot_id']}",
                             use_container_width=True,
                             help="Sauvegarder les modifications sans soumettre"):
                    try:
                        for i, row in edited.iterrows():
                            original = details[i]
                            if data_type == "indicateurs":
                                update_staging_record("indicateurs", original["id_staging"], {
                                    "valeur_mensuelle": float(row["Val. mensuelle"]),
                                    "valeur_recapitulatif": float(row["Val. récap."]),
                                })
                            else:
                                update_staging_record("reclamations", original["id_staging"], {
                                    "nombre_reclamations": int(row["Nombre"]),
                                    "temps_moyen_coupure_h": float(row["TMC (h)"]),
                                    "delai_moyen_traitement_j": float(row["DMT (j)"]),
                                    "valeur_brute": float(row["Val. brute"]),
                                })
                        AuthManager.log_action(user["id"], "MODIFICATION_BROUILLON",
                                                f"staging_{data_type}_dp",
                                                details={"lot_id": lot["lot_id"]})
                        st.success("Modifications enregistrées.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {e}")

            with bc2:
                st.markdown('<div class="btn-success">', unsafe_allow_html=True)
                if st.button("📤 Soumettre pour validation",
                             key=f"submit_draft_{data_type}_{lot['lot_id']}",
                             type="primary",
                             use_container_width=True):
                    try:
                        # D'abord enregistrer les modifications
                        for i, row in edited.iterrows():
                            original = details[i]
                            if data_type == "indicateurs":
                                update_staging_record("indicateurs", original["id_staging"], {
                                    "valeur_mensuelle": float(row["Val. mensuelle"]),
                                    "valeur_recapitulatif": float(row["Val. récap."]),
                                })
                            else:
                                update_staging_record("reclamations", original["id_staging"], {
                                    "nombre_reclamations": int(row["Nombre"]),
                                    "temps_moyen_coupure_h": float(row["TMC (h)"]),
                                    "delai_moyen_traitement_j": float(row["DMT (j)"]),
                                    "valeur_brute": float(row["Val. brute"]),
                                })
                        # Puis soumettre
                        submit_lot(data_type, lot["lot_id"], user["id"])
                        AuthManager.log_action(user["id"], "SOUMISSION_BROUILLON",
                                                f"staging_{data_type}_dp",
                                                details={"lot_id": lot["lot_id"]})
                        st.success("Brouillon soumis pour validation.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {e}")
                st.markdown('</div>', unsafe_allow_html=True)

            with bc3:
                st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
                # Système de confirmation via session_state
                confirm_key = f"confirm_del_{lot['lot_id']}"
                if confirm_key not in st.session_state:
                    st.session_state[confirm_key] = False

                if not st.session_state[confirm_key]:
                    if st.button("🗑️ Supprimer",
                                 key=f"del_draft_{data_type}_{lot['lot_id']}",
                                 use_container_width=True,
                                 help="Supprimer définitivement ce brouillon"):
                        st.session_state[confirm_key] = True
                        st.rerun()
                else:
                    if st.button("⚠️ Confirmer",
                                 key=f"confirm_{data_type}_{lot['lot_id']}",
                                 use_container_width=True):
                        try:
                            delete_lot(data_type, lot["lot_id"])
                            AuthManager.log_action(user["id"], "SUPPRESSION_BROUILLON",
                                                    f"staging_{data_type}_dp",
                                                    details={"lot_id": lot["lot_id"]})
                            st.session_state[confirm_key] = False
                            st.success("Brouillon supprimé.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur : {e}")
                st.markdown('</div>', unsafe_allow_html=True)


def render_rejected_lots(data_type, id_province, user, rejected):
    """Affiche les lots rejetés."""
    role = user["role"]

    if not rejected:
        st.markdown(render_empty("CHECK_CIRCLE", "Aucun lot rejeté",
                                  "Aucune donnée nécessitant de correction"),
                    unsafe_allow_html=True)
        return

    who_can_correct = "Vous pouvez" if role == "agent_dp" else "En tant qu'admin DP, vous pouvez"
    st.markdown(render_notice(
        f"Les lots ci-dessous ont été rejetés. {who_can_correct} consulter le motif, "
        f"corriger les données, puis les resoumettre pour validation.",
        "warning"
    ), unsafe_allow_html=True)

    for lot in rejected:
        status_label = "Rejeté par Admin DP" if lot["statut"] == "rejete_dp" else "Rejeté par Admin Régional"

        with st.expander(
            f"❌ {status_label} — {get_mois_name(lot['mois'])} {lot['annee']} — "
            f"{lot['nb_enregistrements']} enreg.",
            expanded=True,
        ):
            if data_type == "indicateurs":
                details = get_staging_indicateurs(lot_id=lot["lot_id"])
            else:
                details = get_staging_reclamations(lot_id=lot["lot_id"])

            if not details:
                st.info("Aucune donnée trouvée.")
                continue

            first = details[0]
            comment_dp = first.get("commentaire_dp", "")
            comment_reg = first.get("commentaire_regional", "")
            motif = comment_reg or comment_dp

            if motif:
                st.markdown(render_notice(f"<strong>Motif du rejet :</strong> {motif}", "error"),
                            unsafe_allow_html=True)

            st.markdown(render_lot_detail_card({
                "lot_id": lot["lot_id"],
                "agent": first.get("soumis_par_nom", "—"),
                "centre": first.get("nom_centre", "—"),
                "mois": get_mois_name(lot["mois"]),
                "annee": lot["annee"],
                "nb": lot["nb_enregistrements"],
                "date_soum": format_datetime(first.get("date_soumission")),
            }), unsafe_allow_html=True)

            st.markdown("**Corriger les données :**")

            df = pd.DataFrame(details)

            if data_type == "indicateurs":
                editable_df = df[["id_staging", "code_indicateur", "libelle_indicateur",
                                   "valeur_mensuelle", "valeur_recapitulatif"]].copy()
                editable_df.columns = ["ID", "Code", "Indicateur", "Val. mensuelle", "Val. récap."]
                edited = st.data_editor(
                    editable_df,
                    use_container_width=True, hide_index=True,
                    disabled=["ID", "Code", "Indicateur"],
                    column_config={
                        "ID": None,
                        "Val. mensuelle": st.column_config.NumberColumn("Val. mensuelle", format="%.2f", min_value=0),
                        "Val. récap.": st.column_config.NumberColumn("Val. récap.", format="%.2f", min_value=0),
                    },
                    key=f"edit_ind_{lot['lot_id']}",
                )
            else:
                editable_df = df[["id_staging", "code_type", "libelle_reclamation",
                                   "nombre_reclamations", "temps_moyen_coupure_h",
                                   "delai_moyen_traitement_j", "valeur_brute"]].copy()
                editable_df.columns = ["ID", "Code", "Type", "Nombre", "TMC (h)", "DMT (j)", "Val. brute"]
                edited = st.data_editor(
                    editable_df,
                    use_container_width=True, hide_index=True,
                    disabled=["ID", "Code", "Type"],
                    column_config={
                        "ID": None,
                        "Nombre": st.column_config.NumberColumn("Nombre", min_value=0),
                        "TMC (h)": st.column_config.NumberColumn("TMC (h)", format="%.1f", min_value=0),
                        "DMT (j)": st.column_config.NumberColumn("DMT (j)", format="%.1f", min_value=0),
                        "Val. brute": st.column_config.NumberColumn("Val. brute", format="%.2f", min_value=0),
                    },
                    key=f"edit_rec_{lot['lot_id']}",
                )

            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            bc1, bc2, _ = st.columns([2, 1.5, 3])

            with bc1:
                st.markdown('<div class="btn-success">', unsafe_allow_html=True)
                if st.button("Corriger et resoumettre",
                             key=f"resub_{data_type}_{lot['lot_id']}", type="primary",
                             use_container_width=True):
                    try:
                        for i, row in edited.iterrows():
                            original = details[i]
                            if data_type == "indicateurs":
                                update_staging_record("indicateurs", original["id_staging"], {
                                    "valeur_mensuelle": float(row["Val. mensuelle"]),
                                    "valeur_recapitulatif": float(row["Val. récap."]),
                                })
                            else:
                                update_staging_record("reclamations", original["id_staging"], {
                                    "nombre_reclamations": int(row["Nombre"]),
                                    "temps_moyen_coupure_h": float(row["TMC (h)"]),
                                    "delai_moyen_traitement_j": float(row["DMT (j)"]),
                                    "valeur_brute": float(row["Val. brute"]),
                                })
                        submit_lot(data_type, lot["lot_id"], user["id"])
                        AuthManager.log_action(user["id"], "CORRECTION_RESOUMISSION",
                                                f"staging_{data_type}_dp",
                                                details={"lot_id": lot["lot_id"], "role": role})
                        st.success("Corrections enregistrées et lot resoumis.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {e}")
                st.markdown('</div>', unsafe_allow_html=True)

            with bc2:
                if st.button("Remettre en brouillon",
                             key=f"draft_{data_type}_{lot['lot_id']}",
                             use_container_width=True,
                             help="Le lot repasse en brouillon (modifiable dans l'onglet Brouillons)"):
                    reset_lot_for_correction(data_type, lot["lot_id"])
                    AuthManager.log_action(user["id"], "RESET_BROUILLON",
                                            f"staging_{data_type}_dp",
                                            details={"lot_id": lot["lot_id"]})
                    st.info("Lot remis en brouillon. Consultez l'onglet « Brouillons ».")
                    st.rerun()


def _render_history(data_type, id_province):
    """Historique complet des saisies."""
    st.markdown(render_section_open("Historique des saisies", "ARCHIVE"), unsafe_allow_html=True)

    f_st = st.selectbox("Filtrer par statut",
                        ["Tous", "brouillon", "soumis", "valide_dp",
                         "rejete_dp", "valide_regional", "rejete_regional"],
                        format_func=lambda x: "Tous les statuts" if x == "Tous" else STATUS_LABELS.get(x, x),
                        key="hi_s")

    lots = get_staging_lots(
        id_province=id_province,
        statut=f_st if f_st != "Tous" else None,
        data_type=data_type,
    )

    if lots:
        rows = []
        for l in lots:
            rows.append({
                "Lot": l["lot_id"][-15:],
                "Année": l["annee"],
                "Mois": get_mois_name(l["mois"]),
                "Statut": STATUS_LABELS.get(l["statut"], l["statut"]),
                "Enreg.": l["nb_enregistrements"],
                "Créé le": format_datetime(l.get("date_creation")),
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("---")
        lot_opts = {f"{l['lot_id'][-15:]}... — {get_mois_name(l['mois'])} {l['annee']} ({STATUS_LABELS.get(l['statut'], l['statut'])})": l
                    for l in lots}
        sel = st.selectbox("Voir les détails d'un lot", ["—"] + list(lot_opts.keys()), key="det_h")

        if sel != "—":
            lot = lot_opts[sel]
            st.markdown(f"**Statut :** {get_status_badge(lot['statut'])}", unsafe_allow_html=True)

            if data_type == "indicateurs":
                details = get_staging_indicateurs(lot_id=lot["lot_id"])
            else:
                details = get_staging_reclamations(lot_id=lot["lot_id"])

            if details:
                df_d = pd.DataFrame(details)
                if data_type == "indicateurs":
                    cols = [c for c in ["code_indicateur", "libelle_indicateur", "unite",
                                        "valeur_mensuelle", "valeur_recapitulatif"] if c in df_d.columns]
                else:
                    cols = [c for c in ["code_type", "libelle_reclamation", "nombre_reclamations",
                                        "temps_moyen_coupure_h", "delai_moyen_traitement_j",
                                        "valeur_brute"] if c in df_d.columns]
                st.dataframe(df_d[cols], use_container_width=True, hide_index=True)
    else:
        st.markdown(render_empty("INBOX", "Aucun lot trouvé"), unsafe_allow_html=True)

    st.markdown(render_section_close(), unsafe_allow_html=True)