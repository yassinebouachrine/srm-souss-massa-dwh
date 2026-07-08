# views/page_validation_regionale.py
import streamlit as st
import pandas as pd
from auth.session_manager import SessionManager
from auth.authentication import AuthManager
from db.queries import (
    get_staging_lots, get_staging_indicateurs, get_staging_reclamations,
    update_staging_status, transfer_validated_indicateurs_to_gold,
    transfer_validated_reclamations_to_gold
)
from config.provinces import PROVINCES
from utils.helpers import format_datetime, get_mois_name, MOIS_FR
from utils.styles import (
    render_page_header, render_notice, render_empty,
    render_section_open, render_section_close, render_metric
)


def render_validation_regionale():
    SessionManager.require_role(["admin_regional", "super_admin"])
    user = SessionManager.get_user()

    st.markdown(
        render_page_header("Validation régionale",
                           "Siège Agadir — Validation finale toutes provinces"),
        unsafe_allow_html=True,
    )

    # Stats
    all_indic = get_staging_lots(statut="valide_dp", data_type="indicateurs") or []
    all_reclam = get_staging_lots(statut="valide_dp", data_type="reclamations") or []
    done_indic = get_staging_lots(statut="valide_regional", data_type="indicateurs") or []
    done_reclam = get_staging_lots(statut="valide_regional", data_type="reclamations") or []

    c1, c2, c3, c4 = st.columns(4, gap="small")
    with c1:
        st.markdown(render_metric("Indic. à valider", len(all_indic), "CLOCK",
                                   sub="Toutes provinces"), unsafe_allow_html=True)
    with c2:
        st.markdown(render_metric("Réc. à valider", len(all_reclam), "CLOCK",
                                   sub="Toutes provinces"), unsafe_allow_html=True)
    with c3:
        st.markdown(render_metric("Indic. dans DWH", len(done_indic), "DATABASE",
                                   sub="Validés définitivement"), unsafe_allow_html=True)
    with c4:
        st.markdown(render_metric("Réc. dans DWH", len(done_reclam), "DATABASE",
                                   sub="Validées définitivement"), unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    st.markdown(render_notice(
        "Sélectionnez plusieurs lots pour valider en masse. "
        "Les données validées seront transférées immédiatement dans le Data Warehouse."
    ), unsafe_allow_html=True)

    tab_i, tab_r, tab_h = st.tabs([
        f"Indicateurs ({len(all_indic)})",
        f"Réclamations ({len(all_reclam)})",
        f"Historique DWH ({len(done_indic) + len(done_reclam)})"
    ])

    with tab_i:
        _render_regional_batch("indicateurs", user)

    with tab_r:
        _render_regional_batch("reclamations", user)

    with tab_h:
        _render_history(done_indic, done_reclam)


def _render_regional_batch(data_type: str, user: dict):
    lots = get_staging_lots(statut="valide_dp", data_type=data_type) or []

    if not lots:
        st.markdown(render_empty("CHECK_CIRCLE", "Aucun lot en attente",
                                  "Toutes les données ont été traitées"),
                    unsafe_allow_html=True)
        return

    # Filtres
    st.markdown(render_section_open("Filtres", "FILTER"), unsafe_allow_html=True)

    f1, f2, f3 = st.columns(3)
    with f1:
        f_prov = st.selectbox("Province",
                               ["Toutes"] + [(pid, p["nom"]) for pid, p in PROVINCES.items()],
                               format_func=lambda x: "Toutes" if x == "Toutes" else x[1],
                               key=f"fp_{data_type}")
    with f2:
        annees = sorted(set(l["annee"] for l in lots), reverse=True)
        f_annee = st.selectbox("Année", ["Toutes"] + annees, key=f"fa_{data_type}")
    with f3:
        mois_dispo = sorted(set(l["mois"] for l in lots))
        f_mois = st.selectbox("Mois", ["Tous"] + mois_dispo,
                               format_func=lambda x: "Tous" if x == "Tous" else MOIS_FR[x],
                               key=f"fm_{data_type}")

    st.markdown(render_section_close(), unsafe_allow_html=True)

    # Filtrer
    filtered = lots
    if f_prov != "Toutes":
        filtered = [l for l in filtered if l["id_province"] == f_prov[0]]
    if f_annee != "Toutes":
        filtered = [l for l in filtered if l["annee"] == f_annee]
    if f_mois != "Tous":
        filtered = [l for l in filtered if l["mois"] == f_mois]

    # Enrichir
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
                "province": lot["nom_province"],
                "centre": first.get("nom_centre", "—"),
                "agent": first.get("soumis_par_nom", "—"),
                "valide_par": first.get("valide_dp_par_nom", "—"),
                "date_val_dp": format_datetime(first.get("date_validation_dp")),
                "mois": get_mois_name(lot["mois"]),
                "annee": lot["annee"],
                "nb": lot["nb_enregistrements"],
                "details": details,
            })

    st.markdown(f"<div style='color:#6B7280;font-size:0.85rem;margin-bottom:0.5rem;'>"
                f"<strong>{len(lots_enr)}</strong> lot(s) à valider</div>",
                unsafe_allow_html=True)

    if not lots_enr:
        st.markdown(render_empty("FILTER", "Aucun résultat"), unsafe_allow_html=True)
        return

    # Sélection multiple
    st.markdown(render_section_open("Sélection multiple", "LAYERS",
                                     "Cochez plusieurs lots pour validation en masse"),
                unsafe_allow_html=True)

    sel_key = f"selr_{data_type}"
    if sel_key not in st.session_state:
        st.session_state[sel_key] = {}

    hc = st.columns([0.4, 1.2, 1.2, 1.2, 0.6, 1.2, 0.6])
    with hc[0]:
        select_all = st.checkbox("", key=f"sar_{data_type}")
    with hc[1]: st.markdown("**Province**")
    with hc[2]: st.markdown("**Centre**")
    with hc[3]: st.markdown("**Validé DP par**")
    with hc[4]: st.markdown("**Période**")
    with hc[5]: st.markdown("**Date val. DP**")
    with hc[6]: st.markdown("**Enreg.**")

    st.markdown("<hr style='margin:0.3rem 0;'>", unsafe_allow_html=True)

    if select_all:
        for lot in lots_enr:
            st.session_state[sel_key][lot["lot_id"]] = True

    for lot in lots_enr:
        rc = st.columns([0.4, 1.2, 1.2, 1.2, 0.6, 1.2, 0.6])
        with rc[0]:
            checked = st.checkbox("", key=f"chkr_{data_type}_{lot['lot_id']}",
                                   value=st.session_state[sel_key].get(lot["lot_id"], False))
            st.session_state[sel_key][lot["lot_id"]] = checked
        with rc[1]:
            st.markdown(f"<span style='font-size:0.82rem;font-weight:600;'>{lot['province']}</span>",
                        unsafe_allow_html=True)
        with rc[2]:
            st.markdown(f"<span style='font-size:0.82rem;'>{lot['centre']}</span>",
                        unsafe_allow_html=True)
        with rc[3]:
            st.markdown(f"<span style='font-size:0.82rem;'>{lot['valide_par']}</span>",
                        unsafe_allow_html=True)
        with rc[4]:
            st.markdown(f"<span style='font-size:0.82rem;'>{lot['mois'][:3]} {lot['annee']}</span>",
                        unsafe_allow_html=True)
        with rc[5]:
            st.markdown(f"<span style='font-size:0.75rem;color:#6B7280;'>{lot['date_val_dp']}</span>",
                        unsafe_allow_html=True)
        with rc[6]:
            st.markdown(f"<strong style='font-size:0.85rem;'>{lot['nb']}</strong>",
                        unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # Actions de masse
    selected_ids = [lid for lid, sel in st.session_state[sel_key].items() if sel]
    nb_sel = len(selected_ids)

    comment = st.text_area(f"Commentaire pour les {nb_sel} lot(s)",
                            placeholder="Obligatoire en cas de rejet",
                            key=f"cmr_{data_type}", height=70)

    ac1, ac2, _ = st.columns([1.2, 1.2, 3])
    with ac1:
        st.markdown('<div class="btn-success">', unsafe_allow_html=True)
        if st.button(f"Valider & transférer ({nb_sel})", key=f"vallr_{data_type}",
                     use_container_width=True, disabled=(nb_sel == 0)):
            errors = []
            for lid in selected_ids:
                try:
                    update_staging_status(data_type, lid, "valide_regional",
                                          user["id"], comment, "regional")
                    if data_type == "indicateurs":
                        transfer_validated_indicateurs_to_gold(lid)
                    else:
                        transfer_validated_reclamations_to_gold(lid)
                    AuthManager.log_action(user["id"],
                                            f"VALIDATION_REG_{data_type.upper()}_MASS",
                                            f"staging_{data_type}_dp",
                                            details={"lot_id": lid, "dwh": True})
                except Exception as e:
                    errors.append(f"{lid[:15]}: {e}")

            st.session_state[sel_key] = {}
            if errors:
                st.error(f"Erreurs sur {len(errors)} lots :\n" + "\n".join(errors))
            else:
                st.success(f"{nb_sel} lot(s) validé(s) et transféré(s) au DWH.")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with ac2:
        st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
        if st.button(f"Rejeter ({nb_sel})", key=f"rallr_{data_type}",
                     use_container_width=True, disabled=(nb_sel == 0)):
            if not comment:
                st.error("Commentaire obligatoire.")
            else:
                for lid in selected_ids:
                    update_staging_status(data_type, lid, "rejete_regional",
                                          user["id"], comment, "regional")
                st.session_state[sel_key] = {}
                st.warning(f"{nb_sel} lot(s) rejeté(s).")
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(render_section_close(), unsafe_allow_html=True)

    # Détails
    st.markdown(render_section_open("Détails d'un lot", "EYE"),
                unsafe_allow_html=True)

    opts = {f"{l['province']} — {l['lot_id'][:20]}... ({l['nb']} enreg.)": l for l in lots_enr}
    sel = st.selectbox("Choisir un lot", ["—"] + list(opts.keys()), key=f"detr_{data_type}")

    if sel != "—":
        lot = opts[sel]
        first = lot["details"][0]

        st.markdown(f"""
        <div style='background:#F9FAFB;padding:0.75rem 1rem;border-radius:6px;margin-bottom:1rem;font-size:0.85rem;color:#374151;'>
            <strong>Province :</strong> {lot['province']} · <strong>Centre :</strong> {lot['centre']}<br>
            <strong>Agent :</strong> {lot['agent']} · <strong>Validé DP par :</strong> {lot['valide_par']}<br>
            <strong>Période :</strong> {lot['mois']} {lot['annee']}
        </div>
        """, unsafe_allow_html=True)

        if first.get("commentaire_dp"):
            st.markdown(render_notice(f"Commentaire DP : {first['commentaire_dp']}", "info"),
                        unsafe_allow_html=True)

        df = pd.DataFrame(lot["details"])
        if data_type == "indicateurs":
            cols = ["code_indicateur", "libelle_indicateur", "unite",
                    "valeur_mensuelle", "valeur_recapitulatif"]
        else:
            cols = ["code_type", "libelle_reclamation", "nombre_reclamations",
                    "temps_moyen_coupure_h", "delai_moyen_traitement_j", "valeur_brute"]

        st.dataframe(df[[c for c in cols if c in df.columns]],
                     use_container_width=True, hide_index=True)

    st.markdown(render_section_close(), unsafe_allow_html=True)


def _render_history(done_indic, done_reclam):
    st.markdown(render_section_open("Données transférées dans le Data Warehouse", "DATABASE"),
                unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Indicateurs**")
        if done_indic:
            df = pd.DataFrame(done_indic)
            df["date_creation"] = df["date_creation"].apply(format_datetime)
            st.dataframe(df[["nom_province", "annee", "nb_enregistrements", "date_creation"]],
                         use_container_width=True, hide_index=True)
        else:
            st.markdown(render_empty("DATABASE", "Aucune donnée"), unsafe_allow_html=True)

    with c2:
        st.markdown("**Réclamations**")
        if done_reclam:
            df = pd.DataFrame(done_reclam)
            df["date_creation"] = df["date_creation"].apply(format_datetime)
            st.dataframe(df[["nom_province", "annee", "nb_enregistrements", "date_creation"]],
                         use_container_width=True, hide_index=True)
        else:
            st.markdown(render_empty("DATABASE", "Aucune donnée"), unsafe_allow_html=True)

    st.markdown(render_section_close(), unsafe_allow_html=True)