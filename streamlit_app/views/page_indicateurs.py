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
    get_draft_lots, delete_lot,
    update_staging_record_with_history, get_lot_corrections
)
from config.provinces import get_province_name, get_centres_for_province
from utils.helpers import generate_lot_id, get_current_period, MOIS_FR, get_mois_name, format_datetime
from utils.styles import (
    render_page_header, render_notice, render_empty,
    render_section_open, render_section_close,
    render_form_category, get_status_badge,
    render_lot_detail_card, STATUS_LABELS
)


# ═══════════════════════════════════════════════════════════════
# Catégories statiques
# ═══════════════════════════════════════════════════════════════
STATIC_CATEGORIES = ["Infrastructure"]


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

    drafts = get_draft_lots(id_province, "indicateurs") or []
    rejected = get_rejected_lots(id_province, "indicateurs") or []

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
    """Formulaire de saisie avec séparation mensuel/statique."""

    st.markdown(render_notice(
        "Sélectionnez la période et le centre, puis saisissez la valeur de chaque indicateur. "
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

    cats_mensuelles = {}
    cats_statiques = {}
    for t in types:
        cat = t["categorie"] or "Autres"
        if cat in STATIC_CATEGORIES:
            cats_statiques.setdefault(cat, []).append(t)
        else:
            cats_mensuelles.setdefault(cat, []).append(t)

    st.markdown(render_section_open("Indicateurs mensuels", "EDIT"), unsafe_allow_html=True)

    st.markdown(
        "<div style='font-size:0.82rem;color:#6B7280;margin-bottom:0.75rem;'>"
        "Indicateurs à saisir <strong>chaque mois</strong> selon l'activité du centre."
        "</div>",
        unsafe_allow_html=True
    )

    with st.form("form_ind", clear_on_submit=False):
        vals = {}

        for cat_name, indics in cats_mensuelles.items():
            st.markdown(render_form_category("FOLDER", cat_name), unsafe_allow_html=True)

            hc1, hc2 = st.columns([6, 3])
            with hc1:
                st.markdown(
                    "<div style='font-weight:600;font-size:0.8rem;color:#6B7280;'>INDICATEUR</div>",
                    unsafe_allow_html=True
                )
            with hc2:
                st.markdown(
                    "<div style='font-weight:600;font-size:0.8rem;color:#6B7280;'>VALEUR</div>",
                    unsafe_allow_html=True
                )

            for ind in indics:
                col_label, col_val = st.columns([6, 3])
                with col_label:
                    st.markdown(
                        f"<div style='padding-top:0.5rem;'>"
                        f"<strong>{ind['libelle_indicateur']}</strong> "
                        f"<span style='color:#6B7280;font-size:0.78rem;'>({ind['unite']})</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                with col_val:
                    val = st.number_input(
                        f"Valeur {ind['code_indicateur']}",
                        min_value=0.0, value=0.0, step=0.01, format="%.2f",
                        key=f"val_{ind['code_indicateur']}",
                        label_visibility="collapsed",
                    )

                vals[ind["code_indicateur"]] = {
                    "valeur": val,
                    "lib": ind["libelle_indicateur"],
                    "unite": ind["unite"],
                    "cat": cat_name,
                }

        if cats_statiques:
            st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
            st.markdown(
                "<div style='background:#FEF3C7;border-left:4px solid #F59E0B;"
                "padding:0.85rem 1.15rem;border-radius:6px;margin:1rem 0;'>"
                "<div style='font-weight:700;color:#78350F;font-size:0.9rem;margin-bottom:0.25rem;'>"
                "Indicateurs statiques (Infrastructure)"
                "</div>"
                "<div style='font-size:0.8rem;color:#78350F;'>"
                "Ces indicateurs ne changent <strong>pas chaque mois</strong>. "
                "Saisissez-les uniquement lors d'un <strong>changement réel</strong>. "
                "Laissez à 0 si aucun changement."
                "</div></div>",
                unsafe_allow_html=True
            )

            for cat_name, indics in cats_statiques.items():
                st.markdown(render_form_category("FOLDER", cat_name), unsafe_allow_html=True)

                hc1, hc2 = st.columns([6, 3])
                with hc1:
                    st.markdown(
                        "<div style='font-weight:600;font-size:0.8rem;color:#6B7280;'>INDICATEUR</div>",
                        unsafe_allow_html=True
                    )
                with hc2:
                    st.markdown(
                        "<div style='font-weight:600;font-size:0.8rem;color:#6B7280;'>VALEUR</div>",
                        unsafe_allow_html=True
                    )

                for ind in indics:
                    col_label, col_val = st.columns([6, 3])
                    with col_label:
                        st.markdown(
                            f"<div style='padding-top:0.5rem;'>"
                            f"<strong>{ind['libelle_indicateur']}</strong> "
                            f"<span style='color:#6B7280;font-size:0.78rem;'>({ind['unite']})</span>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                    with col_val:
                        val = st.number_input(
                            f"Valeur {ind['code_indicateur']}",
                            min_value=0.0, value=0.0, step=0.01, format="%.2f",
                            key=f"val_{ind['code_indicateur']}",
                            label_visibility="collapsed",
                            help="Laissez à 0 si pas de changement ce mois-ci",
                        )

                    vals[ind["code_indicateur"]] = {
                        "valeur": val,
                        "lib": ind["libelle_indicateur"],
                        "unite": ind["unite"],
                        "cat": cat_name,
                    }

        st.markdown("---")
        b1, b2 = st.columns(2)
        with b1:
            draft = st.form_submit_button("Enregistrer brouillon", use_container_width=True)
        with b2:
            submit = st.form_submit_button("Soumettre pour validation",
                                            use_container_width=True, type="primary")

        if draft or submit:
            has = any(v["valeur"] > 0 for v in vals.values())
            if not has:
                st.error("Saisissez au moins une valeur non nulle.")
            else:
                lot_id = generate_lot_id(code_province, "INDIC")
                status = "brouillon" if draft else "soumis"
                records = []

                for code, v in vals.items():
                    if v["valeur"] > 0:
                        records.append((
                            id_province, province_name, centre["id"], centre["nom"],
                            annee, mois, MOIS_FR[mois], code, v["lib"], v["unite"], v["cat"],
                            v["valeur"], status, user["id"],
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
                        st.success(f"Brouillon enregistré — {len(records)} indicateurs.")
                    else:
                        st.success(f"Soumis pour validation — {len(records)} indicateurs.")
                except Exception as e:
                    st.error(f"Erreur : {e}")

    st.markdown(render_section_close(), unsafe_allow_html=True)


def render_draft_lots(data_type, id_province, user, drafts):
    """Affiche les lots en brouillon."""
    if not drafts:
        st.markdown(render_empty(
            "EDIT", "Aucun brouillon",
            "Aucun lot en brouillon."
        ), unsafe_allow_html=True)
        return

    st.markdown(render_notice(
        "Vos brouillons sont sauvegardés mais pas encore envoyés pour validation.",
        "info"
    ), unsafe_allow_html=True)

    for lot in drafts:
        if data_type == "indicateurs":
            details = get_staging_indicateurs(lot_id=lot["lot_id"])
        else:
            details = get_staging_reclamations(lot_id=lot["lot_id"])

        if not details:
            continue

        first = details[0]

        with st.expander(
            f"Brouillon — {get_mois_name(lot['mois'])} {lot['annee']} — "
            f"{first.get('nom_centre', '—')} — {lot['nb_enregistrements']} enreg.",
            expanded=False,
        ):
            st.markdown(render_lot_detail_card({
                "lot_id": lot["lot_id"],
                "agent": first.get("soumis_par_nom", "—"),
                "centre": first.get("nom_centre", "—"),
                "mois": get_mois_name(lot["mois"]),
                "annee": lot["annee"],
                "nb": lot["nb_enregistrements"],
                "date_soum": format_datetime(lot.get("date_modification")),
            }), unsafe_allow_html=True)

            st.markdown("**Modifier les valeurs :**")

            df = pd.DataFrame(details)

            if data_type == "indicateurs":
                editable_df = df[[
                    "id_staging", "code_indicateur", "libelle_indicateur",
                    "categorie", "unite", "valeur_indicateur"
                ]].copy()
                editable_df.columns = ["ID", "Code", "Indicateur", "Catégorie", "Unité", "Valeur"]

                edited = st.data_editor(
                    editable_df,
                    use_container_width=True, hide_index=True,
                    disabled=["ID", "Code", "Indicateur", "Catégorie", "Unité"],
                    column_config={
                        "ID": None,
                        "Valeur": st.column_config.NumberColumn("Valeur", format="%.2f", min_value=0),
                    },
                    key=f"draft_ind_{lot['lot_id']}",
                )
            else:
                editable_df = df[[
                    "id_staging", "code_type", "libelle_reclamation", "valeur_brute"
                ]].copy()
                editable_df.columns = ["ID", "Code", "Type", "Valeur"]

                edited = st.data_editor(
                    editable_df,
                    use_container_width=True, hide_index=True,
                    disabled=["ID", "Code", "Type"],
                    column_config={
                        "ID": None,
                        "Valeur": st.column_config.NumberColumn("Valeur", format="%.2f", min_value=0),
                    },
                    key=f"draft_rec_{lot['lot_id']}",
                )

            st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

            bc1, bc2, bc3, _ = st.columns([1.5, 1.8, 1.2, 2])

            with bc1:
                if st.button("Enregistrer", key=f"save_draft_{data_type}_{lot['lot_id']}",
                             use_container_width=True):
                    try:
                        for i, row in edited.iterrows():
                            original = details[i]
                            if data_type == "indicateurs":
                                update_staging_record("indicateurs", original["id_staging"], {
                                    "valeur_indicateur": float(row["Valeur"]),
                                })
                            else:
                                update_staging_record("reclamations", original["id_staging"], {
                                    "nombre_reclamations": int(row["Valeur"]),
                                    "valeur_brute": float(row["Valeur"]),
                                })
                        st.success("Modifications enregistrées.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {e}")

            with bc2:
                st.markdown('<div class="btn-success">', unsafe_allow_html=True)
                if st.button("Soumettre pour validation",
                             key=f"submit_draft_{data_type}_{lot['lot_id']}",
                             type="primary", use_container_width=True):
                    try:
                        for i, row in edited.iterrows():
                            original = details[i]
                            if data_type == "indicateurs":
                                update_staging_record("indicateurs", original["id_staging"], {
                                    "valeur_indicateur": float(row["Valeur"]),
                                })
                            else:
                                update_staging_record("reclamations", original["id_staging"], {
                                    "nombre_reclamations": int(row["Valeur"]),
                                    "valeur_brute": float(row["Valeur"]),
                                })
                        submit_lot(data_type, lot["lot_id"], user["id"])
                        st.success("Brouillon soumis pour validation.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {e}")
                st.markdown('</div>', unsafe_allow_html=True)

            with bc3:
                st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
                confirm_key = f"confirm_del_{lot['lot_id']}"
                if confirm_key not in st.session_state:
                    st.session_state[confirm_key] = False

                if not st.session_state[confirm_key]:
                    if st.button("Supprimer", key=f"del_draft_{data_type}_{lot['lot_id']}",
                                 use_container_width=True):
                        st.session_state[confirm_key] = True
                        st.rerun()
                else:
                    if st.button("Confirmer", key=f"confirm_{data_type}_{lot['lot_id']}",
                                 use_container_width=True):
                        try:
                            delete_lot(data_type, lot["lot_id"])
                            st.session_state[confirm_key] = False
                            st.success("Brouillon supprimé.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur : {e}")
                st.markdown('</div>', unsafe_allow_html=True)


def render_rejected_lots(data_type, id_province, user, rejected):
    """Affiche les lots rejetés avec traçabilité des corrections."""
    role = user["role"]

    if not rejected:
        st.markdown(render_empty(
            "CHECK_CIRCLE", "Aucun lot rejeté",
            "Aucune donnée nécessitant de correction"
        ), unsafe_allow_html=True)
        return

    who_can_correct = "Vous pouvez" if role == "agent_dp" else "En tant qu'admin DP, vous pouvez"
    st.markdown(render_notice(
        f"Les lots ci-dessous ont été rejetés. {who_can_correct} consulter le motif, "
        f"corriger les données, puis les resoumettre pour validation. "
        f"<strong>Toutes vos modifications seront tracées.</strong>",
        "warning"
    ), unsafe_allow_html=True)

    for lot in rejected:
        status_label = (
            "Rejeté par Admin DP" if lot["statut"] == "rejete_dp"
            else "Rejeté par Admin Régional"
        )

        with st.expander(
            f"{status_label} — {get_mois_name(lot['mois'])} {lot['annee']} — "
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
                st.markdown(render_notice(
                    f"<strong>Motif du rejet :</strong> {motif}", "error"
                ), unsafe_allow_html=True)

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
                editable_df = df[[
                    "id_staging", "code_indicateur", "libelle_indicateur",
                    "categorie", "unite", "valeur_indicateur"
                ]].copy()
                editable_df.columns = ["ID", "Code", "Indicateur", "Catégorie", "Unité", "Valeur"]

                edited = st.data_editor(
                    editable_df,
                    use_container_width=True, hide_index=True,
                    disabled=["ID", "Code", "Indicateur", "Catégorie", "Unité"],
                    column_config={
                        "ID": None,
                        "Valeur": st.column_config.NumberColumn("Valeur", format="%.2f", min_value=0),
                    },
                    key=f"edit_ind_{lot['lot_id']}",
                )
            else:
                editable_df = df[[
                    "id_staging", "code_type", "libelle_reclamation", "valeur_brute"
                ]].copy()
                editable_df.columns = ["ID", "Code", "Type", "Valeur"]

                edited = st.data_editor(
                    editable_df,
                    use_container_width=True, hide_index=True,
                    disabled=["ID", "Code", "Type"],
                    column_config={
                        "ID": None,
                        "Valeur": st.column_config.NumberColumn("Valeur", format="%.2f", min_value=0),
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
                            code_element = (original.get("code_indicateur")
                                            if data_type == "indicateurs"
                                            else original.get("code_type"))
                            libelle_element = (original.get("libelle_indicateur")
                                               if data_type == "indicateurs"
                                               else original.get("libelle_reclamation"))

                            if data_type == "indicateurs":
                                # Utiliser la fonction avec historique
                                update_staging_record_with_history(
                                    "indicateurs", original["id_staging"],
                                    {"valeur_indicateur": float(row["Valeur"])},
                                    lot_id=lot["lot_id"],
                                    code_element=code_element,
                                    libelle_element=libelle_element,
                                    motif_rejet=motif,
                                    user_id=user["id"],
                                    role=role,
                                )
                            else:
                                update_staging_record_with_history(
                                    "reclamations", original["id_staging"],
                                    {
                                        "nombre_reclamations": int(row["Valeur"]),
                                        "valeur_brute": float(row["Valeur"])
                                    },
                                    lot_id=lot["lot_id"],
                                    code_element=code_element,
                                    libelle_element=libelle_element,
                                    motif_rejet=motif,
                                    user_id=user["id"],
                                    role=role,
                                )

                        submit_lot(data_type, lot["lot_id"], user["id"])
                        AuthManager.log_action(
                            user["id"], "CORRECTION_RESOUMISSION",
                            f"staging_{data_type}_dp",
                            details={"lot_id": lot["lot_id"], "role": role}
                        )
                        st.success("Corrections enregistrées et lot resoumis. Historique conservé.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {e}")
                st.markdown('</div>', unsafe_allow_html=True)

            with bc2:
                if st.button("Remettre en brouillon",
                             key=f"draft_{data_type}_{lot['lot_id']}",
                             use_container_width=True):
                    reset_lot_for_correction(data_type, lot["lot_id"])
                    st.info("Lot remis en brouillon.")
                    st.rerun()


def _render_history(data_type, id_province):
    """Historique complet avec traçabilité des corrections."""
    st.markdown(render_section_open("Historique des saisies", "ARCHIVE"),
                unsafe_allow_html=True)

    f_st = st.selectbox(
        "Filtrer par statut",
        ["Tous", "brouillon", "soumis", "valide_dp",
         "rejete_dp", "valide_regional", "rejete_regional"],
        format_func=lambda x: "Tous les statuts" if x == "Tous" else STATUS_LABELS.get(x, x),
        key="hi_s"
    )

    lots = get_staging_lots(
        id_province=id_province,
        statut=f_st if f_st != "Tous" else None,
        data_type=data_type,
    )

    if lots:
        rows = []
        for l in lots:
            corrections = get_lot_corrections(l["lot_id"])
            nb_corrections = len(corrections) if corrections else 0

            rows.append({
                "Lot": l["lot_id"][-15:],
                "Année": l["annee"],
                "Mois": get_mois_name(l["mois"]),
                "Statut": STATUS_LABELS.get(l["statut"], l["statut"]),
                "Enreg.": l["nb_enregistrements"],
                "Corrections": nb_corrections,
                "Créé le": format_datetime(l.get("date_creation")),
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("---")
        lot_opts = {
            f"{l['lot_id'][-15:]}... — {get_mois_name(l['mois'])} {l['annee']} "
            f"({STATUS_LABELS.get(l['statut'], l['statut'])})": l
            for l in lots
        }
        sel = st.selectbox(
            "Voir les détails d'un lot",
            ["—"] + list(lot_opts.keys()),
            key="det_h"
        )

        if sel != "—":
            lot = lot_opts[sel]
            st.markdown(
                f"**Statut :** {get_status_badge(lot['statut'])}",
                unsafe_allow_html=True
            )

            # ── Données du lot ──
            if data_type == "indicateurs":
                details = get_staging_indicateurs(lot_id=lot["lot_id"])
            else:
                details = get_staging_reclamations(lot_id=lot["lot_id"])

            if details:
                st.markdown("#### Données actuelles")
                df_d = pd.DataFrame(details)
                if data_type == "indicateurs":
                    cols_source = ["code_indicateur", "libelle_indicateur",
                                   "categorie", "unite", "valeur_indicateur"]
                    available = [c for c in cols_source if c in df_d.columns]
                    df_show = df_d[available].copy()
                    df_show = df_show.rename(columns={
                        "code_indicateur": "Code",
                        "libelle_indicateur": "Indicateur",
                        "categorie": "Catégorie",
                        "unite": "Unité",
                        "valeur_indicateur": "Valeur",
                    })
                else:
                    cols_source = ["code_type", "libelle_reclamation",
                                   "nombre_reclamations", "valeur_brute"]
                    available = [c for c in cols_source if c in df_d.columns]
                    df_show = df_d[available].copy()
                    df_show = df_show.rename(columns={
                        "code_type": "Code",
                        "libelle_reclamation": "Type",
                        "nombre_reclamations": "Nombre",
                        "valeur_brute": "Valeur",
                    })

                st.dataframe(df_show, use_container_width=True, hide_index=True)

            # ── Motif de rejet si applicable ──
            if lot["statut"] in ["rejete_dp", "rejete_regional"] and details:
                cm = (details[0].get("commentaire_dp") or
                      details[0].get("commentaire_regional"))
                if cm:
                    st.markdown(render_notice(
                        f"Motif du rejet : {cm}", "warning"
                    ), unsafe_allow_html=True)

            # ── Historique des corrections ──
            corrections = get_lot_corrections(lot["lot_id"])
            if corrections:
                st.markdown("---")
                st.markdown("#### Historique des corrections")
                st.markdown(render_notice(
                    f"Ce lot a été corrigé <strong>{len(corrections)}</strong> fois. "
                    f"Voici le détail des modifications :",
                    "info"
                ), unsafe_allow_html=True)

                # Tableau des corrections
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
                    })

                df_corr = pd.DataFrame(corr_rows)
                st.dataframe(df_corr, use_container_width=True, hide_index=True)

                # Statistique unique : Total corrections
                st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
                col_s1, _, _ = st.columns([1, 1, 2])
                with col_s1:
                    st.metric("Total corrections", len(corrections))
    else:
        st.markdown(render_empty("INBOX", "Aucun lot trouvé"),
                    unsafe_allow_html=True)

    st.markdown(render_section_close(), unsafe_allow_html=True)