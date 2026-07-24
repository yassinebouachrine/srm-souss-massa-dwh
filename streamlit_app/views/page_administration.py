# views/page_administration.py
import streamlit as st
import pandas as pd
from datetime import datetime
from auth.session_manager import SessionManager
from auth.authentication import AuthManager
from db.queries import get_audit_logs, get_audit_available_years
from config.provinces import PROVINCES, get_province_name
from utils.helpers import format_datetime, MOIS_FR, get_mois_name
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
    st.markdown(render_section_open("Comptes utilisateurs", "USERS"),
                unsafe_allow_html=True)

    users = AuthManager.get_all_users()
    if not users:
        st.markdown(render_empty("USERS", "Aucun utilisateur"), unsafe_allow_html=True)
        st.markdown(render_section_close(), unsafe_allow_html=True)
        return

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
    """Journal d'audit avec filtres organisés en une seule ligne."""
    from db.queries import get_audit_available_users

    st.markdown(render_section_open("Journal d'audit", "FILE_TEXT"),
                unsafe_allow_html=True)

    # ─── Introduction ───
    st.markdown(
        "<div style='font-size:0.85rem;color:#6B7280;margin-bottom:1rem;'>"
        "Filtrez le journal par compte, province, année ou mois."
        "</div>",
        unsafe_allow_html=True
    )

    # Récupérer les données pour les filtres
    annees_dispo = get_audit_available_years()
    if not annees_dispo:
        annees_dispo = [datetime.now().year]

    users_dispo = get_audit_available_users()

    role_labels = {
        "agent_dp": "Agent DP",
        "admin_dp": "Admin DP",
        "admin_regional": "Admin Régional",
        "super_admin": "Super Admin",
    }

    # ═══════════════════════════════════════════════════
    # LIGNE DE FILTRES UNIFIÉS (4 filtres alignés)
    # ═══════════════════════════════════════════════════
    f1, f2, f3, f4 = st.columns(4)

    # ─── Filtre 1 : Compte utilisateur ───
    with f1:
        user_options = [(None, "Tous les comptes")]
        for u in users_dispo:
            role = role_labels.get(u["role"], u["role"])
            prov = u.get("code_province") or "Régional"
            status = "" if u.get("est_actif") else " [inactif]"
            label = f"{u['nom_complet']} — {role} ({prov}){status}"
            user_options.append((u["id_utilisateur"], label))

        f_user = st.selectbox(
            "Compte utilisateur",
            user_options,
            format_func=lambda x: x[1] if isinstance(x, tuple) else x,
            key="audit_f_user",
        )

    # ─── Filtre 2 : Province ───
    with f2:
        prov_options = [("Toutes", "Toutes les provinces")]
        for pid, pinfo in PROVINCES.items():
            prov_options.append((pid, pinfo["nom"]))
        prov_options.append(("regional", "Admin Régional"))

        f_prov = st.selectbox(
            "Province (DP)",
            prov_options,
            format_func=lambda x: x[1] if isinstance(x, tuple) else x,
            key="audit_f_prov",
        )

    # ─── Filtre 3 : Année ───
    with f3:
        f_annee = st.selectbox(
            "Année",
            ["Toutes"] + annees_dispo,
            key="audit_f_annee",
        )

    # ─── Filtre 4 : Mois ───
    with f4:
        f_mois = st.selectbox(
            "Mois",
            ["Tous"] + list(range(1, 13)),
            format_func=lambda x: "Tous les mois" if x == "Tous" else MOIS_FR[x],
            key="audit_f_mois",
        )

    # ─── Bouton réinitialiser (compact) ───
    st.markdown("<div style='height:0.25rem'></div>", unsafe_allow_html=True)
    reset_col, _ = st.columns([1, 5])
    with reset_col:
        if st.button("Réinitialiser les filtres",
                     key="audit_reset_filters",
                     use_container_width=True):
            for key in ["audit_f_user", "audit_f_prov",
                        "audit_f_annee", "audit_f_mois"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    # ═══════════════════════════════════════════════════
    # APPLIQUER LES FILTRES
    # ═══════════════════════════════════════════════════
    user_id_filter = None
    if isinstance(f_user, tuple) and f_user[0] is not None:
        user_id_filter = f_user[0]

    id_province_filter = None
    filter_regional_only = False

    if isinstance(f_prov, tuple):
        if f_prov[0] == "regional":
            filter_regional_only = True
        elif f_prov[0] != "Toutes":
            id_province_filter = f_prov[0]

    annee_filter = f_annee if f_annee != "Toutes" else None
    mois_filter = f_mois if f_mois != "Tous" else None

    # Récupérer les logs
    logs = get_audit_logs(
        user_id=user_id_filter,
        id_province=id_province_filter,
        annee=annee_filter,
        mois=mois_filter,
        limit=500
    )

    # Filtre supplémentaire pour "Admin Régional (sans province)"
    if filter_regional_only and logs:
        logs = [log for log in logs if log.get("id_province") is None]

    # ═══════════════════════════════════════════════════
    # RÉSUMÉ DES FILTRES ACTIFS
    # ═══════════════════════════════════════════════════
    filter_summary = []

    if isinstance(f_user, tuple) and f_user[0] is not None:
        selected_user = next(
            (u for u in users_dispo if u["id_utilisateur"] == f_user[0]),
            None
        )
        if selected_user:
            filter_summary.append(f"Compte : <strong>{selected_user['nom_complet']}</strong>")

    if isinstance(f_prov, tuple) and f_prov[0] != "Toutes":
        filter_summary.append(f"Province : <strong>{f_prov[1]}</strong>")

    if annee_filter:
        filter_summary.append(f"Année : <strong>{annee_filter}</strong>")

    if mois_filter:
        filter_summary.append(f"Mois : <strong>{MOIS_FR[mois_filter]}</strong>")

    nb_logs = len(logs) if logs else 0

    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

    if filter_summary:
        st.markdown(
            f"<div style='background:#F0F9FF;border-left:3px solid #0EA5E9;"
            f"padding:0.6rem 0.9rem;border-radius:4px;font-size:0.85rem;color:#075985;"
            f"margin-bottom:0.75rem;'>"
            f"<strong>{nb_logs}</strong> résultat(s) — "
            f"Filtres : {' · '.join(filter_summary)}"
            f"</div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"<div style='color:#6B7280;font-size:0.85rem;margin-bottom:0.75rem;'>"
            f"<strong style='color:#111827;'>{nb_logs}</strong> "
            f"log(s) affiché(s) sur 500 max"
            f"</div>",
            unsafe_allow_html=True
        )

    # ═══════════════════════════════════════════════════
    # AFFICHAGE DU TABLEAU
    # ═══════════════════════════════════════════════════
    if logs:
        rows = []
        for log in logs:
            rows.append({
                "Date": format_datetime(log.get("date_action")),
                "Utilisateur": log.get("nom_complet", "—"),
                "Username": log.get("username", "—"),
                "Rôle": role_labels.get(log.get("role"), log.get("role", "—")),
                "Province": log.get("code_province") or "—",
                "Action": log.get("action", "—"),
                "Table": log.get("table_cible", "—"),
            })

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # ─── Statistiques ───
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        col_s1, col_s2, col_s3 = st.columns(3)

        with col_s1:
            st.metric("Total logs", nb_logs)
        with col_s2:
            unique_users = len(set(log.get("nom_complet") for log in logs))
            st.metric("Utilisateurs actifs", unique_users)
        with col_s3:
            unique_actions = len(set(log.get("action") for log in logs))
            st.metric("Types d'actions", unique_actions)
    else:
        st.markdown(render_empty(
            "FILE_TEXT",
            "Aucune activité",
            "Aucun log ne correspond aux filtres sélectionnés"
        ), unsafe_allow_html=True)

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
                format_func=lambda x: ("Aucune (Régional/Super)"
                                       if x is None else PROVINCES[x]["nom"]),
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