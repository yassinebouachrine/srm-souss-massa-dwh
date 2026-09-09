# views/page_reclamations.py
"""Saisie et gestion des réclamations DP."""

import streamlit as st
import time

from auth.session_manager import SessionManager
from auth.authentication import AuthManager
from db.queries import (
    get_types_reclamation, insert_reclamations_batch, get_staging_lots, get_centres,
    get_lots_transferes_pour_agent,
    get_demandes_pour_user,
)
from config.provinces import get_province_name
from utils.helpers import get_current_period, MOIS_FR
from utils.styles import (
    render_page_header, render_notice, render_section_open,
    render_section_close, render_form_category
)

CATEGORIE_LABELS = {
    "Reclamation_Eau": "Réclamations liées à l'eau",
    "Incidents": "Incidents réseau",
    "QoS_Traitement": "Qualité de service (durées moyennes)",
    "Reclamation_Divers": "Réclamations diverses",
}
ORDRE_CATEGORIES = ["Reclamation_Eau", "Incidents", "QoS_Traitement"]


def render_reclamations():
    SessionManager.require_role(["agent_dp", "admin_dp", "super_admin"])
    user = SessionManager.get_user()
    id_province = user["id_province"]
    province_name = user["nom_province"] or get_province_name(id_province)
    role = user["role"]
    is_admin = role in ("admin_dp", "super_admin")

    st.markdown(render_page_header("Réclamations DP", f"Province de {province_name}"), unsafe_allow_html=True)

    if is_admin:
        st.markdown(render_notice(
            "En tant qu'admin DP, vos saisies sont <strong>auto-validées</strong> et transmises directement au régional. "
            "Consultez la page <strong>Validation DP</strong> pour gérer les rejets et demandes de modification.",
            "info"
        ), unsafe_allow_html=True)

    drafts = get_staging_lots(
        id_province=id_province, statut="brouillon",
        type_donnees="reclamations", user_id=user["id"]
    ) or []

    # ─── Lots rejetés & demandes uniquement pour l'AGENT DP ───
    if role == "agent_dp":
        rej_dp = get_staging_lots(
            id_province=id_province, statut="partiellement_rejete_dp",
            type_donnees="reclamations"
        ) or []
        rej_dp = [l for l in rej_dp if l["cree_par"] == user["id"]]
        rej_transferes = get_lots_transferes_pour_agent(id_province, user["id"], "reclamations") or []
        rejected = rej_dp + rej_transferes

        demandes_modif = get_demandes_pour_user(user["id"], "reclamations") or []
    else:
        rejected = []
        demandes_modif = []

    if rejected:
        st.markdown(render_notice(
            f"Vos lot(s) de réclamations rejeté(s) : <strong>{len(rejected)}</strong>. "
            f"Consultez l'onglet « Lots rejetés » pour corriger.",
            "warning"
        ), unsafe_allow_html=True)

    if drafts:
        st.markdown(render_notice(
            f"Vous avez <strong>{len(drafts)}</strong> brouillon(s) de réclamations non soumis.",
            "info"
        ), unsafe_allow_html=True)

    from views.page_indicateurs import render_draft_lots, render_rejected_lots, _render_history, render_modifications_agent

    # ─── Onglets adaptés selon le rôle ───
    if is_admin:
        # Admin DP / Super Admin : PAS d'onglets rejets/modifs
        tab_new, tab_drafts, tab_hist = st.tabs([
            "Nouvelle saisie",
            f"Brouillons ({len(drafts)})",
            "Historique"
        ])

        with tab_new:
            _render_new_reclamation(user, id_province)
        with tab_drafts:
            render_draft_lots("reclamations", user, drafts)
        with tab_hist:
            _render_history("reclamations", id_province)
    else:
        # Agent DP : tous les onglets
        tab_new, tab_drafts, tab_rejected, tab_modif, tab_hist = st.tabs([
            "Nouvelle saisie",
            f"Brouillons ({len(drafts)})",
            f"Lots rejetés ({len(rejected)})",
            f"Modifications demandées ({len(demandes_modif)})",
            "Historique"
        ])

        with tab_new:
            _render_new_reclamation(user, id_province)
        with tab_drafts:
            render_draft_lots("reclamations", user, drafts)
        with tab_rejected:
            render_rejected_lots("reclamations", user, rejected, role)
        with tab_modif:
            render_modifications_agent("reclamations", user, demandes_modif)
        with tab_hist:
            _render_history("reclamations", id_province)        

def _render_new_reclamation(user, id_province):
    role = user["role"]
    is_admin = role in ("admin_dp", "super_admin")

    st.markdown(render_notice(
        "Saisissez la valeur pour chaque type de réclamation. "
        "Pour tout ce qui n'entre pas dans les types listés, cochez <strong>Autres</strong> "
        "et saisissez votre commentaire."
    ), unsafe_allow_html=True)

    st.markdown(render_section_open("Période et centre", "CALENDAR"), unsafe_allow_html=True)
    cy, cm = get_current_period()
    c1, c2, c3 = st.columns(3)
    with c1:
        annee = st.selectbox("Année", list(range(cy, cy - 3, -1)), key="r_a")
    with c2:
        mois = st.selectbox("Mois", list(range(1, 13)), format_func=lambda x: MOIS_FR[x], index=max(0, cm - 2), key="r_m")
    with c3:
        centres = get_centres(id_province)
        cmap = {c["nom_centre"]: c for c in centres}
        cn = st.selectbox("Centre", list(cmap.keys()), key="r_c")
        centre = cmap[cn]
    st.markdown(render_section_close(), unsafe_allow_html=True)

    types = get_types_reclamation()
    if not types:
        st.warning("Aucun type de réclamation configuré.")
        return

    # Séparer AUTRES du reste
    type_autres = None
    types_normaux = []
    for t in types:
        if t["code_type"] == "AUTRES":
            type_autres = t
        else:
            types_normaux.append(t)

    cats = {}
    for t in types_normaux:
        cats.setdefault(t["categorie_reclamation"] or "Autres", []).append(t)

    cats_ordered = {k: cats[k] for k in ORDRE_CATEGORIES if k in cats}
    for k, v in cats.items():
        if k not in cats_ordered:
            cats_ordered[k] = v

    st.markdown(render_section_open("Saisie des réclamations", "EDIT"), unsafe_allow_html=True)

    with st.form("form_rec", clear_on_submit=True):
        vals = {}

        # Catégories standards
        for cat_code, recs in cats_ordered.items():
            st.markdown(render_form_category("FOLDER", CATEGORIE_LABELS.get(cat_code, cat_code)), unsafe_allow_html=True)
            hc1, hc2 = st.columns([6, 3])
            with hc1:
                st.markdown("<div style='font-weight:600;font-size:0.8rem;color:#6B7280;'>TYPE DE RÉCLAMATION</div>", unsafe_allow_html=True)
            with hc2:
                st.markdown("<div style='font-weight:600;font-size:0.8rem;color:#6B7280;'>VALEUR</div>", unsafe_allow_html=True)

            for rec in recs:
                cl, cv = st.columns([6, 3])
                unite = "h" if "(h)" in rec["libelle_reclamation"] else ("j" if "(j)" in rec["libelle_reclamation"] else "")
                with cl:
                    unite_html = f" <span style='color:#6B7280;font-size:0.78rem;'>({unite})</span>" if unite else ""
                    st.markdown(
                        f"<div style='padding-top:0.5rem;'><strong>{rec['libelle_reclamation']}</strong>{unite_html}</div>",
                        unsafe_allow_html=True
                    )
                with cv:
                    if rec["est_duree"]:
                        val = st.number_input(
                            f"V {rec['code_type']}", min_value=0.0, value=0.0, step=0.1,
                            key=f"val_{rec['code_type']}", label_visibility="collapsed"
                        )
                    else:
                        val = st.number_input(
                            f"V {rec['code_type']}", min_value=0, value=0,
                            key=f"val_{rec['code_type']}", label_visibility="collapsed"
                        )

                if val > 0:
                    vals[rec["code_type"]] = {
                        "id_type_reclamation": rec["id_type_reclamation"],
                        "nb": int(val) if rec["est_comptage"] else 0,
                        "temps_coupure": float(val) if unite == "h" else 0.0,
                        "delai_traitement": float(val) if unite == "j" else 0.0,
                        "valeur_brute": float(val),
                        "commentaire_autre": None,
                    }

        # ═══ SECTION AUTRES (Checkbox + Commentaire = Valeur) ═══
        st.markdown(
            "<div style='background:#F9FAFB;border:1px solid #E5E7EB;border-radius:8px;"
            "padding:1rem;margin:1.25rem 0 0.75rem;'>"
            "<div style='font-weight:600;color:#111827;margin-bottom:0.35rem;'>Autres réclamations</div>"
            "<div style='font-size:0.8rem;color:#6B7280;'>"
            "Cochez si vous avez d'autres réclamations non listées ci-dessus et saisissez le détail ci-dessous."
            "</div></div>",
            unsafe_allow_html=True
        )

        use_autres = st.checkbox("Autres", key="chk_autres_reclamation")
        commentaire_autre = st.text_area(
            "Commentaire (ce texte sera la valeur de « Autres »)",
            placeholder="Ex: Réclamation spécifique au centre, incident particulier...",
            height=80,
            key="cmt_autres_reclamation",
        )

        if use_autres and type_autres:
            txt_comment = (commentaire_autre or "").strip() or None
            vals["AUTRES"] = {
                "id_type_reclamation": type_autres["id_type_reclamation"],
                "nb": 1,
                "temps_coupure": 0.0,
                "delai_traitement": 0.0,
                "valeur_brute": 1.0,
                "commentaire_autre": txt_comment,  # Le commentaire EST la valeur
            }

        st.markdown("---")
        b1, b2 = st.columns(2)
        with b1:
            draft = st.form_submit_button("Enregistrer brouillon", use_container_width=True)
        with b2:
            btn_lbl = "Soumettre et auto-valider" if is_admin else "Soumettre pour validation"
            submit = st.form_submit_button(btn_lbl, use_container_width=True, type="primary")

        if draft or submit:
            if not vals:
                st.error("Saisissez au moins une valeur non nulle, ou cochez « Autres ».")
            else:
                is_sub = bool(submit)
                id_lot = insert_reclamations_batch(
                    centre["id_centre"], annee, mois,
                    list(vals.values()), user["id"], is_sub
                )
                AuthManager.log_action(
                    user["id"],
                    "SOUMISSION_RECLAMATIONS" if is_sub else "BROUILLON_RECLAMATIONS",
                    "lot_saisie", id_lot,
                    {"nb": len(vals), "avec_autres": "AUTRES" in vals}
                )

                _clear_reclamation_form_keys()

                if is_sub and is_admin:
                    st.success(
                        f"Lot #{id_lot} saisi et transmis au régional "
                        f"(auto-validation DP) — {len(vals)} réclamation(s)."
                    )
                elif is_sub:
                    st.success(f"Lot #{id_lot} soumis — {len(vals)} réclamation(s).")
                else:
                    st.success(f"Brouillon #{id_lot} enregistré — {len(vals)} réclamation(s).")

                time.sleep(1)
                st.rerun()

    st.markdown(render_section_close(), unsafe_allow_html=True)


def _clear_reclamation_form_keys():
    """Vide les champs du formulaire de réclamations."""
    keys_to_delete = []
    for k in list(st.session_state.keys()):
        if k.startswith("val_") or k in ("chk_autres_reclamation", "cmt_autres_reclamation"):
            keys_to_delete.append(k)
    for k in keys_to_delete:
        try:
            del st.session_state[k]
        except KeyError:
            pass