# views/page_reclamations.py
import streamlit as st
import pandas as pd
from datetime import datetime
from auth.session_manager import SessionManager
from auth.authentication import AuthManager
from db.queries import (
    get_types_reclamation, insert_staging_reclamations,
    get_staging_reclamations, submit_lot, get_staging_lots,
    get_rejected_lots, get_draft_lots
)
from config.provinces import get_province_name, get_centres_for_province
from utils.helpers import generate_lot_id, get_current_period, MOIS_FR, get_mois_name, format_datetime
from utils.styles import (
    render_page_header, render_notice, render_empty,
    render_section_open, render_section_close,
    render_form_category, get_status_badge, STATUS_LABELS
)


def render_reclamations():
    SessionManager.require_role(["agent_dp", "admin_dp", "super_admin"])
    user = SessionManager.get_user()
    id_province = user["id_province"]
    code_province = user["code_province"]
    province_name = get_province_name(id_province)
    role = user["role"]

    st.markdown(
        render_page_header("Réclamations DP", f"Province de {province_name}"),
        unsafe_allow_html=True,
    )

    drafts = get_draft_lots(id_province, "reclamations") or []
    rejected = get_rejected_lots(id_province, "reclamations") or []

    if rejected:
        who = "Vos" if role == "agent_dp" else "Les"
        st.markdown(render_notice(
            f"{who} lot(s) de réclamations rejeté(s) : <strong>{len(rejected)}</strong>. "
            f"Consultez l'onglet « Lots rejetés » pour corriger.",
            "warning"
        ), unsafe_allow_html=True)

    if drafts:
        st.markdown(render_notice(
            f"Vous avez <strong>{len(drafts)}</strong> brouillon(s) de réclamations non soumis.",
            "info"
        ), unsafe_allow_html=True)

    tab_new, tab_drafts, tab_rejected, tab_hist = st.tabs([
        "Nouvelle saisie",
        f"Brouillons ({len(drafts)})",
        f"Lots rejetés ({len(rejected)})",
        "Historique"
    ])

    with tab_new:
        _render_new_reclamation(user, id_province, code_province, province_name)

    with tab_drafts:
        from views.page_indicateurs import render_draft_lots
        render_draft_lots("reclamations", id_province, user, drafts)

    with tab_rejected:
        from views.page_indicateurs import render_rejected_lots
        render_rejected_lots("reclamations", id_province, user, rejected)

    with tab_hist:
        _render_reclam_history(id_province)


def _render_new_reclamation(user, id_province, code_province, province_name):
    """Formulaire simplifié avec un seul champ Valeur par type.
    
    Pour Reclamation_Divers : champs personnalisés Nom + Valeur."""

    st.markdown(render_notice(
        "Saisissez la valeur pour chaque type de réclamation. "
        "Pour la catégorie « Réclamation Divers », vous pouvez ajouter des réclamations personnalisées."
    ), unsafe_allow_html=True)

    # ── Période et centre ──
    st.markdown(render_section_open("Période et centre", "CALENDAR"), unsafe_allow_html=True)

    cy, cm = get_current_period()
    c1, c2, c3 = st.columns(3)
    with c1:
        annee = st.selectbox("Année", list(range(cy, cy - 3, -1)), key="r_a")
    with c2:
        mois = st.selectbox("Mois", list(range(1, 13)), format_func=lambda x: MOIS_FR[x],
                            index=max(0, cm - 2), key="r_m")
    with c3:
        centres = get_centres_for_province(id_province)
        cmap = {c["nom"]: c for c in centres}
        cn = st.selectbox("Centre", list(cmap.keys()), key="r_c")
        centre = cmap[cn]

    st.markdown(render_section_close(), unsafe_allow_html=True)

    # ── Types de réclamations ──
    types = get_types_reclamation()
    if not types:
        st.warning("Aucun type de réclamation configuré.")
        return

    cats = {}
    for t in types:
        cats.setdefault(t["categorie_reclamation"] or "Autres", []).append(t)

    st.markdown(render_section_open("Saisie des réclamations", "EDIT"), unsafe_allow_html=True)

    # ── Gestion dynamique des réclamations personnalisées (hors formulaire) ──
    if "nb_custom_reclams" not in st.session_state:
        st.session_state["nb_custom_reclams"] = 1

    # Boutons ajouter/retirer (HORS du formulaire)
    col_btn1, col_btn2, col_space = st.columns([2, 2, 5])
    with col_btn1:
        if st.button("Ajouter une réclamation divers", use_container_width=True,
                     key="btn_add_custom"):
            st.session_state["nb_custom_reclams"] += 1
            st.rerun()
    with col_btn2:
        if st.session_state["nb_custom_reclams"] > 1:
            if st.button("Retirer la dernière", use_container_width=True,
                         key="btn_remove_custom"):
                st.session_state["nb_custom_reclams"] -= 1
                st.rerun()

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # ── Formulaire principal ──
    with st.form("form_rec", clear_on_submit=False):
        vals = {}
        custom_reclams = []

        for cat_name, recs in cats.items():
            st.markdown(render_form_category("FOLDER", cat_name), unsafe_allow_html=True)

            # En-tête
            hc1, hc2 = st.columns([6, 3])
            with hc1:
                st.markdown(
                    "<div style='font-weight:600;font-size:0.8rem;color:#6B7280;'>"
                    "TYPE DE RÉCLAMATION</div>",
                    unsafe_allow_html=True
                )
            with hc2:
                st.markdown(
                    "<div style='font-weight:600;font-size:0.8rem;color:#6B7280;text-align:left;'>"
                    "VALEUR</div>",
                    unsafe_allow_html=True
                )

            # ── Types standards ──
            for rec in recs:
                col_label, col_val = st.columns([6, 3])
                with col_label:
                    st.markdown(
                        f"<div style='padding-top:0.5rem;'>"
                        f"<strong>{rec['libelle_reclamation']}</strong>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                with col_val:
                    val = st.number_input(
                        f"Val {rec['code_type']}",
                        min_value=0.0,
                        value=0.0,
                        step=0.01,
                        format="%.2f",
                        key=f"val_{rec['code_type']}",
                        label_visibility="collapsed",
                    )

                vals[rec["code_type"]] = {
                    "valeur": val,
                    "lib": rec["libelle_reclamation"],
                    "cat": cat_name,
                }

            # ── Section personnalisée pour Reclamation_Divers ──
            if "divers" in cat_name.lower():
                st.markdown(
                    "<div style='background:#F0F9FF;padding:0.75rem;border-left:3px solid #0EA5E9;"
                    "border-radius:4px;margin:0.75rem 0 0.5rem;'>"
                    "<div style='font-weight:600;color:#0369A1;font-size:0.85rem;'>"
                    "Réclamations personnalisées</div>"
                    "<div style='font-size:0.78rem;color:#075985;margin-top:0.15rem;'>"
                    "Ajoutez ci-dessous d'autres types de réclamations non listés."
                    "</div></div>",
                    unsafe_allow_html=True
                )

                # En-tête personnalisé
                hc1, hc2 = st.columns([6, 3])
                with hc1:
                    st.markdown(
                        "<div style='font-weight:600;font-size:0.8rem;color:#6B7280;'>"
                        "NOM DE LA RÉCLAMATION</div>",
                        unsafe_allow_html=True
                    )
                with hc2:
                    st.markdown(
                        "<div style='font-weight:600;font-size:0.8rem;color:#6B7280;'>"
                        "VALEUR</div>",
                        unsafe_allow_html=True
                    )

                # Champs dynamiques
                for i in range(st.session_state["nb_custom_reclams"]):
                    col_nom, col_val = st.columns([6, 3])
                    with col_nom:
                        nom_custom = st.text_input(
                            f"Nom réclamation {i+1}",
                            placeholder=f"Ex: Réclamation particulière #{i+1}",
                            key=f"custom_nom_{i}",
                            label_visibility="collapsed",
                        )
                    with col_val:
                        val_custom = st.number_input(
                            f"Valeur custom {i+1}",
                            min_value=0.0,
                            value=0.0,
                            step=0.01,
                            format="%.2f",
                            key=f"custom_val_{i}",
                            label_visibility="collapsed",
                        )

                    # Collecter uniquement si nom ET valeur sont remplis
                    if nom_custom and nom_custom.strip() and val_custom > 0:
                        custom_reclams.append({
                            "nom": nom_custom.strip(),
                            "valeur": val_custom,
                            "cat": cat_name,
                        })

        # ── Boutons d'action ──
        st.markdown("---")
        b1, b2 = st.columns(2)
        with b1:
            draft = st.form_submit_button("Enregistrer brouillon", use_container_width=True)
        with b2:
            submit = st.form_submit_button("Soumettre pour validation",
                                            use_container_width=True, type="primary")

        if draft or submit:
            has_standard = any(v["valeur"] > 0 for v in vals.values())
            has_custom = len(custom_reclams) > 0

            if not has_standard and not has_custom:
                st.error("Saisissez au moins une réclamation.")
            else:
                lot_id = generate_lot_id(code_province, "RECLAM")
                status = "brouillon" if draft else "soumis"
                records = []

                # ── Réclamations standards ──
                for code, v in vals.items():
                    if v["valeur"] > 0:
                        records.append((
                            id_province,
                            province_name,
                            centre["id"],
                            centre["nom"],
                            annee,
                            mois,
                            code,
                            v["lib"],
                            v["cat"],
                            int(v["valeur"]),     # nombre_reclamations
                            0.0,                  # temps_moyen_coupure_h
                            0.0,                  # delai_moyen_traitement_j
                            v["valeur"],           # valeur_brute
                            status,
                            user["id"],
                            datetime.now() if submit else None,
                            lot_id,
                        ))

                # ── Réclamations personnalisées (Divers) ──
                for idx, cr in enumerate(custom_reclams):
                    code_custom = f"DIVERS_CUSTOM_{idx+1}"
                    records.append((
                        id_province,
                        province_name,
                        centre["id"],
                        centre["nom"],
                        annee,
                        mois,
                        code_custom,
                        cr["nom"],          # libelle_reclamation = nom saisi
                        cr["cat"],
                        int(cr["valeur"]),   # nombre_reclamations
                        0.0,                 # temps_moyen_coupure_h
                        0.0,                 # delai_moyen_traitement_j
                        cr["valeur"],        # valeur_brute
                        status,
                        user["id"],
                        datetime.now() if submit else None,
                        lot_id,
                    ))

                try:
                    insert_staging_reclamations(records)
                    AuthManager.log_action(
                        user["id"],
                        "SAISIE_RECLAMATIONS" if draft else "SOUMISSION_RECLAMATIONS",
                        "staging_reclamations_dp",
                        details={
                            "lot_id": lot_id,
                            "nb": len(records),
                            "nb_custom": len(custom_reclams),
                        },
                    )
                    if draft:
                        st.success(
                            f"Brouillon enregistré — {len(records)} réclamation(s) "
                            f"(dont {len(custom_reclams)} personnalisée(s)). "
                            f"Modifiez dans l'onglet « Brouillons »."
                        )
                    else:
                        st.success(
                            f"Soumis pour validation — {len(records)} réclamation(s) "
                            f"(dont {len(custom_reclams)} personnalisée(s))."
                        )

                    # Reset des réclamations personnalisées
                    st.session_state["nb_custom_reclams"] = 1

                except Exception as e:
                    st.error(f"Erreur : {e}")

    st.markdown(render_section_close(), unsafe_allow_html=True)


def _render_reclam_history(id_province):
    """Historique avec traçabilité des corrections."""
    from db.queries import get_lot_corrections

    st.markdown(render_section_open("Historique des saisies", "ARCHIVE"),
                unsafe_allow_html=True)

    f_st = st.selectbox(
        "Filtrer par statut",
        ["Tous", "brouillon", "soumis", "valide_dp",
         "rejete_dp", "valide_regional", "rejete_regional"],
        format_func=lambda x: "Tous" if x == "Tous" else STATUS_LABELS.get(x, x),
        key="hr_s"
    )

    lots = get_staging_lots(
        id_province=id_province,
        statut=f_st if f_st != "Tous" else None,
        data_type="reclamations"
    )

    if lots:
        rows = []
        for l in lots:
            corrections = get_lot_corrections(l["lot_id"])
            nb_corr = len(corrections) if corrections else 0

            rows.append({
                "Lot": l["lot_id"][-15:],
                "Année": l["annee"],
                "Mois": get_mois_name(l["mois"]),
                "Statut": STATUS_LABELS.get(l["statut"], l["statut"]),
                "Enreg.": l["nb_enregistrements"],
                "Corrections": nb_corr,
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
        sel = st.selectbox("Détails d'un lot", ["—"] + list(lot_opts.keys()), key="det_rh")

        if sel != "—":
            lot = lot_opts[sel]
            st.markdown(
                f"**Statut :** {get_status_badge(lot['statut'])}",
                unsafe_allow_html=True
            )

            details = get_staging_reclamations(lot_id=lot["lot_id"])
            if details:
                st.markdown("#### Données actuelles")
                df_d = pd.DataFrame(details)
                cols = [c for c in ["code_type", "libelle_reclamation",
                                    "nombre_reclamations", "valeur_brute"]
                        if c in df_d.columns]
                df_show = df_d[cols].rename(columns={
                    "code_type": "Code",
                    "libelle_reclamation": "Type",
                    "nombre_reclamations": "Nombre",
                    "valeur_brute": "Valeur",
                })
                st.dataframe(df_show, use_container_width=True, hide_index=True)

            # Motif de rejet
            if lot["statut"] in ["rejete_dp", "rejete_regional"] and details:
                cm = (details[0].get("commentaire_dp") or
                      details[0].get("commentaire_regional"))
                if cm:
                    st.markdown(render_notice(
                        f"Motif du rejet : {cm}", "warning"
                    ), unsafe_allow_html=True)

            # Historique des corrections
            corrections = get_lot_corrections(lot["lot_id"])
            if corrections:
                st.markdown("---")
                st.markdown("#### Historique des corrections")
                st.markdown(render_notice(
                    f"Ce lot a été corrigé <strong>{len(corrections)}</strong> fois.",
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
                st.dataframe(pd.DataFrame(corr_rows),
                             use_container_width=True, hide_index=True)

                # Statistique unique : Total corrections
                st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
                col_s1, _, _ = st.columns([1, 1, 2])
                with col_s1:
                    st.metric("Total corrections", len(corrections))
    else:
        st.markdown(render_empty("INBOX", "Aucun lot trouvé"),
                    unsafe_allow_html=True)

    st.markdown(render_section_close(), unsafe_allow_html=True)