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
    st.markdown(render_notice(
        "Saisissez le nombre de réclamations par type. "
        "Vous pouvez enregistrer en brouillon pour continuer plus tard."
    ), unsafe_allow_html=True)

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

    types = get_types_reclamation()
    if not types:
        st.warning("Aucun type de réclamation configuré.")
        return

    cats = {}
    for t in types:
        cats.setdefault(t["categorie_reclamation"] or "Autres", []).append(t)

    st.markdown(render_section_open("Saisie des réclamations", "EDIT"), unsafe_allow_html=True)

    with st.form("form_rec", clear_on_submit=False):
        vals = {}
        for cat_name, recs in cats.items():
            st.markdown(render_form_category("FOLDER", cat_name), unsafe_allow_html=True)
            for rec in recs:
                col_label, col_nb, col_tmc, col_dmt, col_vb = st.columns([4, 1, 1, 1, 1])
                with col_label:
                    st.markdown(f"**{rec['libelle_reclamation']}**", unsafe_allow_html=True)
                with col_nb:
                    nb = st.number_input("Nombre", 0, value=0, step=1,
                                         key=f"nb_{rec['code_type']}")
                with col_tmc:
                    tmc = st.number_input("TMC (h)", 0.0, value=0.0, step=0.1,
                                          key=f"tmc_{rec['code_type']}",
                                          disabled=not rec.get("est_duree", True))
                with col_dmt:
                    dmt = st.number_input("DMT (j)", 0.0, value=0.0, step=0.1,
                                          key=f"dmt_{rec['code_type']}")
                with col_vb:
                    vb = st.number_input("Val. brute", 0.0, value=0.0, step=0.01,
                                         key=f"vb_{rec['code_type']}")
                vals[rec["code_type"]] = {
                    "nb": nb, "tmc": tmc, "dmt": dmt, "vb": vb,
                    "lib": rec["libelle_reclamation"], "cat": cat_name,
                }

        st.markdown("---")
        b1, b2 = st.columns(2)
        with b1:
            draft = st.form_submit_button("Enregistrer brouillon", use_container_width=True)
        with b2:
            submit = st.form_submit_button("Soumettre pour validation",
                                            use_container_width=True, type="primary")

        if draft or submit:
            has = any(v["nb"] > 0 or v["vb"] > 0 for v in vals.values())
            if not has:
                st.error("Saisissez au moins une réclamation.")
            else:
                lot_id = generate_lot_id(code_province, "RECLAM")
                status = "brouillon" if draft else "soumis"
                records = []
                for code, v in vals.items():
                    if v["nb"] > 0 or v["vb"] > 0:
                        records.append((
                            id_province, province_name, centre["id"], centre["nom"],
                            annee, mois, code, v["lib"], v["cat"],
                            v["nb"], v["tmc"], v["dmt"], v["vb"],
                            status, user["id"],
                            datetime.now() if submit else None, lot_id,
                        ))
                try:
                    insert_staging_reclamations(records)
                    AuthManager.log_action(
                        user["id"],
                        "SAISIE_RECLAMATIONS" if draft else "SOUMISSION_RECLAMATIONS",
                        "staging_reclamations_dp",
                        details={"lot_id": lot_id, "nb": len(records)},
                    )
                    if draft:
                        st.success(f"Brouillon enregistré — {len(records)} types. "
                                   f"Modifiez-le dans l'onglet « Brouillons ».")
                    else:
                        st.success(f"Soumis pour validation — {len(records)} types.")
                except Exception as e:
                    st.error(f"Erreur : {e}")

    st.markdown(render_section_close(), unsafe_allow_html=True)


def _render_reclam_history(id_province):
    st.markdown(render_section_open("Historique des saisies", "ARCHIVE"), unsafe_allow_html=True)

    f_st = st.selectbox("Filtrer par statut",
                        ["Tous", "brouillon", "soumis", "valide_dp",
                         "rejete_dp", "valide_regional", "rejete_regional"],
                        format_func=lambda x: "Tous" if x == "Tous" else STATUS_LABELS.get(x, x),
                        key="hr_s")

    lots = get_staging_lots(id_province=id_province,
                            statut=f_st if f_st != "Tous" else None,
                            data_type="reclamations")

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
        sel = st.selectbox("Détails d'un lot", ["—"] + list(lot_opts.keys()), key="det_rh")

        if sel != "—":
            lot = lot_opts[sel]
            st.markdown(f"**Statut :** {get_status_badge(lot['statut'])}", unsafe_allow_html=True)
            details = get_staging_reclamations(lot_id=lot["lot_id"])
            if details:
                df_d = pd.DataFrame(details)
                cols = [c for c in ["code_type", "libelle_reclamation", "nombre_reclamations",
                                    "temps_moyen_coupure_h", "delai_moyen_traitement_j",
                                    "valeur_brute"] if c in df_d.columns]
                st.dataframe(df_d[cols], use_container_width=True, hide_index=True)
    else:
        st.markdown(render_empty("INBOX", "Aucun lot trouvé"), unsafe_allow_html=True)

    st.markdown(render_section_close(), unsafe_allow_html=True)