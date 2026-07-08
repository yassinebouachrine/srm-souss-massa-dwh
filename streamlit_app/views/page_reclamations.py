# pages/page_reclamations.py
import streamlit as st
import pandas as pd
from datetime import datetime
from auth.session_manager import SessionManager
from auth.authentication import AuthManager
from db.queries import (
    get_types_reclamation, insert_staging_reclamations,
    get_staging_reclamations, submit_lot, get_staging_lots
)
from config.provinces import get_province_name, get_centres_for_province
from utils.helpers import generate_lot_id, get_current_period, MOIS_FR, get_mois_name
from utils.styles import (
    render_page_header, render_notice, render_empty,
    render_section_open, render_section_close,
    render_form_category, get_status_badge
)


def render_reclamations():
    SessionManager.require_role(["agent_dp", "admin_dp", "super_admin"])
    user = SessionManager.get_user()
    id_province = user["id_province"]
    code_province = user["code_province"]
    province_name = get_province_name(id_province)

    st.markdown(
        render_page_header("Réclamations DP",
                           f"Province de {province_name}"),
        unsafe_allow_html=True,
    )

    tab_new, tab_hist = st.tabs(["Nouvelle saisie", "Historique"])

    with tab_new:
        st.markdown(render_notice(
            "Saisissez le nombre de réclamations, le temps moyen de coupure et le délai moyen de traitement."
        ), unsafe_allow_html=True)

        st.markdown(render_section_open("Période et centre", "CALENDAR"),
                    unsafe_allow_html=True)

        cy, cm = get_current_period()
        c1, c2, c3 = st.columns(3)
        with c1:
            annee = st.selectbox("Année", list(range(cy, cy - 3, -1)), key="r_a")
        with c2:
            mois = st.selectbox("Mois", list(range(1, 13)),
                                format_func=lambda x: MOIS_FR[x],
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

        st.markdown(render_section_open("Saisie des réclamations", "EDIT"),
                    unsafe_allow_html=True)

        with st.form("form_rec", clear_on_submit=False):
            vals = {}

            for cat_name, recs in cats.items():
                st.markdown(render_form_category("FOLDER", cat_name), unsafe_allow_html=True)

                # Headers with visible labels
                hc = st.columns([3.5, 1, 1, 1, 1])
                with hc[0]: st.markdown("**Type de réclamation**")
                with hc[1]: st.markdown("**Nombre**")
                with hc[2]: st.markdown("**TMC (h)**")
                with hc[3]: st.markdown("**DMT (j)**")
                with hc[4]: st.markdown("**Valeur brute**")

                for rec in recs:
                    cc = st.columns([3.5, 1, 1, 1, 1])
                    with cc[0]:
                        st.markdown(
                            f"<div style='padding-top:0.5rem;font-size:0.85rem;color:#111827;'>"
                            f"<code>{rec['code_type']}</code> {rec['libelle_reclamation']}"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                    with cc[1]:
                        nb = st.number_input(f"nb_{rec['code_type']}", 0, value=0, step=1,
                                             key=f"nb_{rec['code_type']}",
                                             label_visibility="collapsed")
                    with cc[2]:
                        tmc = st.number_input(f"tmc_{rec['code_type']}", 0.0, value=0.0, step=0.1,
                                              key=f"tmc_{rec['code_type']}",
                                              label_visibility="collapsed",
                                              disabled=not rec.get("est_duree", True))
                    with cc[3]:
                        dmt = st.number_input(f"dmt_{rec['code_type']}", 0.0, value=0.0, step=0.1,
                                              key=f"dmt_{rec['code_type']}",
                                              label_visibility="collapsed")
                    with cc[4]:
                        vb = st.number_input(f"vb_{rec['code_type']}", 0.0, value=0.0, step=0.01,
                                             key=f"vb_{rec['code_type']}",
                                             label_visibility="collapsed")

                    vals[rec["code_type"]] = {
                        "nb": nb, "tmc": tmc, "dmt": dmt, "vb": vb,
                        "lib": rec["libelle_reclamation"], "cat": cat_name,
                    }

            st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

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
                            st.success(f"Brouillon enregistré ({len(records)} types)")
                        else:
                            st.success(f"Soumis pour validation ({len(records)} types)")
                    except Exception as e:
                        st.error(f"Erreur : {e}")

        st.markdown(render_section_close(), unsafe_allow_html=True)

    with tab_hist:
        st.markdown(render_section_open("Historique des saisies", "ARCHIVE"),
                    unsafe_allow_html=True)

        f_st = st.selectbox("Filtrer par statut",
                            ["Tous", "brouillon", "soumis", "valide_dp",
                             "rejete_dp", "valide_regional", "rejete_regional"],
                            key="hr_s")

        lots = get_staging_lots(id_province=id_province,
                                statut=f_st if f_st != "Tous" else None,
                                data_type="reclamations")

        if lots:
            for lot in lots:
                with st.expander(
                    f"{lot['lot_id']}  ·  {get_mois_name(lot['mois'])} {lot['annee']}  ·  "
                    f"{lot['nb_enregistrements']} types"
                ):
                    st.markdown(f"**Statut :** {get_status_badge(lot['statut'])}",
                                unsafe_allow_html=True)

                    details = get_staging_reclamations(lot_id=lot["lot_id"])
                    if details:
                        df = pd.DataFrame(details)
                        cols = [c for c in ["code_type", "libelle_reclamation", "nombre_reclamations",
                                            "temps_moyen_coupure_h", "delai_moyen_traitement_j",
                                            "valeur_brute"] if c in df.columns]
                        st.dataframe(df[cols], use_container_width=True, hide_index=True)

                    if lot["statut"] == "brouillon":
                        if st.button("Soumettre", key=f"sr_{lot['lot_id']}", type="primary"):
                            submit_lot("reclamations", lot["lot_id"], user["id"])
                            st.success("Soumis.")
                            st.rerun()

                    if lot["statut"] in ["rejete_dp", "rejete_regional"] and details:
                        cm = details[0].get("commentaire_dp") or details[0].get("commentaire_regional")
                        if cm:
                            st.markdown(render_notice(f"Motif : {cm}", "warning"),
                                        unsafe_allow_html=True)
        else:
            st.markdown(render_empty("INBOX", "Aucun lot"), unsafe_allow_html=True)

        st.markdown(render_section_close(), unsafe_allow_html=True)