# views/page_validation_regionale.py
"""
Validation régionale - Admin régional voit UNIQUEMENT :
- Lots validés par admin DP (statut = valide_dp) : à valider
- Lots validés définitivement (statut = valide_regional) : archivés
- Lots rejetés au régional (statut = rejete_regional)

L'admin régional peut aussi consulter l'historique des corrections
pour voir les modifications faites après un rejet.
"""
import streamlit as st
import pandas as pd
from auth.session_manager import SessionManager
from auth.authentication import AuthManager
from db.queries import (
    get_staging_lots, get_staging_indicateurs, get_staging_reclamations,
    update_staging_status, get_lot_corrections
)
from config.provinces import PROVINCES
from utils.helpers import format_datetime, get_mois_name, MOIS_FR
from utils.styles import (
    render_page_header, render_notice, render_empty,
    render_section_open, render_section_close, render_metric,
    render_lot_detail_card, render_action_bar, render_prov_card,
    STATUS_LABELS
)


def render_validation_regionale():
    SessionManager.require_role(["admin_regional", "super_admin"])
    user = SessionManager.get_user()

    st.markdown(
        render_page_header("Validation régionale",
                           "Siège Agadir — Données validées par les admins DP"),
        unsafe_allow_html=True,
    )

    st.markdown(render_notice(
        "Vous voyez uniquement les données <strong>déjà validées par les admins DP</strong> "
        "des 6 provinces. L'historique des corrections effectuées est disponible pour chaque lot.",
        "info"
    ), unsafe_allow_html=True)

    # Récupérer les lots avec filtrage strict
    all_indic = get_staging_lots(data_type="indicateurs") or []
    all_reclam = get_staging_lots(data_type="reclamations") or []

    allowed_statuts = ["valide_dp", "valide_regional", "rejete_regional"]
    all_indic = [l for l in all_indic if l["statut"] in allowed_statuts]
    all_reclam = [l for l in all_reclam if l["statut"] in allowed_statuts]

    indic_pending = [l for l in all_indic if l["statut"] == "valide_dp"]
    reclam_pending = [l for l in all_reclam if l["statut"] == "valide_dp"]
    indic_valides = [l for l in all_indic if l["statut"] == "valide_regional"]
    reclam_valides = [l for l in all_reclam if l["statut"] == "valide_regional"]
    indic_rej = [l for l in all_indic if l["statut"] == "rejete_regional"]
    reclam_rej = [l for l in all_reclam if l["statut"] == "rejete_regional"]

    # Métriques
    c1, c2, c3, c4 = st.columns(4, gap="small")
    with c1:
        st.markdown(render_metric("Indic. à valider", len(indic_pending), "CLOCK",
                                   sub="Validés par les DP"), unsafe_allow_html=True)
    with c2:
        st.markdown(render_metric("Réc. à valider", len(reclam_pending), "CLOCK",
                                   sub="Validées par les DP"), unsafe_allow_html=True)
    with c3:
        st.markdown(render_metric("Validés définitivement",
                                   len(indic_valides) + len(reclam_valides),
                                   "CHECK_CIRCLE",
                                   sub=f"Ind: {len(indic_valides)} · Réc: {len(reclam_valides)}"),
                    unsafe_allow_html=True)
    with c4:
        st.markdown(render_metric("Rejetés par vous",
                                   len(indic_rej) + len(reclam_rej), "X",
                                   sub="Retournés aux DP"), unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # Vue par province
    st.markdown(render_section_open(
        "Vue d'ensemble par province", "MAP_PIN",
        "Statistiques des données ayant passé la validation DP"
    ), unsafe_allow_html=True)

    cols = st.columns(3, gap="small")
    for idx, (pid, pinfo) in enumerate(PROVINCES.items()):
        prov_i = [l for l in all_indic if l["id_province"] == pid]
        prov_r = [l for l in all_reclam if l["id_province"] == pid]

        pending = len([l for l in prov_i if l["statut"] == "valide_dp"]) + \
                  len([l for l in prov_r if l["statut"] == "valide_dp"])
        valides = len([l for l in prov_i if l["statut"] == "valide_regional"]) + \
                  len([l for l in prov_r if l["statut"] == "valide_regional"])
        rejetes = len([l for l in prov_i if l["statut"] == "rejete_regional"]) + \
                  len([l for l in prov_r if l["statut"] == "rejete_regional"])
        total = len(prov_i) + len(prov_r)

        with cols[idx % 3]:
            st.markdown(render_prov_card(pinfo["nom"], total, pending, valides, rejetes),
                        unsafe_allow_html=True)

    st.markdown(render_section_close(), unsafe_allow_html=True)

    # Onglets
    tab_queue, tab_valides = st.tabs([
        f"File d'attente ({len(indic_pending) + len(reclam_pending)})",
        f"Validés définitivement ({len(indic_valides) + len(reclam_valides)})"
    ])

    with tab_queue:
        _render_regional_queue(user, indic_pending, reclam_pending)

    with tab_valides:
        _render_valides_history(indic_valides, reclam_valides)


def _render_regional_queue(user, indic_pending, reclam_pending):
    st.markdown(render_notice(
        "Validez ou rejetez les lots. Les données validées définitivement seront prêtes "
        "pour être transférées dans le Data Warehouse par le pipeline ETL."
    ), unsafe_allow_html=True)

    sub_i, sub_r = st.tabs([
        f"Indicateurs ({len(indic_pending)})",
        f"Réclamations ({len(reclam_pending)})"
    ])

    with sub_i:
        _render_regional_batch("indicateurs", user, indic_pending)
    with sub_r:
        _render_regional_batch("reclamations", user, reclam_pending)


def _render_regional_batch(data_type, user, lots):
    if not lots:
        st.markdown(render_empty("CHECK_CIRCLE", "File d'attente vide",
                                  "Aucun lot en attente de validation régionale"),
                    unsafe_allow_html=True)
        return

    # Enrichir les lots
    lots_enr = []
    for lot in lots:
        if data_type == "indicateurs":
            details = get_staging_indicateurs(lot_id=lot["lot_id"])
        else:
            details = get_staging_reclamations(lot_id=lot["lot_id"])
        if details:
            first = details[0]
            lots_enr.append({
                "lot_id": lot["lot_id"],
                "id_province": lot["id_province"],
                "province": lot["nom_province"],
                "centre": first.get("nom_centre", "—"),
                "agent": first.get("soumis_par_nom", "—"),
                "valide_par": first.get("valide_dp_par_nom", "—"),
                "date_soum": format_datetime(first.get("date_soumission")),
                "date_val_dp": format_datetime(first.get("date_validation_dp")),
                "commentaire_dp": first.get("commentaire_dp", ""),
                "annee": lot["annee"],
                "mois_num": lot["mois"],
                "nb": lot["nb_enregistrements"],
                "details": details,
            })

    # Filtres
    st.markdown(render_section_open("Filtres", "FILTER"), unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    with f1:
        prov_opts = [("Toutes", "Toutes les provinces")] + \
                    [(pid, p["nom"]) for pid, p in PROVINCES.items()]
        f_prov = st.selectbox("Province", prov_opts,
                               format_func=lambda x: x[1] if isinstance(x, tuple) else x,
                               key=f"fp_{data_type}")
    with f2:
        annees = sorted(set(l["annee"] for l in lots_enr), reverse=True)
        f_annee = st.selectbox("Année", ["Toutes"] + annees, key=f"fa_{data_type}")
    with f3:
        mois_dispo = sorted(set(l["mois_num"] for l in lots_enr))
        f_mois = st.selectbox("Mois", ["Tous"] + mois_dispo,
                               format_func=lambda x: "Tous" if x == "Tous" else MOIS_FR[x],
                               key=f"fm_{data_type}")
    st.markdown(render_section_close(), unsafe_allow_html=True)

    prov_id = f_prov[0] if isinstance(f_prov, tuple) and f_prov[0] != "Toutes" else None
    filtered = [l for l in lots_enr
                if (prov_id is None or l["id_province"] == prov_id)
                and (f_annee == "Toutes" or l["annee"] == f_annee)
                and (f_mois == "Tous" or l["mois_num"] == f_mois)]

    st.markdown(f"<div style='color:#6B7280;font-size:0.85rem;margin:0.5rem 0;'>"
                f"<strong style='color:#111827;'>{len(filtered)}</strong> lot(s) affiché(s)</div>",
                unsafe_allow_html=True)

    if not filtered:
        st.markdown(render_empty("FILTER", "Aucun lot", "Modifiez les filtres"),
                    unsafe_allow_html=True)
        return

    # Sélection multiple
    st.markdown(render_section_open("Sélection multiple", "LAYERS"),
                unsafe_allow_html=True)

    sel_key = f"selr_{data_type}"
    if sel_key not in st.session_state:
        st.session_state[sel_key] = set()

    tc1, tc2 = st.columns([1, 5])
    with tc1:
        if st.button("Tout sélectionner", key=f"selall_r_{data_type}",
                     use_container_width=True):
            st.session_state[sel_key] = set(l["lot_id"] for l in filtered)
            st.rerun()
    with tc2:
        if st.button("Tout désélectionner", key=f"unsel_r_{data_type}"):
            st.session_state[sel_key] = set()
            st.rerun()

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # Enrichir les lignes avec le nombre de corrections
    rows_data = []
    for lot in filtered:
        corrections = get_lot_corrections(lot["lot_id"])
        nb_corr = len(corrections) if corrections else 0

        rows_data.append({
            "✓": lot["lot_id"] in st.session_state[sel_key],
            "Province": lot["province"],
            "Centre": lot["centre"],
            "Agent": lot["agent"],
            "Validé DP par": lot["valide_par"],
            "Période": f"{get_mois_name(lot['mois_num'])[:3]} {lot['annee']}",
            "Enreg.": lot["nb"],
            "Corrections": nb_corr,
            "Date val. DP": lot["date_val_dp"],
        })

    df_display = pd.DataFrame(rows_data)
    edited = st.data_editor(
        df_display, use_container_width=True, hide_index=True,
        disabled=["Province", "Centre", "Agent", "Validé DP par",
                  "Période", "Enreg.", "Corrections", "Date val. DP"],
        column_config={"✓": st.column_config.CheckboxColumn("Sél.", width="small")},
        key=f"editorR_{data_type}",
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
                                     key=f"cmtr_{data_type}", height=80)

        ac1, ac2, _ = st.columns([1.5, 1.2, 3])
        with ac1:
            st.markdown('<div class="btn-success">', unsafe_allow_html=True)
            if st.button(f"Valider définitivement ({nb_sel})",
                         key=f"vallr_{data_type}", use_container_width=True):
                errors = []
                for lid in selected_ids:
                    try:
                        update_staging_status(data_type, lid, "valide_regional",
                                              user["id"], comment_mass, "regional")
                        AuthManager.log_action(user["id"],
                                                f"VALIDATION_REG_{data_type.upper()}",
                                                f"staging_{data_type}_dp",
                                                details={"lot_id": lid})
                    except Exception as e:
                        errors.append(f"{lid[-12:]}: {str(e)[:50]}")

                st.session_state[sel_key] = set()
                if errors:
                    st.error(f"Erreurs : {len(errors)}\n" + "\n".join(errors))
                else:
                    st.success(
                        f"{nb_sel} lot(s) validé(s) définitivement. "
                        f"Prêts pour le pipeline ETL."
                    )
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with ac2:
            st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
            if st.button(f"Rejeter ({nb_sel})", key=f"rallr_{data_type}",
                         use_container_width=True):
                if not comment_mass:
                    st.error("Commentaire obligatoire pour un rejet.")
                else:
                    for lid in selected_ids:
                        update_staging_status(data_type, lid, "rejete_regional",
                                              user["id"], comment_mass, "regional")
                    st.session_state[sel_key] = set()
                    st.warning(f"{nb_sel} lot(s) rejeté(s), renvoyés aux DP.")
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════
    # INSPECTION D'UN LOT (avec historique des corrections)
    # ═══════════════════════════════════════════════════════════
    st.markdown(render_section_open("Inspection d'un lot", "EYE"),
                unsafe_allow_html=True)

    opts = {f"[{l['province']}] {l['centre']} — {get_mois_name(l['mois_num'])} {l['annee']} "
            f"({l['nb']} enreg.)": l for l in filtered}
    sel = st.selectbox("Choisir un lot", ["— Sélectionner —"] + list(opts.keys()),
                        key=f"insr_{data_type}")

    if sel != "— Sélectionner —":
        lot = opts[sel]

        # Carte détails du lot
        st.markdown(render_lot_detail_card({
            "lot_id": lot["lot_id"], "agent": lot["agent"], "centre": lot["centre"],
            "mois": get_mois_name(lot["mois_num"]), "annee": lot["annee"],
            "nb": lot["nb"], "date_soum": lot["date_soum"],
        }, extra_info={
            "Province": lot["province"],
            "Validé DP par": lot["valide_par"],
            "Date validation DP": lot["date_val_dp"],
        }), unsafe_allow_html=True)

        # Commentaire de l'admin DP
        if lot["commentaire_dp"]:
            st.markdown(render_notice(
                f"Commentaire de l'Admin DP : {lot['commentaire_dp']}", "info"
            ), unsafe_allow_html=True)

        # ── Données actuelles ──
        st.markdown("#### Données actuelles")
        df = pd.DataFrame(lot["details"])

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
                           "nombre_reclamations", "valeur_brute"]
            available = [c for c in cols_source if c in df.columns]
            df_show = df[available].copy()
            df_show = df_show.rename(columns={
                "code_type": "Code",
                "libelle_reclamation": "Type",
                "nombre_reclamations": "Nombre",
                "valeur_brute": "Valeur",
            })

        st.dataframe(df_show, use_container_width=True, hide_index=True)

        # ═══════════════════════════════════════════════════
        # HISTORIQUE DES CORRECTIONS
        # ═══════════════════════════════════════════════════
        corrections = get_lot_corrections(lot["lot_id"])
        if corrections:
            st.markdown("---")
            st.markdown("#### Historique des corrections")
            st.markdown(render_notice(
                f"Ce lot a été corrigé <strong>{len(corrections)}</strong> fois "
                f"avant d'arriver à vous. Voici le détail des modifications :",
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
                })

            df_corr = pd.DataFrame(corr_rows)
            st.dataframe(df_corr, use_container_width=True, hide_index=True)

            # Statistique
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            col_s1, _, _ = st.columns([1, 1, 2])
            with col_s1:
                st.metric("Total corrections", len(corrections))
        else:
            st.markdown(render_notice(
                "Aucune correction n'a été effectuée sur ce lot.",
                "info"
            ), unsafe_allow_html=True)

    st.markdown(render_section_close(), unsafe_allow_html=True)


def _render_valides_history(indic_valides, reclam_valides):
    """Historique des lots validés définitivement avec possibilité d'inspection."""
    st.markdown(render_notice(
        "Données validées définitivement et prêtes pour le transfert vers le Data Warehouse "
        "par le pipeline ETL. L'historique des corrections reste consultable.",
        "success"
    ), unsafe_allow_html=True)

    tab_i, tab_r = st.tabs([
        f"Indicateurs ({len(indic_valides)})",
        f"Réclamations ({len(reclam_valides)})"
    ])

    with tab_i:
        _render_valides_table_with_details(indic_valides, "indicateurs", "i")
    with tab_r:
        _render_valides_table_with_details(reclam_valides, "reclamations", "r")


def _render_valides_table_with_details(lots, data_type, key):
    """Affiche les lots validés avec possibilité d'inspection détaillée."""
    if not lots:
        st.markdown(render_empty("CHECK_CIRCLE", "Aucune donnée validée"),
                    unsafe_allow_html=True)
        return

    # Filtre province
    prov_opts = ["Toutes"] + [(pid, p["nom"]) for pid, p in PROVINCES.items()]
    f_prov = st.selectbox("Filtrer par province", prov_opts,
                           format_func=lambda x: x if x == "Toutes" else x[1],
                           key=f"val_p_{key}")

    filtered = lots
    if isinstance(f_prov, tuple) and f_prov[0] != "Toutes":
        filtered = [l for l in lots if l["id_province"] == f_prov[0]]

    if not filtered:
        st.info("Aucune donnée pour cette province.")
        return

    # Enrichir avec nb corrections
    rows = []
    for lot in filtered:
        corrections = get_lot_corrections(lot["lot_id"])
        nb_corr = len(corrections) if corrections else 0
        rows.append({
            "Province": lot.get("nom_province", "—"),
            "Année": lot.get("annee", "—"),
            "Mois": get_mois_name(lot.get("mois", 0)) if lot.get("mois") else "—",
            "Enreg.": lot.get("nb_enregistrements", 0),
            "Corrections": nb_corr,
            "Validé le": format_datetime(lot.get("date_modification")),
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # ═══════════════════════════════════════════════════
    # INSPECTION DÉTAILLÉE (données + historique)
    # ═══════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("#### Inspection détaillée d'un lot validé")

    # Enrichir les lots pour le dropdown
    lots_enr = []
    for lot in filtered:
        if data_type == "indicateurs":
            details = get_staging_indicateurs(lot_id=lot["lot_id"])
        else:
            details = get_staging_reclamations(lot_id=lot["lot_id"])
        if details:
            first = details[0]
            lots_enr.append({
                "lot_id": lot["lot_id"],
                "province": lot.get("nom_province", "—"),
                "centre": first.get("nom_centre", "—"),
                "agent": first.get("soumis_par_nom", "—"),
                "valide_dp_par": first.get("valide_dp_par_nom", "—"),
                "valide_reg_par": first.get("valide_reg_par_nom", "—"),
                "date_soum": format_datetime(first.get("date_soumission")),
                "date_val_dp": format_datetime(first.get("date_validation_dp")),
                "date_val_reg": format_datetime(first.get("date_validation_reg")),
                "commentaire_dp": first.get("commentaire_dp", ""),
                "commentaire_reg": first.get("commentaire_regional", ""),
                "annee": lot.get("annee"),
                "mois_num": lot.get("mois"),
                "nb": lot.get("nb_enregistrements", 0),
                "details": details,
            })

    opts = {
        f"[{l['province']}] {l['centre']} — "
        f"{get_mois_name(l['mois_num']) if l['mois_num'] else '—'} {l['annee']} "
        f"({l['nb']} enreg.)": l for l in lots_enr
    }
    sel = st.selectbox("Choisir un lot pour voir les détails",
                        ["— Sélectionner —"] + list(opts.keys()),
                        key=f"insp_val_{key}")

    if sel != "— Sélectionner —":
        lot = opts[sel]

        # Carte détails
        st.markdown(render_lot_detail_card({
            "lot_id": lot["lot_id"],
            "agent": lot["agent"],
            "centre": lot["centre"],
            "mois": get_mois_name(lot["mois_num"]) if lot["mois_num"] else "—",
            "annee": lot["annee"],
            "nb": lot["nb"],
            "date_soum": lot["date_soum"],
        }, extra_info={
            "Province": lot["province"],
            "Validé DP par": lot["valide_dp_par"],
            "Date validation DP": lot["date_val_dp"],
            "Validé régional par": lot["valide_reg_par"],
            "Date validation régionale": lot["date_val_reg"],
        }), unsafe_allow_html=True)

        # Commentaires
        if lot["commentaire_dp"]:
            st.markdown(render_notice(
                f"Commentaire Admin DP : {lot['commentaire_dp']}", "info"
            ), unsafe_allow_html=True)

        if lot["commentaire_reg"]:
            st.markdown(render_notice(
                f"Votre commentaire (régional) : {lot['commentaire_reg']}", "success"
            ), unsafe_allow_html=True)

        # ── Données ──
        st.markdown("#### Données validées")
        df = pd.DataFrame(lot["details"])

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
                           "nombre_reclamations", "valeur_brute"]
            available = [c for c in cols_source if c in df.columns]
            df_show = df[available].copy()
            df_show = df_show.rename(columns={
                "code_type": "Code",
                "libelle_reclamation": "Type",
                "nombre_reclamations": "Nombre",
                "valeur_brute": "Valeur",
            })

        st.dataframe(df_show, use_container_width=True, hide_index=True)

        # ── Historique des corrections ──
        corrections = get_lot_corrections(lot["lot_id"])
        if corrections:
            st.markdown("---")
            st.markdown("#### Historique des corrections")
            st.markdown(render_notice(
                f"Ce lot a été corrigé <strong>{len(corrections)}</strong> fois "
                f"avant sa validation définitive.",
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
                })

            df_corr = pd.DataFrame(corr_rows)
            st.dataframe(df_corr, use_container_width=True, hide_index=True)

            # Statistique
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            col_s1, _, _ = st.columns([1, 1, 2])
            with col_s1:
                st.metric("Total corrections", len(corrections))
        else:
            st.markdown(render_notice(
                "Aucune correction n'a été effectuée sur ce lot.",
                "info"
            ), unsafe_allow_html=True)