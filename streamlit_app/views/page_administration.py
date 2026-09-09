# views/page_administration.py
"""
Administration de l'application (Schéma Normalisé 3NF).
Gestion des utilisateurs avec clés étrangères id_role / id_province,
journal d'audit complet et création de nouveaux comptes.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from auth.session_manager import SessionManager
from auth.authentication import AuthManager
from db.queries import (
    get_audit_logs,
    get_audit_available_years,
    get_audit_available_users,
    get_roles,
    get_provinces,
)
from utils.helpers import format_datetime, MOIS_FR
from utils.styles import (
    render_page_header,
    render_section_open,
    render_section_close,
    render_empty,
    render_notice,
)


def render_administration():
    SessionManager.require_role(["admin_regional", "super_admin"])
    user = SessionManager.get_user()

    st.markdown(
        render_page_header("Administration", "Gestion des comptes utilisateurs et journal d'audit"),
        unsafe_allow_html=True,
    )

    tab_users, tab_logs, tab_create = st.tabs([
        "Utilisateurs",
        "Journal d'audit",
        "Nouveau compte"
    ])

    with tab_users:
        _render_users_list(user)

    with tab_logs:
        _render_audit_logs()

    with tab_create:
        _render_create_user(user)


def _render_users_list(current_user):
    """Liste des utilisateurs avec bascule actif/inactif et suppression sécurisée."""
    st.markdown(render_section_open("Comptes utilisateurs", "USERS"), unsafe_allow_html=True)

    users = AuthManager.get_all_users()
    if not users:
        st.markdown(render_empty("USERS", "Aucun utilisateur"), unsafe_allow_html=True)
        st.markdown(render_section_close(), unsafe_allow_html=True)
        return

    rows = []
    for u in users:
        rows.append({
            "ID": u["id_utilisateur"],
            "Identifiant": u.get("username", "—"),
            "Nom complet": u.get("nom_complet", "—"),
            "Rôle": u.get("libelle_role", u.get("code_role", "—")),
            "Province": u.get("nom_province") or "Régional (Siège)",
            "Actif": "Oui" if u.get("est_actif") else "Non",
            "Dernière connexion": format_datetime(u.get("derniere_connexion")),
            "Créé le": format_datetime(u.get("date_creation")),
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Selectbox utilisateur
    user_tuple_list = [(u["id_utilisateur"], u["username"], u["est_actif"], u["code_role"]) for u in users]
    sel = st.selectbox(
        "Sélectionner un utilisateur à gérer",
        user_tuple_list,
        format_func=lambda x: f"{x[1]} ({'actif' if x[2] else 'inactif'})",
        key="user_select_mgmt",
    )

    is_self = sel[0] == current_user["id"]
    if is_self:
        st.warning("Vous ne pouvez pas modifier ou désactiver votre propre compte actuellement connecté.")

    st.markdown("**Activer / Désactiver le compte**")
    b1, b2, _ = st.columns([1.5, 1.5, 3])

    with b1:
        st.markdown('<div class="btn-success">', unsafe_allow_html=True)
        if st.button("Activer le compte", use_container_width=True, key="btn_act_user", disabled=is_self):
            AuthManager.toggle_user_status(sel[0], True)
            AuthManager.log_action(current_user["id"], "ACTIVATE_USER", "utilisateurs", sel[0])
            st.success(f"Compte {sel[1]} activé.")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with b2:
        st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
        if st.button("Désactiver le compte", use_container_width=True, key="btn_deact_user", disabled=is_self):
            AuthManager.toggle_user_status(sel[0], False)
            AuthManager.log_action(current_user["id"], "DEACTIVATE_USER", "utilisateurs", sel[0])
            st.warning(f"Compte {sel[1]} désactivé.")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # Suppression super_admin
    if current_user["role"] == "super_admin":
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        st.markdown("**Supprimer définitivement le compte**")

        target_role = sel[3]
        can_delete = not is_self and target_role != "super_admin"

        confirm_key = f"confirm_del_usr_{sel[0]}"
        if confirm_key not in st.session_state:
            st.session_state[confirm_key] = False

        if not can_delete:
            st.caption("Impossible de supprimer son propre compte ou un compte Super Admin.")
        elif not st.session_state[confirm_key]:
            st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
            if st.button("🗑 Supprimer ce compte", key="btn_del_usr_init"):
                st.session_state[confirm_key] = True
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.error(f"⚠️ Confirmation : Supprimer définitivement '{sel[1]}' ? Cette action est irréversible.")
            c_yes, c_no = st.columns(2)
            with c_yes:
                st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
                if st.button("Oui, supprimer", key="btn_del_usr_conf"):
                    res = AuthManager.delete_user(sel[0])
                    if res["success"]:
                        st.session_state[confirm_key] = False
                        st.success(res["message"])
                        st.rerun()
                    else:
                        st.error(res["message"])
                st.markdown("</div>", unsafe_allow_html=True)
            with c_no:
                if st.button("Annuler", key="btn_del_usr_canc"):
                    st.session_state[confirm_key] = False
                    st.rerun()

    st.markdown(render_section_close(), unsafe_allow_html=True)


def _render_audit_logs():
    """Affiche le journal d'audit avec filtres unifiés."""
    st.markdown(render_section_open("Journal d'audit", "FILE_TEXT"), unsafe_allow_html=True)

    annees_dispo = get_audit_available_years() or [datetime.now().year]
    users_dispo = get_audit_available_users() or []
    provinces = get_provinces() or []

    f1, f2, f3, f4 = st.columns(4)

    with f1:
        u_opts = [(None, "Tous les utilisateurs")] + [(u["id_utilisateur"], f"{u['nom_complet']} ({u['username']})") for u in users_dispo]
        f_user = st.selectbox("Utilisateur", u_opts, format_func=lambda x: x[1], key="audit_f_usr")

    with f2:
        p_opts = [(None, "Toutes les provinces")] + [(p["id_province"], p["nom_province"]) for p in provinces]
        f_prov = st.selectbox("Province", p_opts, format_func=lambda x: x[1], key="audit_f_prv")

    with f3:
        f_annee = st.selectbox("Année", ["Toutes"] + annees_dispo, key="audit_f_yr")

    with f4:
        f_mois = st.selectbox(
            "Mois",
            ["Tous"] + list(range(1, 13)),
            format_func=lambda x: "Tous les mois" if x == "Tous" else MOIS_FR[x],
            key="audit_f_mth",
        )

    user_id_filter = f_user[0] if isinstance(f_user, tuple) else None
    prov_id_filter = f_prov[0] if isinstance(f_prov, tuple) else None
    annee_filter = f_annee if f_annee != "Toutes" else None
    mois_filter = f_mois if f_mois != "Tous" else None

    logs = get_audit_logs(
        user_id=user_id_filter,
        id_province=prov_id_filter,
        annee=annee_filter,
        mois=mois_filter,
        limit=500,
    )

    if logs:
        rows = []
        for log in logs:
            rows.append({
                "Date": format_datetime(log.get("date_action")),
                "Utilisateur": log.get("nom_complet", "—"),
                "Username": log.get("username", "—"),
                "Rôle": log.get("role", "—"),
                "Province": log.get("code_province") or "Régional",
                "Action": log.get("action", "—"),
                "Table ciblée": log.get("table_cible", "—"),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.markdown(render_empty("FILE_TEXT", "Aucune activité trouvée", "Aucun log ne correspond à vos filtres."), unsafe_allow_html=True)

    st.markdown(render_section_close(), unsafe_allow_html=True)


def _render_create_user(current_user):
    """Formulaire de création d'un utilisateur utilisant id_role et id_province (Clés étrangères 3NF)."""
    st.markdown(render_section_open("Créer un nouveau compte", "PLUS"), unsafe_allow_html=True)

    st.markdown(render_notice("Le mot de passe par défaut est <strong>SRM2024!</strong>."), unsafe_allow_html=True)

    roles = get_roles() or []
    role_map = {r["libelle_role"]: r["id_role"] for r in roles}

    provinces = get_provinces() or []
    prov_map = {p["nom_province"]: p["id_province"] for p in provinces}

    with st.form("create_usr_form_3nf"):
        c1, c2 = st.columns(2)

        with c1:
            username = st.text_input("Identifiant *", placeholder="ex: agent_dp_tata")
            nom_complet = st.text_input("Nom complet *", placeholder="Prénom Nom")
            email = st.text_input("Email", placeholder="agent.tata@srm-sm.ma")

        with c2:
            sel_role_lbl = st.selectbox("Rôle *", list(role_map.keys()))
            sel_prov_lbl = st.selectbox("Province", ["Aucune (Siège Régional)"] + list(prov_map.keys()))
            password = st.text_input("Mot de passe *", type="password", value="SRM2024!")

        submitted = st.form_submit_button("Créer le compte", type="primary", use_container_width=True)

        if submitted:
            if not username or not nom_complet or not password:
                st.error("Les champs marqués d'un * sont obligatoires.")
            elif len(password) < 8:
                st.error("Le mot de passe doit contenir au moins 8 caractères.")
            else:
                id_role = role_map[sel_role_lbl]
                id_province = prov_map.get(sel_prov_lbl) if sel_prov_lbl != "Aucune (Siège Régional)" else None

                res = AuthManager.create_user(
                    username=username,
                    password=password,
                    nom_complet=nom_complet,
                    email=email,
                    id_role=id_role,
                    id_province=id_province,
                )

                if res["success"]:
                    AuthManager.log_action(current_user["id"], "CREATE_USER", "utilisateurs", details={"username": username, "id_role": id_role})
                    st.success(res["message"])
                    st.rerun()
                else:
                    st.error(res["message"])

    st.markdown(render_section_close(), unsafe_allow_html=True)