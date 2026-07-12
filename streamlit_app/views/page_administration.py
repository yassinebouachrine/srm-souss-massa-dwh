# views/page_administration.py
import streamlit as st
import pandas as pd
from auth.session_manager import SessionManager
from auth.authentication import AuthManager
from db.queries import get_audit_logs
from config.provinces import PROVINCES
from utils.helpers import format_datetime
from utils.styles import (
    render_page_header, render_section_open, render_section_close,
    render_empty, render_notice
)


def render_administration():
    """Page d'administration - gestion des utilisateurs et audit."""
    SessionManager.require_role(["admin_regional", "super_admin"])
    user = SessionManager.get_user()

    st.markdown(
        render_page_header("Administration",
                           "Gestion des utilisateurs et journal d'audit"),
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
    """Liste des utilisateurs avec possibilité d'activer/désactiver."""
    st.markdown(render_section_open("Comptes utilisateurs", "USERS"), unsafe_allow_html=True)

    users = AuthManager.get_all_users()
    if not users:
        st.markdown(render_empty("USERS", "Aucun utilisateur"), unsafe_allow_html=True)
        st.markdown(render_section_close(), unsafe_allow_html=True)
        return

    # ✅ FIX : Construire le DataFrame ligne par ligne pour gérer les NULL
    role_labels = {
        "agent_dp": "Agent DP",
        "admin_dp": "Admin DP",
        "admin_regional": "Admin Régional",
        "super_admin": "Super Admin",
    }

    rows = []
    for u in users:
        rows.append({
            "Identifiant": u.get("username", "—"),
            "Nom complet": u.get("nom_complet", "—"),
            "Rôle": role_labels.get(u.get("role"), u.get("role", "—")),
            "Province": u.get("code_province") or "—",
            "Actif": "Oui" if u.get("est_actif") else "Non",
            "Dernière connexion": format_datetime(u.get("derniere_connexion")),
            "Créé le": format_datetime(u.get("date_creation")),
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("**Activer / Désactiver un compte**")

    sel = st.selectbox(
        "Sélectionner un utilisateur",
        [(u["id_utilisateur"], u["username"], u["est_actif"]) for u in users],
        format_func=lambda x: f"{x[1]}  ({'actif' if x[2] else 'inactif'})",
        key="user_toggle",
    )

    b1, b2, _ = st.columns([1.5, 1.5, 3])

    with b1:
        st.markdown('<div class="btn-success">', unsafe_allow_html=True)
        if st.button("Activer le compte", use_container_width=True, key="btn_activate"):
            AuthManager.toggle_user_status(sel[0], True)
            AuthManager.log_action(current_user["id"], "ACTIVATE_USER",
                                    "utilisateurs", sel[0])
            st.success(f"Compte {sel[1]} activé.")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with b2:
        st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
        if st.button("Désactiver le compte", use_container_width=True, key="btn_deactivate"):
            AuthManager.toggle_user_status(sel[0], False)
            AuthManager.log_action(current_user["id"], "DEACTIVATE_USER",
                                    "utilisateurs", sel[0])
            st.warning(f"Compte {sel[1]} désactivé.")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(render_section_close(), unsafe_allow_html=True)


def _render_audit_logs():
    """Journal d'audit."""
    st.markdown(render_section_open("Journal d'audit", "FILE_TEXT"), unsafe_allow_html=True)

    nb = st.slider("Nombre d'entrées à afficher", 10, 200, 50)
    logs = get_audit_logs(limit=nb)

    if logs:
        # ✅ FIX : construire ligne par ligne
        rows = []
        for log in logs:
            rows.append({
                "Date": format_datetime(log.get("date_action")),
                "Utilisateur": log.get("nom_complet", "—"),
                "Action": log.get("action", "—"),
                "Table": log.get("table_cible", "—"),
            })

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.markdown(render_empty("FILE_TEXT", "Aucune activité enregistrée"),
                    unsafe_allow_html=True)

    st.markdown(render_section_close(), unsafe_allow_html=True)


def _render_create_user(current_user):
    """Formulaire de création d'utilisateur."""
    st.markdown(render_section_open("Créer un nouveau compte", "PLUS"),
                unsafe_allow_html=True)

    st.markdown(render_notice(
        "Le mot de passe par défaut est <strong>SRM2024!</strong>. "
        "L'utilisateur devra le changer à la première connexion."
    ), unsafe_allow_html=True)

    with st.form("create_user_form"):
        c1, c2 = st.columns(2)

        with c1:
            username = st.text_input("Identifiant *",
                                      placeholder="ex: agent_dp_tata")
            nom_complet = st.text_input("Nom complet *",
                                         placeholder="Prénom Nom")
            email = st.text_input("Email",
                                   placeholder="email@srm-sm.ma")

        with c2:
            role = st.selectbox(
                "Rôle *",
                ["agent_dp", "admin_dp", "admin_regional", "super_admin"],
                format_func=lambda x: {
                    "agent_dp": "Agent DP (saisie)",
                    "admin_dp": "Administrateur DP (validation locale)",
                    "admin_regional": "Administrateur Régional (validation finale)",
                    "super_admin": "Super Administrateur (accès complet)",
                }[x],
            )

            province_id = st.selectbox(
                "Province",
                [None] + list(PROVINCES.keys()),
                format_func=lambda x: "Aucune (Régional/Super)" if x is None else PROVINCES[x]["nom"],
            )

            password = st.text_input("Mot de passe *",
                                      type="password",
                                      value="SRM2024!")

        submitted = st.form_submit_button("Créer le compte",
                                           type="primary",
                                           use_container_width=True)

        if submitted:
            if not username or not nom_complet or not password:
                st.error("Les champs marqués d'un * sont obligatoires.")
            elif len(password) < 8:
                st.error("Le mot de passe doit contenir au moins 8 caractères.")
            elif role in ["agent_dp", "admin_dp"] and province_id is None:
                st.error("Une province doit être sélectionnée pour ce rôle.")
            else:
                code_province = PROVINCES[province_id]["code"] if province_id else None

                result = AuthManager.create_user(
                    username=username,
                    password=password,
                    nom_complet=nom_complet,
                    email=email,
                    role=role,
                    id_province=province_id,
                    code_province=code_province,
                )

                if result["success"]:
                    AuthManager.log_action(
                        current_user["id"], "CREATE_USER", "utilisateurs",
                        details={"username": username, "role": role,
                                 "province": code_province}
                    )
                    st.success(result["message"])
                    st.rerun()
                else:
                    st.error(result["message"])

    st.markdown(render_section_close(), unsafe_allow_html=True)