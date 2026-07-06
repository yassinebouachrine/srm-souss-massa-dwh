"""
SRM Souss-Massa - Point d'entree
Redirige vers Dashboard ou Login
"""

import streamlit as st
from pathlib import Path

from streamlit_app.auth.simple_auth import (
    check_authentication, show_login_page,
    show_user_info_sidebar, get_current_user
)


st.set_page_config(
    page_title="SRM Souss-Massa",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS
css_path = Path(__file__).parent / "assets" / "style.css"
if css_path.exists():
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Verification authentification
if not check_authentication():
    show_login_page()
    st.stop()

# Rediriger automatiquement vers Dashboard
st.switch_page("pages/00_Dashboard.py")