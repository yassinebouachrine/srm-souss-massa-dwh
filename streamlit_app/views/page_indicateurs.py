# pages/page_indicateurs.py
import streamlit as st
import pandas as pd
from datetime import datetime
from auth.session_manager import SessionManager
from auth.authentication import AuthManager
from db.queries import (
    get_types_indicateur, insert_staging_indicateurs,
    get_staging_indicateurs, submit_lot, get_staging_lots
)
from config.provinces import get_province_name, get_centres_for_province
from utils.helpers import generate_lot_id, get_current_period, MOIS_FR, get_mois_name
from utils.styles import (
    render_page_header, render_notice, render_empty,
    render_section_open, render_section_close,
    render_form_category, get_status_badge
)


def render_indicateurs():
    SessionManager.require_role(["agent_dp", "admin_dp", "super_admin"])
    user = SessionManager.get_user()
    id_province = user["id_province"]
    code_province = user["code_province"]
    province_name = get_province_name(id_province)

    st.markdown(
        render_page_header("Indicateurs de performance DP",
                           f"Province de {province_name}"),
        unsafe_allow_html=True,
    )

    tab_new, tab_hist = st.tabs(["Nouvelle saisie", "Historique"])

    # ═══════════════════════════════════════════════
    with tab_new:
        st.markdown(render_notice(
            "Renseignez les valeurs mensuelles et récapitulatives, puis enregistrez en brouillon ou soumettez pour validation."
        ), unsafe_allow_html=True)

        # Période et centre
        st.markdown(render_section_open("Période et centre", "CALENDAR"),
                    unsafe_allow_html=True)

        cy, cm = get_current_period()
        c1, c2, c3 = st.columns(3)
        with c1:
            annee = st.selectbox("Année", list(range(cy, cy - 3, -1)), key="i_a")
        with c2:
            mois = st.selectbox("Mois", list(range(1, 13)),
                                format_func=lambda x: MOIS_FR[x],
                                index=max(0, cm - 2), key="i_m")
        with c3:
            centres = get_centres_for_province(id_province)
            cmap = {c["nom"]: c for c in centres}
            cn = st.selectbox("Centre", list(cmap.keys()), key="i_c")
            centre = cmap[cn]

        st.markdown(render_section_close(), unsafe_allow_html=True)

        # Indicateurs
        types = get_types_indicateur()
        if not types:
            st.warning("Aucun type d'indicateur configuré.")
            return

        cats = {}
        for t in types:
            cats.setdefault(t["categorie"] or "Autres", []).append(t)

        st.markdown(render_section_open("Saisie des valeurs", "EDIT"),
                    unsafe_allow_html=True)

        with st.form("form_ind", clear_on_submit=False):
            vals = {}

            for cat_name, indics in cats.items():
                st.markdown(render_form_category("FOLDER", cat_name),
                            unsafe_allow_html=True)

                # Headers — LABELS VISIBLES avec markdown ** **
                h1, h2, h3 = st.columns([4, 1.5, 1.5])
                with h1:
                    st.markdown("**Indicateur**")
                with h2:
                    st.markdown("**Valeur mensuelle**")
                with h3:
                    st.markdown("**Valeur récap.**")

                for ind in indics:
                    cc1, cc2, cc3 = st.columns([4, 1.5, 1.5])
                    with cc1:
                        st.markdown(
                            f"<div style='padding-top:0.5rem;font-size:0.85rem;color:#111827;'>"
                            f"<code>{ind['code_indicateur']}</code> {ind['libelle_indicateur']} "
                            f"<span style='color:#9CA3AF;font-size:0.75rem;'>({ind['unite']})</span>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                    with cc2:
                        vm = st.number_input(
                            f"vm_{ind['code_indicateur']}",
                            min_value=0.0, value=0.0, step=0.01,
                            key=f"vm_{ind['code_indicateur']}",
                            label_visibility="collapsed",
                        )
                    with cc3:
                        vr = st.number_input(
                            f"vr_{ind['code_indicateur']}",
                            min_value=0.0, value=0.0, step=0.01,
                            key=f"vr_{ind['code_indicateur']}",
                            label_visibility="collapsed",
                        )
                    vals[ind["code_indicateur"]] = {
                        "vm": vm, "vr": vr, "lib": ind["libelle_indicateur"],
                        "unite": ind["unite"], "cat": cat_name,
                    }

            st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

            b1, b2 = st.columns(2)
            with b1:
                draft = st.form_submit_button("Enregistrer brouillon", use_container_width=True)
            with b2:
                submit = st.form_submit_button("Soumettre pour validation",
                                                use_container_width=True, type="primary")

            if draft or submit:
                has = any(v["vm"] > 0 or v["vr"] > 0 for v in vals.values())
                if not has:
                    st.error("Saisissez au moins une valeur.")
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
                            st.success(f"Brouillon enregistré ({len(records)} indicateurs)")
                        else:
                            st.success(f"Soumis pour validation ({len(records)} indicateurs)")
                    except Exception as e:
                        st.error(f"Erreur : {e}")

        st.markdown(render_section_close(), unsafe_allow_html=True)

    # ═══════════════════════════════════════════════
    with tab_hist:
        st.markdown(render_section_open("Historique des saisies", "ARCHIVE"),
                    unsafe_allow_html=True)

        f_st = st.selectbox("Filtrer par statut",
                            ["Tous", "brouillon", "soumis", "valide_dp",
                             "rejete_dp", "valide_regional", "rejete_regional"],
                            key="hi_s")

        lots = get_staging_lots(
            id_province=id_province,
            statut=f_st if f_st != "Tous" else None,
            data_type="indicateurs",
        )

        if lots:
            for lot in lots:
                with st.expander(
                    f"{lot['lot_id']}  ·  {get_mois_name(lot['mois'])} {lot['annee']}  ·  "
                    f"{lot['nb_enregistrements']} enreg."
                ):
                    st.markdown(f"**Statut :** {get_status_badge(lot['statut'])}",
                                unsafe_allow_html=True)

                    details = get_staging_indicateurs(lot_id=lot["lot_id"])
                    if details:
                        df = pd.DataFrame(details)
                        cols = [c for c in ["code_indicateur", "libelle_indicateur", "unite",
                                            "valeur_mensuelle", "valeur_recapitulatif"]
                                if c in df.columns]
                        st.dataframe(df[cols], use_container_width=True, hide_index=True)

                    if lot["statut"] == "brouillon":
                        if st.button("Soumettre ce lot", key=f"sub_{lot['lot_id']}", type="primary"):
                            submit_lot("indicateurs", lot["lot_id"], user["id"])
                            st.success("Lot soumis.")
                            st.rerun()

                    if lot["statut"] in ["rejete_dp", "rejete_regional"] and details:
                        cm = details[0].get("commentaire_dp") or details[0].get("commentaire_regional")
                        if cm:
                            st.markdown(render_notice(f"Motif du rejet : {cm}", "warning"),
                                        unsafe_allow_html=True)
        else:
            st.markdown(render_empty("INBOX", "Aucun lot"), unsafe_allow_html=True)

        st.markdown(render_section_close(), unsafe_allow_html=True)