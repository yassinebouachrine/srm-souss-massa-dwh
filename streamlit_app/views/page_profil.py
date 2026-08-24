# views/page_profil.py
import streamlit as st
from auth.session_manager import SessionManager
from auth.authentication import AuthManager
from config.provinces import get_province_name
from utils.styles import (
    render_page_header,
    render_section_open, render_section_close,
    get_role_label
)


def render_profil():
    """Page de profil utilisateur."""
    SessionManager.require_auth()
    user = SessionManager.get_user()

    st.markdown(
        render_page_header("Mon profil", "Informations personnelles et sécurité"),
        unsafe_allow_html=True,
    )

    province_name = get_province_name(user["id_province"]) if user["id_province"] else "Région complète"

    c_l, c_r = st.columns(2, gap="medium")

    # ── Informations du compte ──
    with c_l:
        st.markdown(render_section_open("Informations du compte", "USER"),
                    unsafe_allow_html=True)

        st.markdown(f"""
        <div style="line-height:2;font-size:0.88rem;">
            <div><strong>Nom complet :</strong> {user['nom_complet']}</div>
            <div><strong>Identifiant :</strong> <code>{user['username']}</code></div>
            <div><strong>Email :</strong> {user.get('email', '—') or '—'}</div>
            <div><strong>Rôle :</strong> {get_role_label(user['role'])}</div>
            <div><strong>Province :</strong> {province_name}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(render_section_close(), unsafe_allow_html=True)

    # ── Changer le mot de passe ──
    with c_r:
        st.markdown(render_section_open("Changer le mot de passe", "LOCK"),
                    unsafe_allow_html=True)

        with st.form("pwd_form"):
            old = st.text_input("Ancien mot de passe", type="password")
            new = st.text_input("Nouveau mot de passe", type="password",
                                 help="Minimum 8 caractères")
            conf = st.text_input("Confirmer le nouveau mot de passe", type="password")

            if st.form_submit_button("Modifier le mot de passe",
                                     type="primary",
                                     use_container_width=True):
                if not old or not new or not conf:
                    st.error("Remplissez tous les champs.")
                elif new != conf:
                    st.error("Les nouveaux mots de passe ne correspondent pas.")
                elif len(new) < 8:
                    st.error("Le mot de passe doit contenir au moins 8 caractères.")
                else:
                    res = AuthManager.change_password(user["id"], old, new)
                    if res["success"]:
                        st.success(res["message"])
                    else:
                        st.error(res["message"])

        st.markdown(render_section_close(), unsafe_allow_html=True)